#!/usr/bin/env python3
"""
LLM Orchestration for ai-blog-system
Gemini API パイプライン向けオーケストレーションパターン

1. RetryWithBackoff  - 指数バックオフ (base_delay=2s, max_delay=30s, jitter=25%)
2. ContextBudget     - 6ステージパイプラインのトークン予算管理
3. StageCache        - ステージ間の安定データキャッシュ (per-run TTL)
"""

import logging
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. RetryWithBackoff — 指数バックオフ付きリトライ
# ---------------------------------------------------------------------------

class RetryWithBackoff:
    """API呼び出しの指数バックオフリトライ管理.

    gemini_client.py の既存キーローテーションと併用する。
    全キーが429で枯渇した場合にバックオフ待機を挟んでリトライする。

    Usage:
        backoff = RetryWithBackoff()
        delay = backoff.next_delay()  # 2.0 + jitter
        backoff.record_success()      # リセット
    """

    def __init__(
        self,
        base_delay: float = 2.0,
        max_delay: float = 30.0,
        jitter_factor: float = 0.25,
        max_retries: int = 4,
    ):
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter_factor = jitter_factor
        self.max_retries = max_retries
        self._attempt = 0

    def next_delay(self) -> Optional[float]:
        """次のバックオフ待機時間を返す。リトライ上限超過時は None."""
        if self._attempt >= self.max_retries:
            return None
        delay = min(self.base_delay * (2 ** self._attempt), self.max_delay)
        jitter = delay * self.jitter_factor * random.random()
        self._attempt += 1
        return delay + jitter

    def record_success(self) -> None:
        """成功時にリトライカウンタをリセット."""
        self._attempt = 0

    @property
    def attempt(self) -> int:
        return self._attempt

    @property
    def exhausted(self) -> bool:
        return self._attempt >= self.max_retries

    def wait_and_retry(self) -> bool:
        """バックオフ待機を実行。リトライ可能なら True、上限到達なら False."""
        delay = self.next_delay()
        if delay is None:
            return False
        print(
            f"  [Backoff] Waiting {delay:.1f}s (attempt {self._attempt}/{self.max_retries})...",
            file=sys.stderr,
        )
        time.sleep(delay)
        return True


# ---------------------------------------------------------------------------
# 2. ContextBudget — ステージ別トークン予算管理
# ---------------------------------------------------------------------------

# 日本語: ~1.5文字/トークン（英語混在を考慮して2文字/トークンで推定）
CHARS_PER_TOKEN = 2

# Stage 2 コンテキスト予算のデフォルト値
DEFAULT_STAGE2_BUDGET = {
    "kb": 2000,           # KnowledgeBase コンテキスト
    "research": 800,      # ResearchLoader コンテキスト
    "compliance": 300,    # ComplianceLoader コンテキスト
    "persona": 500,       # ペルソナ情報
}

# Stage 2 合計上限
STAGE2_TOTAL_LIMIT = sum(DEFAULT_STAGE2_BUDGET.values())  # 3600 tokens


