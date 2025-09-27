# -*- coding: utf-8 -*-

"""
ブログの更新をチェックし、新しい記事があればGmailで通知するスクリプト。

このスクリプトは、以下の処理を行います:
1. 指定されたブログURLからHTMLを取得します。
2. HTMLを解析し、最新記事のタイトル、URL、サムネイル画像を取得します。
   - beautifulsoup4が利用可能な場合はそれを使用し、なければ正規表現での解析にフォールバックします。
3. 前回取得した記事のURLと比較し、更新があるかを確認します。
4. 更新があった場合、環境変数から取得したGmailアカウント情報を使って通知メールを送信します。
5. 最新の記事URLをファイルに保存し、次回の実行に備えます。
"""

import urllib.request
import urllib.error
import os
import re
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- グローバル設定 ---
LAST_ARTICLE_FILE = 'last_article.txt'  # 前回記事のURLを保存するファイル
BLOG_URL = 'https://www.t-p-o.com/blog/'  # チェック対象のブログURL

# --- ライブラリの動的インポート ---
# beautifulsoup4がインストールされていなくても動作するように、インポートを試みる
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# --- 関数定義 ---

def read_last_article_url():
    """
    last_article.txt から前回の記事URLを読み込む。
    ファイルが存在しない場合はNoneを返す。
    """
    if not os.path.exists(LAST_ARTICLE_FILE):
        return None
    with open(LAST_ARTICLE_FILE, 'r', encoding='utf-8') as f:
        return f.read().strip()

def write_last_article_url(url):
    """
    last_article.txt に新しいURLを書き込む。
    """
    with open(LAST_ARTICLE_FILE, 'w', encoding='utf-8') as f:
        f.write(url)

def fetch_blog_html(url):
    """
    指定されたURLのHTMLコンテンツを取得する。
    標準ライブラリ urllib を使用。
    """
    try:
        with urllib.request.urlopen(url) as response:
            if response.getcode() == 200:
                return response.read().decode('utf-8')
            else:
                print(f"Error fetching blog HTML: Status code {response.getcode()}")
                return None
    except urllib.error.URLError as e:
        print(f"Error fetching blog HTML: {e}")
        return None

# --- HTML解析関数 ---

def parse_latest_article_with_bs(html):
    """
    BeautifulSoupを使ってHTMLを解析し、最新記事の情報を抽出する。
    (注: 現在の実行環境ではbeautifulsoup4が使えないため、この関数は呼び出されない)
    """
    soup = BeautifulSoup(html, 'html.parser')
    # セレクタはターゲットサイトの構造に合わせて調整が必要
    latest_article_element = soup.select_one('li[id^="post-"]')

    if not latest_article_element:
        return None

    title_element = latest_article_element.select_one('h2')
    url_element = latest_article_element.select_one('.blog-more a')
    thumbnail_element = latest_article_element.select_one('figure.thumb img')

    title = title_element.get_text(strip=True) if title_element else 'No Title'
    url = url_element['href'] if url_element and 'href' in url_element.attrs else 'No URL'
    thumbnail_url = thumbnail_element['src'] if thumbnail_element and 'src' in thumbnail_element.attrs else 'No Thumbnail'

    # URLが相対パスの場合、絶対パスに変換
    if url.startswith('/'):
        url = "https://www.t-p-o.com" + url

    return {
        'title': title,
        'url': url,
        'thumbnail_url': thumbnail_url
    }

def parse_latest_article_with_regex(html):
    """
    正規表現を使ってHTMLを解析し、最新記事の情報を抽出する。
    HTML構造の変更に弱いため、あくまでBeautifulSoupが使えない場合のフォールバック。
    """
    # 最新の記事を含む可能性が最も高い、最初の<li>ブロックを特定
    item_match = re.search(r'<li id="post-.*?">.*?</li>', html, re.DOTALL)
    if not item_match:
        print("Regex Error: Could not find the latest article block (li id='post-...').")
        return None
    
    item_html = item_match.group(0)

    # ブロック内からタイトルを抽出
    title_match = re.search(r'<h2>(.*?)</h2>', item_html, re.DOTALL)
    title = title_match.group(1).strip() if title_match else 'No Title'

    # ブロック内から記事URLを抽出
    url_match = re.search(r'<div class="blog-more"><a href="(.*?)">MORE</a></div>', item_html, re.DOTALL)
    if url_match:
        relative_url = url_match.group(1)
        # URLが相対パスの場合、絶対パスに変換
        if relative_url.startswith('/'):
            url = "https://www.t-p-o.com" + relative_url
        else:
            url = relative_url
    else:
        url = 'No URL'

    # ブロック内からサムネイルURLを抽出
    thumb_match = re.search(r'<figure class="thumb">.*?<img.*?src="(.*?)".*?>.*?</figure>', item_html, re.DOTALL)
    thumbnail_url = thumb_match.group(1) if thumb_match else 'No Thumbnail'

    if title == 'No Title' or url == 'No URL':
        print(f"Regex Error: Could not parse title or URL. Title Match: {title_match}, URL Match: {url_match}")
        return None

    return {
        'title': title,
        'url': url,
        'thumbnail_url': thumbnail_url
    }

