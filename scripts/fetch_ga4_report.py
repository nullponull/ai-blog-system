#!/usr/bin/env python3
"""
GA4 Data API レポート取得スクリプト

使い方:
  # サービスアカウント認証 (推奨)
  export GA4_PROPERTY_ID="123456789"
  export GOOGLE_APPLICATION_CREDENTIALS="/home/sol/.ga4_service_account.json"
  python3 fetch_ga4_report.py

  # または OAuth 認証
  export GA4_PROPERTY_ID="123456789"
  export GA4_CREDENTIALS="/home/sol/.ga4_credentials.json"
  python3 fetch_ga4_report.py

事前準備:
  1. GA4管理画面 > プロパティ設定 から Property ID を確認
  2. サービスアカウント ga4-reader@gemini-api-project-470216.iam.gserviceaccount.com を
     GA4管理画面 > アカウントアクセス管理 で「閲覧者」として追加
  3. pip install google-analytics-data
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta

# Suppress Python 3.8 deprecation warnings
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    OrderBy,
    RunReportRequest,
)


def get_client():
    """認証済みGA4クライアントを取得"""
    # 方法1: サービスアカウント (GOOGLE_APPLICATION_CREDENTIALS)
    sa_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if sa_path and os.path.exists(sa_path):
        return BetaAnalyticsDataClient()

    # 方法2: OAuth credentials
    oauth_path = os.environ.get("GA4_CREDENTIALS", os.path.expanduser("~/.ga4_credentials.json"))
    if os.path.exists(oauth_path):
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        with open(oauth_path) as f:
            data = json.load(f)
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data["refresh_token"],
            token_uri=data["token_uri"],
            client_id=data["client_id"],
            client_secret=data["client_secret"],
        )
        if creds.expired or not creds.token:
            creds.refresh(Request())
        return BetaAnalyticsDataClient(credentials=creds)

    print("エラー: 認証情報が見つかりません。")
    print("GOOGLE_APPLICATION_CREDENTIALS または GA4_CREDENTIALS を設定してください。")
    sys.exit(1)


def get_property_id():
    prop_id = os.environ.get("GA4_PROPERTY_ID")
    if not prop_id:
        print("エラー: GA4_PROPERTY_ID 環境変数を設定してください。")
        print("GA4管理画面 > プロパティ設定 で確認できます。")
        sys.exit(1)
    return prop_id


def run_report(client, property_id, dimensions, metrics, date_range, order_by=None, limit=0):
    """汎用レポート実行"""
    request = RunReportRequest(
        property=f"properties/{property_id}",
        dimensions=[Dimension(name=d) for d in dimensions],
        metrics=[Metric(name=m) for m in metrics],
        date_ranges=[DateRange(start_date=date_range[0], end_date=date_range[1])],
        limit=limit if limit else 10000,
    )
    if order_by:
        request.order_bys = order_by
    return client.run_report(request)


def report_overview(client, property_id, date_range):
    """サマリーレポート: PV, ユーザー数, セッション数"""
    print("\n" + "=" * 60)
    print(f"  GA4 サマリーレポート ({date_range[0]} ~ {date_range[1]})")
    print("=" * 60)

    response = run_report(
        client, property_id,
        dimensions=[],
        metrics=[
            "screenPageViews", "activeUsers", "sessions",
            "averageSessionDuration", "bounceRate", "newUsers",
        ],
        date_range=date_range,
    )

    if response.rows:
        row = response.rows[0]
        labels = ["ページビュー", "アクティブユーザー", "セッション",
                  "平均セッション時間(秒)", "直帰率", "新規ユーザー"]
        for label, val in zip(labels, row.metric_values):
            v = val.value
            if "率" in label:
                v = f"{float(v)*100:.1f}%"
            elif "時間" in label:
                v = f"{float(v):.0f}秒"
            print(f"  {label}: {v}")
    else:
        print("  データなし")


def report_daily_trend(client, property_id, date_range):
    """日別トレンド"""
    print("\n" + "-" * 60)
    print("  日別PV・ユーザートレンド")
    print("-" * 60)

    response = run_report(
        client, property_id,
        dimensions=["date"],
        metrics=["screenPageViews", "activeUsers"],
        date_range=date_range,
        order_by=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
    )

    print(f"  {'日付':<12} {'PV':>8} {'ユーザー':>8}")
    print(f"  {'-'*12} {'-'*8} {'-'*8}")
    for row in response.rows:
        date_str = row.dimension_values[0].value
        date_fmt = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:]}"
        pv = row.metric_values[0].value
        users = row.metric_values[1].value
        print(f"  {date_fmt:<12} {pv:>8} {users:>8}")


def report_top_pages(client, property_id, date_range, limit=20):
    """ページ別PVランキング"""
    print("\n" + "-" * 60)
    print(f"  上位記事ランキング (TOP {limit})")
    print("-" * 60)

    response = run_report(
        client, property_id,
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "activeUsers", "averageSessionDuration"],
        date_range=date_range,
        order_by=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"),
            desc=True,
        )],
        limit=limit,
    )

    print(f"  {'#':>3} {'PV':>8} {'Users':>6} {'Avg(s)':>7}  タイトル")
    print(f"  {'---':>3} {'--------':>8} {'------':>6} {'-------':>7}  {'---'*10}")
    for i, row in enumerate(response.rows, 1):
        path = row.dimension_values[0].value
        title = row.dimension_values[1].value[:50]
        pv = row.metric_values[0].value
        users = row.metric_values[1].value
        avg_dur = f"{float(row.metric_values[2].value):.0f}"
        print(f"  {i:>3} {pv:>8} {users:>6} {avg_dur:>7}  {title}")
        if i <= 5:
            print(f"  {'':>3} {'':>8} {'':>6} {'':>7}  {path}")


def report_traffic_sources(client, property_id, date_range):
    """流入元レポート"""
    print("\n" + "-" * 60)
    print("  流入元 (Traffic Sources)")
    print("-" * 60)

    response = run_report(
        client, property_id,
        dimensions=["sessionDefaultChannelGroup"],
        metrics=["sessions", "activeUsers", "screenPageViews"],
        date_range=date_range,
        order_by=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="sessions"),
            desc=True,
        )],
    )

    print(f"  {'チャネル':<25} {'Sessions':>10} {'Users':>8} {'PV':>8}")
    print(f"  {'-'*25} {'-'*10} {'-'*8} {'-'*8}")
    for row in response.rows:
        channel = row.dimension_values[0].value
        sessions = row.metric_values[0].value
        users = row.metric_values[1].value
        pv = row.metric_values[2].value
        print(f"  {channel:<25} {sessions:>10} {users:>8} {pv:>8}")


def report_devices(client, property_id, date_range):
    """デバイス別レポート"""
    print("\n" + "-" * 60)
    print("  デバイス別アクセス")
    print("-" * 60)

    response = run_report(
        client, property_id,
        dimensions=["deviceCategory"],
        metrics=["sessions", "activeUsers", "screenPageViews"],
        date_range=date_range,
        order_by=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="sessions"),
            desc=True,
        )],
    )

    print(f"  {'デバイス':<15} {'Sessions':>10} {'Users':>8} {'PV':>8}")
    print(f"  {'-'*15} {'-'*10} {'-'*8} {'-'*8}")
    for row in response.rows:
        device = row.dimension_values[0].value
        sessions = row.metric_values[0].value
        users = row.metric_values[1].value
        pv = row.metric_values[2].value
        print(f"  {device:<15} {sessions:>10} {users:>8} {pv:>8}")


def report_search_queries(client, property_id, date_range):
    """検索クエリ（Landing Page + Source）"""
    print("\n" + "-" * 60)
    print("  オーガニック検索ランディングページ TOP10")
    print("-" * 60)

    response = run_report(
        client, property_id,
        dimensions=["landingPage"],
        metrics=["sessions", "activeUsers"],
        date_range=date_range,
        order_by=[OrderBy(
            metric=OrderBy.MetricOrderBy(metric_name="sessions"),
            desc=True,
        )],
        limit=10,
    )

    print(f"  {'#':>3} {'Sessions':>10} {'Users':>8}  ランディングページ")
    print(f"  {'---':>3} {'----------':>10} {'--------':>8}  {'---'*15}")
    for i, row in enumerate(response.rows, 1):
        page = row.dimension_values[0].value[:60]
        sessions = row.metric_values[0].value
        users = row.metric_values[1].value
        print(f"  {i:>3} {sessions:>10} {users:>8}  {page}")


def main():
    property_id = get_property_id()
    client = get_client()

    # 過去30日間
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    date_range = (start_date, end_date)

    print(f"\nGA4 Property ID: {property_id}")
    print(f"期間: {start_date} ~ {end_date}")

    report_overview(client, property_id, date_range)
    report_daily_trend(client, property_id, date_range)
    report_top_pages(client, property_id, date_range, limit=20)
    report_traffic_sources(client, property_id, date_range)
    report_devices(client, property_id, date_range)
    report_search_queries(client, property_id, date_range)

    print("\n" + "=" * 60)
    print("  レポート完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