@dataclass
class ContextBudget:
    """6ステージパイプラインのトークン予算トラッカー.

    各ステージのコンテキストサイズを推定し、予算超過を検知・制限する。
    Stage 2 のコンテキストは KB + Research + Compliance + Persona で
    合計 ~12,000 トークン以内に収める。

    Usage:
        budget = ContextBudget()
        kb_text = budget.truncate_to_budget("kb", raw_kb_text)
        research_text = budget.truncate_to_budget("research", raw_research)
        budget.log_summary()
    """

    limits: Dict[str, int] = field(default_factory=lambda: dict(DEFAULT_STAGE2_BUDGET))
    _usage: Dict[str, int] = field(default_factory=dict, init=False)

    def estimate_tokens(self, text: str) -> int:
        """テキストの推定トークン数を返す."""
        if not text:
            return 0
        return len(text) // CHARS_PER_TOKEN

    def truncate_to_budget(self, component: str, text: str) -> str:
        """コンポーネントのトークン予算に収まるようテキストを切り詰める.

        Args:
            component: 予算コンポーネント名 (kb, research, compliance, persona)
            text: 入力テキスト

        Returns:
            予算内に収まるテキスト（切り詰め時は末尾に注記）
        """
        if not text:
            self._usage[component] = 0
            return text

        limit = self.limits.get(component, 1000)
        max_chars = limit * CHARS_PER_TOKEN
        estimated = self.estimate_tokens(text)

        if estimated <= limit:
            self._usage[component] = estimated
            return text

        # 切り詰め: 文末で切る試行
        truncated = text[:max_chars]
        # 最後の改行で切る（途中の文を避ける）
        last_newline = truncated.rfind('\n')
        if last_newline > max_chars * 0.7:
            truncated = truncated[:last_newline]

        truncated += "\n...(トークン予算により省略)"
        self._usage[component] = self.estimate_tokens(truncated)

        print(
            f"  [ContextBudget] {component}: {estimated} → {self._usage[component]} tokens "
            f"(limit: {limit})",
            file=sys.stderr,
        )
        return truncated

    def total_used(self) -> int:
        """使用済みトークン合計."""
        return sum(self._usage.values())

    def remaining(self, component: str) -> int:
        """コンポーネントの残りトークン数."""
        limit = self.limits.get(component, 0)
        used = self._usage.get(component, 0)
        return max(0, limit - used)

    def log_summary(self) -> None:
        """予算使用状況をログ出力."""
        total = self.total_used()
        total_limit = sum(self.limits.values())
        parts = []
        for comp, limit in self.limits.items():
            used = self._usage.get(comp, 0)
            parts.append(f"{comp}={used}/{limit}")
        detail = ", ".join(parts)
        print(
            f"  [ContextBudget] Total: {total}/{total_limit} tokens ({detail})",
            file=sys.stderr,
        )

    def summary(self) -> Dict[str, Any]:
        """予算使用状況を辞書で返す."""
        return {
            "total_used": self.total_used(),
            "total_limit": sum(self.limits.values()),
            "components": {
                comp: {"used": self._usage.get(comp, 0), "limit": limit}
                for comp, limit in self.limits.items()
            },
        }


# ---------------------------------------------------------------------------
# 3. StageCache — ステージ間の安定データキャッシュ
# ---------------------------------------------------------------------------

class StageCache:
    """パイプライン実行間で安定データをキャッシュする.

    compliance_loader.build_article_context() や research_loader.find_research() は
    同一パイプラインの複数記事で結果が変わらないデータを返す。
    per-run TTL でキャッシュし、不要な再計算を避ける。

    Usage:
        cache = StageCache(ttl=3600)
        key = "compliance:AI最新ニュース"
        if cache.has(key):
            data = cache.get(key)
        else:
            data = compliance_loader.build_article_context(...)
            cache.set(key, data)
    """

    def __init__(self, ttl: int = 3600):
        """初期化.

        Args:
            ttl: キャッシュの有効期間（秒）。デフォルト1時間。
        """
        self.ttl = ttl
        self._store: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._hits = 0
        self._misses = 0

    def _is_valid(self, key: str) -> bool:
        """キーが有効期限内かどうかチェック."""
        if key not in self._timestamps:
            return False
        return (time.time() - self._timestamps[key]) < self.ttl

    def has(self, key: str) -> bool:
        """キーが存在し有効期限内か."""
        return key in self._store and self._is_valid(key)

    def get(self, key: str, default: Any = None) -> Any:
        """キャッシュから値を取得."""
        if self.has(key):
            self._hits += 1
            return self._store[key]
        self._misses += 1
        return default

    def set(self, key: str, value: Any) -> None:
        """キャッシュに値を設定."""
        self._store[key] = value
        self._timestamps[key] = time.time()

    def invalidate(self, key: str) -> None:
        """特定キーを無効化."""
        self._store.pop(key, None)
        self._timestamps.pop(key, None)

    def clear(self) -> None:
        """全キャッシュをクリア."""
        self._store.clear()
        self._timestamps.clear()

    @property
    def stats(self) -> Dict[str, int]:
        """ヒット率統計."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0.0,
            "entries": len(self._store),
        }

    def log_stats(self) -> None:
        """統計をログ出力."""
        s = self.stats
        print(
            f"  [StageCache] hits={s['hits']}, misses={s['misses']}, "
            f"rate={s['hit_rate']}%, entries={s['entries']}",
            file=sys.stderr,
        )


# ---------------------------------------------------------------------------
# Module-level singletons (パイプライン全体で共有)
# ---------------------------------------------------------------------------

# Stage 2 コンテキスト予算トラッカー
context_budget = ContextBudget()

# パイプライン実行間キャッシュ（TTL 1時間）
stage_cache = StageCache(ttl=3600)

# Gemini API バックオフ管理
api_backoff = RetryWithBackoff(
    base_delay=2.0,
    max_delay=30.0,
    jitter_factor=0.25,
    max_retries=4,
)
