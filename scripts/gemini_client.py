#!/usr/bin/env python3
"""
Enhanced Gemini API client with structured JSON output and Web Search support.
Replaces the simple generate_content.py wrapper.

Features:
- Model rotation for quota management
- JSON mode with schema validation
- Google Search grounding support
- Flexible model selection (light/heavy tasks)
- Backward compatibility with generate_content.py

Usage:
    from gemini_client import GeminiClient

    client = GeminiClient()

    # Basic text generation
    text = client.call("Write a blog post about AI")

    # Structured JSON output
    json_data = client.call_json("Generate article metadata", schema={...})

    # With Google Search grounding
    researched_text = client.call_with_search("Latest AI trends in 2026")
    researched_json = client.call_json_with_search("Find trending topics", schema={...})
"""

import os
import sys
import json
import time
import requests

# Import orchestration (optional — graceful degradation)
try:
    from llm_orchestration import RetryWithBackoff, api_backoff as _api_backoff
except ImportError:
    _api_backoff = None


class GeminiClient:
    """Gemini API client with model rotation, API key rotation, JSON mode, and Web Search."""

    # Model rotation list
    # Strategy: pro for quality-critical drafts, flash-lite for everything else
    # Avoids flash (20 RPD free tier limit) to prevent 429 cascades
    MODELS = [
        "gemini-2.5-flash-lite",
        "gemini-2.0-flash"
    ]

    # Model tiers for different tasks
    # LIGHT: JSON/metadata tasks - flash-lite first (1,000 RPD free tier)
    LIGHT_MODELS = ["gemini-2.5-flash-lite", "gemini-2.0-flash"]
    # HEAVY: Article drafts - pro first (100 RPD free tier), then flash-lite fallback
    HEAVY_MODELS = ["gemini-2.5-pro", "gemini-2.5-flash-lite"]
    # NEWS: Web Search でリアルタイムニュース取得 — 3モデルをローテーション
    NEWS_MODELS = ["gemini-2.5-flash-lite", "gemini-2.5-flash", "gemini-2.0-flash"]

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key=None):
        """Initialize Gemini client with multiple API key support.

        Reads API keys from:
          1. api_key argument (single key)
          2. GEMINI_API_KEYS env var (comma-separated list)
          3. GEMINI_API_KEY env var (single key, backward compatible)

        On 429 quota errors, automatically rotates to the next API key.
        """
        self.api_keys = []
        self._current_key_index = 0

        if api_key:
            self.api_keys = [api_key]
        else:
            # Try comma-separated list first
            keys_str = os.environ.get('GEMINI_API_KEYS', '')
            if keys_str:
                self.api_keys = [k.strip() for k in keys_str.split(',') if k.strip()]
            # Fallback to single key
            if not self.api_keys:
                single_key = os.environ.get('GEMINI_API_KEY', '')
                if single_key:
                    self.api_keys = [single_key]

        if not self.api_keys:
            raise ValueError("No Gemini API keys found (set GEMINI_API_KEYS or GEMINI_API_KEY)")

        # Track exhausted keys per model to avoid retrying known-bad combos
        self._exhausted = set()

        # Token usage estimation (per-session)
        self._token_usage = {"input": 0, "output": 0, "calls": 0}

        print(f"  [GeminiClient] Initialized with {len(self.api_keys)} API key(s)", file=sys.stderr)

    @property
    def api_key(self):
        """Current active API key (backward compatible)."""
        return self.api_keys[self._current_key_index]

    @api_key.setter
    def api_key(self, value):
        """Setter for backward compatibility."""
        if value and value not in self.api_keys:
            self.api_keys = [value]
            self._current_key_index = 0

    @property
    def token_usage(self):
        """Session token usage estimation summary."""
        return dict(self._token_usage)

    def call(self, prompt, model=None, temperature=0.9, max_tokens=8192, model_tier=None):
        """Generate text content.

        Args:
            prompt: The prompt text to send to the model
            model: Specific model to use (or None for automatic rotation)
            temperature: Sampling temperature (0.0-1.0, default 0.9)
            max_tokens: Maximum output tokens (default 8192)
            model_tier: "heavy" for HEAVY_MODELS, "light" for LIGHT_MODELS,
                        None for default MODELS rotation

        Returns:
            Generated text string, or None if all models fail
        """
        if model:
            models = [model]
        elif model_tier == "heavy":
            models = self.HEAVY_MODELS
        elif model_tier == "light":
            models = self.LIGHT_MODELS
        else:
            models = self.MODELS

        for m in models:
            result = self._request(m, prompt, temperature, max_tokens)
            if result is not None:
                return result
        return None

    def call_json(self, prompt, schema=None, model=None, temperature=0.7, max_tokens=8192, model_tier=None):
        """Generate structured JSON output.

        Args:
            prompt: The prompt text
            schema: Optional JSON schema dict for response validation
            model: Specific model to use (or None for rotation)
            temperature: Lower default (0.7) for structured output
            max_tokens: Max output tokens
            model_tier: "heavy" for HEAVY_MODELS, "light" for LIGHT_MODELS,
                        None for default LIGHT_MODELS rotation

        Returns:
            Parsed JSON dict, or None if all models fail

        Example:
            schema = {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}}
                }
            }
            result = client.call_json("Generate article metadata", schema=schema)
        """
        if model:
            models = [model]
        elif model_tier == "heavy":
            models = self.HEAVY_MODELS
        elif model_tier == "light":
            models = self.LIGHT_MODELS
        else:
            models = self.LIGHT_MODELS

        for m in models:
            result = self._request(
                m, prompt, temperature, max_tokens,
                response_mime_type="application/json",
                response_schema=schema
            )
            if result is not None:
                parsed = self._extract_json(result)
                if parsed is not None:
                    return parsed
                print(f"Warning: Failed to parse JSON from {m}, trying next model", file=sys.stderr)
                continue
        return None

    def call_with_search(self, prompt, model=None, temperature=0.9, max_tokens=8192):
        """Generate content with Google Search grounding enabled.

        This method enables the model to search the web for up-to-date information
        before generating the response.

        Args:
            prompt: The prompt text
            model: Specific model to use (or None for heavy model rotation)
            temperature: Sampling temperature (default 0.9)
            max_tokens: Max output tokens

        Returns:
            Generated text string with search grounding, or None if all models fail
        """
        models = [model] if model else self.HEAVY_MODELS

        for m in models:
            result = self._request(
                m, prompt, temperature, max_tokens,
                enable_search=True
            )
            if result is not None:
                return result
        return None

    def call_json_with_search(self, prompt, schema=None, model=None, temperature=0.7, max_tokens=8192):
        """Generate structured JSON with Google Search grounding.

        Note: Gemini API does not support responseMimeType with google_search tool,
        so this method relies on prompt instructions for JSON output and parses
        the text response. The schema parameter is kept for documentation purposes
        but is NOT sent to the API when search is enabled.

        Args:
            prompt: The prompt text (should include JSON output instructions)
            schema: JSON schema dict (used as documentation; not sent with search)
            model: Specific model to use (or None for heavy model rotation)
            temperature: Lower default (0.7) for structured output
            max_tokens: Max output tokens

        Returns:
            Parsed JSON dict with search grounding, or None if all models fail
        """
        models = [model] if model else self.HEAVY_MODELS

        for m in models:
            result = self._request(
                m, prompt, temperature, max_tokens,
                response_mime_type="application/json",
                response_schema=schema,
                enable_search=True
            )
            if result is not None:
                parsed = self._extract_json(result)
                if parsed is not None:
                    return parsed
                print(f"Warning: Failed to parse JSON from {m}, trying next", file=sys.stderr)
                continue
        return None

    def fetch_news(self, query="AI 人工知能 最新ニュース", max_items=15, temperature=0.5):
        """Fetch latest AI news headlines via Google Search grounding.

        Uses NEWS_MODELS rotation to retrieve real-time news.

        Args:
            query: Search query for news (default: AI news)
            max_items: Maximum number of news items to return (default: 15)
            temperature: Low temperature for factual output (default: 0.5)

        Returns:
            List of dicts with keys: headline, source, date, summary, url
            Returns empty list if all models fail.
        """
        from datetime import datetime, timezone, timedelta
        today = datetime.now(timezone(timedelta(hours=9))).strftime('%Y年%m月%d日')

        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "headline": {"type": "STRING"},
                    "source": {"type": "STRING"},
                    "date": {"type": "STRING"},
                    "summary": {"type": "STRING"},
                    "category": {"type": "STRING"},
                },
                "required": ["headline", "summary", "category"]
            }
        }

        prompt = f"""あなたはAIニュース調査員です。本日（{today}）時点の最新AI関連ニュースを{max_items}件リストアップしてください。

【検索対象】
{query}

【収集範囲】
- 直近1週間以内のニュースを優先
- グローバル（英語圏）と日本国内の両方を含む
- 企業発表、製品リリース、研究成果、規制動向、資金調達など幅広く

【カテゴリ分類】各ニュースに以下のいずれかを付与:
- 企業動向（製品発表、提携、M&A）
- 技術革新（新モデル、ベンチマーク更新、新手法）
- 規制・政策（法規制、ガイドライン、国際協定）
- 資金調達・市場（投資、IPO、市場規模）
- 研究成果（論文、学会発表）
- 社会影響（雇用、教育、倫理）

【出力条件】
- headline: ニュース見出し（日本語、40文字以内）
- source: 情報源（メディア名やプレスリリース元）
- date: 日付（YYYY-MM-DD形式、不明なら空文字）
- summary: 要約（100文字以内、具体的な数値や企業名を含む）
- category: 上記カテゴリから1つ

重複や古いニュースは除外し、多様なカテゴリから選んでください。"""

        for model in self.NEWS_MODELS:
            result = self._request(
                model, prompt, temperature, max_tokens=4096,
                response_mime_type="application/json",
                response_schema=schema,
                enable_search=True
            )
            if result is not None:
                try:
                    news = json.loads(result)
                    if isinstance(news, list) and len(news) > 0:
                        print(f"  [GeminiClient] Fetched {len(news)} news items via {model}", file=sys.stderr)
                        return news[:max_items]
                except json.JSONDecodeError:
                    cleaned = result.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.split("\n")
                        json_str = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
                        try:
                            news = json.loads(json_str)
                            if isinstance(news, list):
                                return news[:max_items]
                        except json.JSONDecodeError:
                            pass
                    print(f"  [GeminiClient] Failed to parse news JSON from {model}", file=sys.stderr)
                    continue

        print("  [GeminiClient] All NEWS_MODELS failed for fetch_news", file=sys.stderr)
        return []

    @staticmethod
    def _extract_json(text):
        """Extract and parse JSON from text that may contain markdown code fences.

        Handles these formats:
          - Pure JSON string
          - ```json ... ``` wrapped JSON
          - ``` ... ``` wrapped JSON

        Returns:
            Parsed Python object (dict or list), or None if parsing fails.
        """
        if text is None:
            return None

        # 1) Try direct parse first
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass

        # 2) Try stripping markdown code fences
        cleaned = text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            # Remove first line (```json or ```) and last line (```)
            end = -1 if lines[-1].strip() == "```" else len(lines)
            json_str = "\n".join(lines[1:end])
            try:
                return json.loads(json_str)
            except (json.JSONDecodeError, TypeError):
                pass

        return None

    def _request(self, model, prompt, temperature, max_tokens,
                 response_mime_type=None, response_schema=None, enable_search=False):
        """Internal: Make API request with automatic key rotation on 429.

        Tries the current API key first. On quota error (429), rotates to
        the next key and retries the same model. Only returns None when all
        keys are exhausted for this model.
        """
        url = f"{self.BASE_URL}/{model}:generateContent"

        data = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topK": 40,
                "topP": 0.95,
                "maxOutputTokens": max_tokens,
            }
        }

        # Gemini API does not support responseMimeType with google_search tool.
        # When search is enabled, skip JSON mode and rely on prompt-based JSON output
        # with text-based parsing in the caller.
        if response_mime_type and not enable_search:
            data["generationConfig"]["responseMimeType"] = response_mime_type
        if response_schema and not enable_search:
            data["generationConfig"]["responseSchema"] = response_schema

        if enable_search:
            data["tools"] = [{"google_search": {}}]

        # Try each API key for this model
        keys_tried = 0
        start_index = self._current_key_index

        while keys_tried < len(self.api_keys):
            key_id = self._current_key_index
            cache_key = f"{model}:key{key_id}"

            # Skip keys already known to be exhausted for this model
            if cache_key in self._exhausted:
                self._current_key_index = (self._current_key_index + 1) % len(self.api_keys)
                keys_tried += 1
                continue

            current_key = self.api_keys[self._current_key_index]
            key_label = f"key{key_id + 1}/{len(self.api_keys)}"

            headers = {
                'Content-Type': 'application/json',
                'X-goog-api-key': current_key
            }

            try:
                print(f"  [GeminiClient] Trying {model} ({key_label})...", file=sys.stderr)
                response = requests.post(url, headers=headers, json=data, timeout=120)

                if response.status_code == 429:
                    print(f"  [GeminiClient] Quota limit for {model} ({key_label})", file=sys.stderr)
                    self._exhausted.add(cache_key)
                    self._current_key_index = (self._current_key_index + 1) % len(self.api_keys)
                    keys_tried += 1
                    continue

                if response.status_code != 200:
                    print(f"  [GeminiClient] HTTP {response.status_code} for {model}: {response.text[:200]}", file=sys.stderr)
                    return None

                result = response.json()
                if 'candidates' in result and len(result['candidates']) > 0:
                    candidate = result['candidates'][0]
                    if 'content' in candidate and 'parts' in candidate['content']:
                        text = candidate['content']['parts'][0].get('text', '')
                        if text:
                            print(f"  [GeminiClient] Success with {model} ({key_label})", file=sys.stderr)
                            # Track token usage (estimation)
                            self._token_usage["input"] += len(prompt) // 2
                            self._token_usage["output"] += len(text) // 2
                            self._token_usage["calls"] += 1
                            # Reset backoff on success
                            if _api_backoff:
                                _api_backoff.record_success()
                            return text

                print(f"  [GeminiClient] No content from {model}", file=sys.stderr)
                return None

            except requests.exceptions.Timeout:
                print(f"  [GeminiClient] Timeout for {model}", file=sys.stderr)
                return None
            except requests.exceptions.RequestException as e:
                print(f"  [GeminiClient] Request error for {model}: {e}", file=sys.stderr)
                return None
            except Exception as e:
                print(f"  [GeminiClient] Error for {model}: {e}", file=sys.stderr)
                return None

        # All keys exhausted — apply exponential backoff before giving up
        if _api_backoff and not _api_backoff.exhausted:
            print(f"  [GeminiClient] All {len(self.api_keys)} keys exhausted for {model}, applying backoff...", file=sys.stderr)
            if _api_backoff.wait_and_retry():
                # Clear exhausted keys for this model to allow retry
                self._exhausted = {k for k in self._exhausted if not k.startswith(f"{model}:")}
                # Recursive retry (backoff attempt counter prevents infinite recursion)
                return self._request(model, prompt, temperature, max_tokens,
                                     response_mime_type, response_schema, enable_search)

        print(f"  [GeminiClient] All {len(self.api_keys)} keys exhausted for {model}", file=sys.stderr)
        return None


# Convenience function for backward compatibility
def call_gemini_api(prompt, output_file=None):
    """Drop-in replacement for generate_content.py's call_gemini_api.

    Args:
        prompt: The prompt text to send to the model
        output_file: Optional file path to write output. If None, prints to stdout.

    Returns:
        True if successful, False otherwise
    """
    try:
        client = GeminiClient()
        result = client.call(prompt)
        if result:
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(result)
            else:
                print(result)
            return True
        return False
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return False


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: gemini_client.py <prompt> [output_file]", file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    success = call_gemini_api(prompt, output_file)
    sys.exit(0 if success else 1)
