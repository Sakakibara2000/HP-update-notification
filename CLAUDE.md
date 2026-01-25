# CLAUDE.md - Project Context for AI Assistant

## プロジェクト概要

このプロジェクトは、複数のWebサイトの更新を監視し、変更があった場合にGmail経由でメール通知を送る自動化システムです。GitHub Actionsで毎日自動実行されます。

**目的**: HP（ホームページ）の更新を監視して、重要な情報をタイムリーにキャッチする

## 現在の監視対象

### 1. ブログ更新監視
- **対象**: タカギプランニングオフィスブログ (https://www.t-p-o.com/blog/)
- **検知条件**: 新しい記事が投稿されたとき
- **状態管理**: `last_article.txt` - 最後にチェックした記事のURL
- **通知内容**: 記事タイトル、URL、サムネイル画像

### 2. UR賃貸空室監視
- **対象**: 品川区・港区・目黒区のUR賃貸物件（9物件）
- **検知条件**: 空室数が増加したとき（0→1、1→2など）
- **状態管理**: `ur_properties.json` - 各物件の空室数と最終更新日時
- **通知内容**: 物件名、所在区、空室数の変化、詳細ページURL

## ファイル構成

```
HP-update-notification/
├── main.py                      # メインスクリプト（全てのロジック）
├── requirements.txt             # Python依存関係
├── last_article.txt            # ブログ記事の状態（1行：URL）
├── ur_properties.json          # UR物件の状態（JSON形式）
├── .github/workflows/main.yml  # GitHub Actions設定
├── README.md                   # ユーザー向けドキュメント
├── IMPLEMENTATION_PLAN.md      # 実装計画書（参考用）
└── CLAUDE.md                   # このファイル（AI向けコンテキスト）
```

## 技術スタック

- **Python 3.x**
- **BeautifulSoup4**: HTML解析（ブログ用）
- **Selenium + webdriver-manager**: 動的コンテンツの取得（UR用）
- **smtplib**: Gmail SMTP経由のメール送信
- **GitHub Actions**: 自動実行環境（1日3回: 6:00、12:00、18:00 JST）

## main.pyの構造

### グローバル設定
```python
LAST_ARTICLE_FILE = 'last_article.txt'
BLOG_URL = 'https://www.t-p-o.com/blog/'
UR_STATE_FILE = 'ur_properties.json'
TARGET_UR_PROPERTIES = {...}  # 9物件の定義
```

### 主要な関数グループ

**共通ユーティリティ:**
- `get_email_credentials()` - 環境変数からGmail認証情報を取得
- `send_email()` - SMTPでメール送信

**ブログチェック関連:**
- `fetch_blog_html()` - urllib でHTMLを取得
- `parse_latest_article()` - BeautifulSoup or 正規表現で記事を抽出
- `read_last_article_url()` / `write_last_article_url()` - 状態管理
- `create_email_body()` - ブログ更新メールのHTML生成
- `check_blog_updates()` - ブログチェックのメイン処理

**UR空室チェック関連:**
- `setup_driver()` - Selenium headless Chromeのセットアップ
- `fetch_vacancy_count(property_id)` - Seleniumで空室数を取得
- `read_ur_state()` / `write_ur_state()` - JSON状態管理
- `detect_vacancy_increases()` - 空室増加の検出
- `create_ur_email_body()` - UR空室メールのHTML生成
- `check_ur_vacancies()` - UR空室チェックのメイン処理

**メイン処理:**
- `main()` - `check_blog_updates()` と `check_ur_vacancies()` を順次実行

## 監視対象のUR物件（9物件）

### 品川区（5物件）
- 20_1830: 大井六丁目
- 20_3550: 品川八潮パークタウン 潮路北第二ハイツ
- 20_3640: 品川八潮パークタウン 潮路南第一ハイツ
- 20_3810: 品川八潮パークタウン 潮路中央ハイツ
- 20_7220: コンフォール品川西大井

### 港区（1物件）
- 20_4920: デュプレ芝浦

### 目黒区（3物件）
- 20_5180: 恵比寿ビュータワー
- 20_6480: 中目黒ゲートタウンハイツ
- 20_7090: 中目黒アトラスタワー

## GitHub Actions設定

**実行スケジュール**: 1日3回 21:00, 3:00, 9:00 UTC（日本時間 6:00, 12:00, 18:00）

**環境変数（GitHub Secrets）**:
- `GMAIL_ADDRESS` - 送信元Gmailアドレス
- `GMAIL_APP_PASSWORD` - Gmailアプリパスワード
- `RECIPIENT_EMAIL` - 通知先メールアドレス

**ワークフローステップ**:
1. リポジトリをチェックアウト
2. Python 3.xをセットアップ
3. 依存関係をインストール（pip install）
4. Chrome/ChromeDriverをインストール（apt-get）
5. main.pyを実行（環境変数を渡す）
6. 変更があれば`last_article.txt`と`ur_properties.json`をコミット・プッシュ

## 重要な実装詳細

### 1. ブログ解析のフォールバック
- BeautifulSoup4が利用可能ならそれを使用
- なければ正規表現で解析（`parse_latest_article_with_regex()`）

### 2. Seleniumの環境適応
- `webdriver-manager`で自動的にChromeDriverをダウンロード
- GitHub Actions環境では`/usr/bin/chromedriver`をフォールバックで使用
- headlessモード、sandboxなしで実行

### 3. エラーハンドリング
- 1つの物件の取得に失敗しても、他の物件のチェックは継続
- Seleniumが利用できない場合、UR空室チェックをスキップ
- ネットワークエラー時は古いデータを保持

### 4. 通知の独立性
- ブログとURは別々のメールで送信
- 一方が失敗してももう一方は実行される
- どちらも更新がない場合はメールを送信しない

## 状態ファイルのフォーマット

### last_article.txt
```
https://www.t-p-o.com/blog/31973
```
単一行のURL

### ur_properties.json
```json
{
  "last_updated": "2026-01-25T15:30:00",
  "properties": {
    "20_3550": {
      "name": "品川八潮パークタウン 潮路北第二ハイツ",
      "ward": "品川区",
      "vacancy_count": 2,
      "last_changed": "2026-01-25T10:00:00",
      "url": "https://www.ur-net.go.jp/chintai/kanto/tokyo/20_3550.html"
    }
  }
}
```

## 今後の拡張可能性

### 新しい監視対象を追加する場合

1. **新しいチェッカー関数を追加**
   ```python
   def check_new_website():
       # 新しいサイトのチェック処理
       pass
   ```

2. **main()に追加**
   ```python
   def main():
       check_blog_updates()
       check_ur_vacancies()
       check_new_website()  # 追加
   ```

3. **状態管理ファイルを追加**（必要に応じて）

4. **GitHub Actions workflowを更新**
   - 新しい状態ファイルを`git add`に追加

### 既存機能の修正例

**UR物件を追加:**
- `TARGET_UR_PROPERTIES`辞書に物件を追加

**通知条件を変更:**
- `detect_vacancy_increases()`の条件を修正
- 例: 空室減少も通知 → `if new_count != old_count:`

**スケジュール変更:**
- `.github/workflows/main.yml`のcron式を編集
- 例: 1日1回（9:00 JST）に戻す → `cron: '0 0 * * *'`
- 例: 1時間ごと → `cron: '0 * * * *'`
- 現在: 1日3回（6:00, 12:00, 18:00 JST） → `cron: '0 21,3,9 * * *'`

## トラブルシューティング

### ブログ解析が失敗する
- サイトのHTML構造が変更された可能性
- `parse_latest_article_with_regex()`の正規表現を更新
- または`parse_latest_article_with_bs()`のセレクタを修正

### Seleniumがタイムアウトする
- `setup_driver()`のタイムアウト時間を延長
- `fetch_vacancy_count()`の`time.sleep(3)`を増やす

### GitHub Actionsでのみ失敗する
- ローカルとGitHub Actionsで環境が異なる
- ChromeDriverのパスやバージョンの問題
- Actionsログで詳細を確認

### メールが送信されない
- GitHub Secretsの設定を確認
- Gmailのアプリパスワードが正しいか確認
- 2段階認証が有効になっているか確認

## ローカルでのテスト方法

```bash
# 依存関係インストール
pip install -r requirements.txt

# 環境変数を設定
export GMAIL_ADDRESS="your.email@gmail.com"
export GMAIL_APP_PASSWORD="your_app_password"
export RECIPIENT_EMAIL="notify.me@example.com"

# 実行
python3 main.py

# 構文チェックのみ
python3 -m py_compile main.py
```

## コードの設計原則

1. **単一ファイル**: 全ロジックをmain.pyに集約（シンプルさ優先）
2. **モジュール化**: 各チェッカーは独立した関数として実装
3. **フォールバック**: 依存ライブラリがなくても最低限動作する
4. **エラー継続**: 一部の失敗が全体を止めない
5. **状態永続化**: Gitでバージョン管理される状態ファイル

## 参考情報

- **ブログURL**: https://www.t-p-o.com/blog/
- **UR物件リスト**: https://www.ur-net.go.jp/chintai/kanto/tokyo/list/
- **GitHub リポジトリ**: Sakakibara2000/HP-update-notification
- **実行ログ**: リポジトリのActionsタブで確認可能

---

**最終更新**: 2026-01-25
**バージョン**: v2.0 (ブログ + UR空室監視)
