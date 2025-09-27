# 実装計画書

このドキュメントは、「ブログ更新通知スクリプト」の開発に関する実装タスクをまとめたものです。

## フェーズ1: プロジェクトの初期設定と環境構築

- [x] 1-1. Gitリポジトリの初期化
- [x] 1-2. ディレクトリ構造の作成 (`.github/workflows/`)
- [x] 1-3. 空のファイルを作成
    - [x] `main.py`
    - [x] `requirements.txt`
    - [x] `.github/workflows/main.yml`
    - [x] `last_article.txt` (空またはダミーURLを記載)
    - [x] `.gitignore` (Pythonのキャッシュファイルなどを除外)
- [x] 1-4. `requirements.txt`に必要なライブラリを記述
    - [x] `requests`
    - [x] `beautifulsoup4`

## フェーズ2: Webサイトからの情報取得機能（`main.py`）

- [x] 2-1. `last_article.txt` から前回の記事URLを読み込む関数の実装
    - [x] ファイルが存在しない場合の例外処理を含む
- [x] 2-2. 対象のブログサイト (`https://www.t-p-o.com/blog/`) のHTMLを取得する関数の実装
    - [x] `requests`ライブラリを使用
    - [x] 接続エラーなどに対する例外処理を含む
- [x] 2-3. HTMLを解析し、最新記事の情報を抽出する関数の実装
    - [x] `BeautifulSoup`ライブラリを使用
    - [x] 最新記事の要素を特定するセレクタを決定
    - [x] 記事タイトルを抽出
    - [x] 記事URLを抽出
    - [x] サムネイル画像のURLを抽出
    - [x] 抽出した情報を辞書などのデータ構造に格納

## フェーズ3: メール送信機能の実装（`main.py`）

- [x] 3-1. 環境変数からGmailの認証情報を読み込む処理の実装
    - [x] 送信元メールアドレス
    - [x] アプリパスワード
    - [x] 送信先メールアドレス
- [x] 3-2. メール本文を生成する関数の実装
    - [x] HTML形式でメールを作成
    - [x] 記事タイトル、URL、サムネイル画像 (`<img>`タグ) を本文に含める
- [x] 3-3. GmailのSMTPサーバー経由でメールを送信する関数の実装
    - [x] `smtplib` を使用
    - [x] `STARTTLS`で接続を暗号化
    - [x] SMTP認証（ログイン処理）
    - [x] メール送信処理
    - [x] サーバー切断処理 (`quit()`)

## フェーズ4: メイン処理の組み立て（`main.py`）

- [x] 4-1. 上記で作成した関数を呼び出し、全体の処理フローを実装
- [x] 4-2. 取得した最新記事URLと、`last_article.txt`から読み込んだURLを比較するロジックを実装
- [x] 4-3. URLが変更されていた（新しい記事があった）場合のみ、以下の処理を実行
    - [x] 4-3-1. メール送信関数を呼び出す
    - [x] 4-3-2. `last_article.txt` に新しいURLを書き込む関数を呼び出す
- [x] 4-4. URLに変更がなかった場合は、その旨をコンソールに出力して終了
- [x] 4-5. 処理の開始、終了、更新の有無などを知らせるログ出力処理を追加

## フェーズ5: GitHub Actions の設定（`.github/workflows/main.yml`）

- [x] 5-1. ワークフローの基本設定
    - [x] ワークフロー名を設定
    - [x] `on`トリガーを設定
        - [x] `schedule` (cron: `0 0 * * *` など)
        - [x] `workflow_dispatch` (手動実行用)
- [x] 5-2. ジョブのステップを定義
    - [x] 5-2-1. `actions/checkout@v4` を使用してリポジトリをチェックアウト
    - [x] 5-2-2. `actions/setup-python@v5` を使用してPython環境をセットアップ
    - [x] 5-2-3. `pip install -r requirements.txt` を実行して依存ライブラリをインストール
    - [x] 5-2-4. Pythonスクリプト (`main.py`) を実行
        - [x] `env`ブロックでGitHub Secretsを環境変数としてスクリプトに渡す (`GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `RECIPIENT_EMAIL`)
    - [x] 5-2-5. `last_article.txt` の変更を検知し、変更があった場合のみコミット＆プッシュするステップを追加
        - [x] `git config` でコミットユーザー情報を設定
        - [x] `git add`, `git commit`, `git push` を実行

## フェーズ6: ドキュメント作成と最終確認

- [x] 6-1. `README.md` ファイルの作成
    - [x] プロジェクトの概要説明
    - [x] 使い方（セットアップ方法）
    - [x] 設定が必要なGitHub Secrets（`GMAIL_ADDRESS`, `GMAIL_APP_PASSWORD`, `RECIPIENT_EMAIL`）に関する説明
- [x] 6-2. 手動実行 (`workflow_dispatch`) で全体の動作テスト
- [x] 6-3. コード全体のレビューとリファクタリング