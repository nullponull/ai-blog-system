# GA4 Data API セットアップガイド

## 現状

| 項目 | 値 |
|------|------|
| GA4 Measurement ID | G-B86T05DQQ7 |
| GA4 Property ID | **未確認** (手動確認が必要) |
| AdSense Publisher ID | ca-pub-2749909945906194 |
| GA4所有者アカウント | pokesapo0@gmail.com |
| GCPプロジェクト | gemini-api-project-470216 |
| サービスアカウント | ga4-reader@gemini-api-project-470216.iam.gserviceaccount.com |
| SAキーファイル | /home/sol/.ga4_service_account.json |

## セットアップ手順 (3ステップ)

### Step 1: GA4 Property ID を確認する

1. [GA4管理画面](https://analytics.google.com/) に `pokesapo0@gmail.com` でログイン
2. 左下の歯車アイコン(管理) をクリック
3. **プロパティ設定** を開く
4. **プロパティ ID** (数字のみ、例: 123456789) をメモ

### Step 2: サービスアカウントにGA4アクセス権を付与

1. GA4管理画面 > **アカウントアクセス管理** (または プロパティアクセス管理)
2. 右上の **+** ボタン > **ユーザーを追加**
3. メールアドレス: `ga4-reader@gemini-api-project-470216.iam.gserviceaccount.com`
4. 権限: **閲覧者** (Viewer)
5. 保存

### Step 3: レポートを実行

```bash
export GA4_PROPERTY_ID="<Step1で確認したID>"
export GOOGLE_APPLICATION_CREDENTIALS="/home/sol/.ga4_service_account.json"
cd /home/sol/ai-blog-system
python3 scripts/fetch_ga4_report.py
```

## 代替手段: OAuth認証 (サービスアカウントが使えない場合)

```bash
cd /home/sol/ai-blog-system
python3 scripts/ga4_auth_setup.py
# ブラウザが開くので pokesapo0@gmail.com でログイン
# 認証完了後、~/.ga4_credentials.json に保存される

export GA4_PROPERTY_ID="<Property ID>"
export GA4_CREDENTIALS="/home/sol/.ga4_credentials.json"
python3 scripts/fetch_ga4_report.py
```

## AdSense 収益確認方法

### 方法1: AdSense ダッシュボード (推奨)
1. [Google AdSense](https://www.google.com/adsense/) に `pokesapo0@gmail.com` でログイン
2. ホーム画面で推定収益を確認
3. レポート > カスタムレポートで詳細分析

### 方法2: AdSense API (将来対応)
- AdSense Management API v2 が必要
- OAuth スコープ: `https://www.googleapis.com/auth/adsense.readonly`
- ga4_auth_setup.py の SCOPES に追加済み

### AdSense 確認ポイント
- **推定収益**: 日別/月別の収益推移
- **RPM** (Revenue Per Mille): 1000PVあたりの収益
- **CTR** (Click Through Rate): 広告クリック率
- **ads.txt**: ai-media.co.jp/ads.txt が正しく配置されているか

## レポート内容

fetch_ga4_report.py で取得できるデータ:

1. **サマリー**: PV数、アクティブユーザー、セッション数、直帰率、新規ユーザー
2. **日別トレンド**: 過去30日の日別PV・ユーザー推移
3. **上位記事ランキング**: PV順TOP20 (タイトル、パス、滞在時間)
4. **流入元**: Organic Search, Direct, Social, Referral の内訳
5. **デバイス別**: Mobile / Desktop / Tablet の比率
6. **ランディングページ**: 検索流入のトップページ

## トラブルシューティング

### "Request had insufficient authentication scopes"
- 既存のGemini CLI OAuth (cloud-platform scope) では GA4 API にアクセスできない
- サービスアカウント認証 または ga4_auth_setup.py による専用OAuth認証が必要

### "User does not have sufficient permissions"
- サービスアカウントのメールが GA4 プロパティに追加されていない
- Step 2 を実行してください

### Property ID がわからない
- GA4 管理画面で確認 (Measurement ID G-xxx とは別の数字)
- 管理 > プロパティ設定 > プロパティ ID
