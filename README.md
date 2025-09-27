# ブログ更新通知スクリプト

## 概要

このプロジェクトは、指定されたブログ（[タカギプランニングオフィスブログ](https://www.t-p-o.com/blog/)）を定期的にチェックし、新しい記事が投稿された場合にGmail経由で通知を送るPythonスクリプトです。

処理はGitHub Actionsによって自動化されており、毎日定刻に実行されます。

## 主な機能

- 指定されたWebページから最新のブログ記事情報を取得
- 前回の記事情報と比較し、更新があるかを確認
- 更新があった場合、指定されたGmailアカウントから通知メールを送信
- GitHub Actionsによる定期的な自動実行

## セットアップ方法

この自動通知システムを利用するには、以下の手順でセットアップが必要です。

1.  **リポジトリの準備**
    このリポジトリを自身のGitHubアカウントにフォークまたはクローンします。

2.  **GitHub Secretsの設定**
    本スクリプトは、メール送信のためにGmailの認証情報を必要とします。安全に情報を管理するため、GitHubリポジトリのSecretsに以下の3つの情報を登録してください。

    リポジトリの `Settings` > `Secrets and variables` > `Actions` に移動し、`New repository secret` ボタンから登録します。

    - `GMAIL_ADDRESS`
      - **説明**: 通知メールの送信元となるGmailアドレス。
      - **例**: `your.email@gmail.com`

    - `GMAIL_APP_PASSWORD`
      - **説明**: 送信元Gmailアカウントのアプリパスワード。通常のログインパスワードとは異なります。アプリパスワードはGoogleアカウントのセキュリティ設定から生成できます。
      - **参考**: [アプリ パスワードでログイン - Google アカウント ヘルプ](https://support.google.com/accounts/answer/185833)

    - `RECIPIENT_EMAIL`
      - **説明**: 通知メールを受け取る宛先のメールアドレス。
      - **例**: `notify.me@example.com`

3.  **GitHub Actionsの有効化**
    上記の設定が完了すると、`main.yml`ワークフローが有効になります。デフォルトでは、毎日午前9時（JST）に自動実行されます。

## 手動での動作確認

すぐに動作を確認したい場合は、以下の手順で手動実行が可能です。

1.  リポジトリの **Actions** タブに移動します。
2.  左側のサイドバーから **Blog Update Checker** ワークフローを選択します。
3.  **Run workflow** というドロップダウンボタンが表示されるので、それをクリックしてワークフローを開始します。

## ローカル環境での実行（任意）

ローカルマシンでスクリプトを直接実行することも可能です。

1.  **依存ライブラリのインストール:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **環境変数の設定:**
    ```bash
    export GMAIL_ADDRESS="your.email@gmail.com"
    export GMAIL_APP_PASSWORD="your_app_password"
    export RECIPIENT_EMAIL="notify.me@example.com"
    ```

3.  **スクリプトの実行:**
    ```bash
    python3 main.py
    ```