def parse_latest_article(html):
    """
    HTMLを解析し、最新記事の情報を抽出する。
    BeautifulSoupが利用可能であればそれを使用し、なければ正規表現での解析を試みる。
    """
    if not html:
        return None

    if BeautifulSoup:
        print("Parsing with BeautifulSoup...")
        return parse_latest_article_with_bs(html)
    else:
        # GitHub Actions環境では、pipでライブラリがインストールされる想定
        # ローカルのCLI環境ではこちらが実行される
        print("BeautifulSoup not found. Parsing with Regex (might be unstable)...")
        return parse_latest_article_with_regex(html)

# --- メール送信用関数 ---

def get_email_credentials():
    """
    環境変数からGmailの認証情報を読み込む。
    GitHub ActionsのSecretsに設定することを想定。
    """
    gmail_address = os.getenv('GMAIL_ADDRESS')
    gmail_app_password = os.getenv('GMAIL_APP_PASSWORD')
    recipient_email = os.getenv('RECIPIENT_EMAIL')

    if not all([gmail_address, gmail_app_password, recipient_email]):
        print("Warning: Email credentials (GMAIL_ADDRESS, GMAIL_APP_PASSWORD, RECIPIENT_EMAIL) are not set.")
        return None, None, None

    return gmail_address, gmail_app_password, recipient_email

def create_email_body(article, recipient_email, sender_email):
    """
    HTML形式のメール本文を生成する。
    """
    subject = f"ブログ更新通知: {article['title']}"
    
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['To'] = recipient_email
    msg['From'] = sender_email

    html_body = f"""
    <html>
    <body>
        <h2>新しい記事が投稿されました！</h2>
        <h3>{article['title']}</h3>
        <p><a href="{article['url']}">記事を読む</a></p>
        <p><img src="{article['thumbnail_url']}" alt="Thumbnail" width="300"></p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    return msg

def send_email(message, sender_email, sender_password):
    """
    GmailのSMTPサーバー経由でメールを送信する。
    """
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(message)
            print("Email sent successfully!")
    except smtplib.SMTPException as e:
        print(f"Error sending email: {e}")
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")

# --- メイン処理 ---

def main():
    """
    スクリプトのメイン処理フロー
    """
    print("--- Blog Update Notification Script Start ---")

    # 1. 最新記事の情報を取得
    print(f"Fetching latest article from {BLOG_URL}...")
    html = fetch_blog_html(BLOG_URL)
    if not html:
        print("Error: Could not fetch blog page. Exiting.")
        return

    latest_article = parse_latest_article(html)
    if not latest_article or latest_article.get('url') == 'No URL':
        print("Error: Could not parse the latest article. Exiting.")
        return
    
    print("Successfully fetched and parsed the latest article.")
    print(f"  - Title: {latest_article['title']}")
    print(f"  - URL: {latest_article['url']}")

    # 2. 前回の記事URLと比較
    last_url = read_last_article_url()
    print(f"Last article URL was: {last_url}")

    if latest_article['url'] == last_url:
        print("No new articles found.")
    else:
        print("Found a new article!")
        
        # 3. メール送信処理
        gmail_address, gmail_app_password, recipient_email = get_email_credentials()
        if gmail_address:
            print("Creating and sending email...")
            email_msg = create_email_body(latest_article, recipient_email, gmail_address)
            send_email(email_msg, gmail_address, gmail_app_password)
        else:
            print("Skipping email notification because credentials are not set.")

        # 4. 最後に読み込んだ記事のURLをファイルに保存
        print(f"Updating last article URL to: {latest_article['url']}")
        write_last_article_url(latest_article['url'])

    print("--- Blog Update Notification Script End ---")

if __name__ == '__main__':
    main()
