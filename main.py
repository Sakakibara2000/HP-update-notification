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
import json
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- グローバル設定 ---
LAST_ARTICLE_FILE = 'last_article.txt'  # 前回記事のURLを保存するファイル
BLOG_URL = 'https://www.t-p-o.com/blog/'  # チェック対象のブログURL

# UR賃貸物件設定
UR_STATE_FILE = 'ur_properties.json'  # UR物件の状態を保存するファイル
TARGET_UR_PROPERTIES = {
    '20_1830': {'ward': '品川区', 'name': '大井六丁目'},
    '20_3550': {'ward': '品川区', 'name': '品川八潮パークタウン 潮路北第二ハイツ'},
    '20_3640': {'ward': '品川区', 'name': '品川八潮パークタウン 潮路南第一ハイツ'},
    '20_3810': {'ward': '品川区', 'name': '品川八潮パークタウン 潮路中央ハイツ'},
    '20_7220': {'ward': '品川区', 'name': 'コンフォール品川西大井'},
    '20_4920': {'ward': '港区', 'name': 'デュプレ芝浦'},
    '20_5180': {'ward': '目黒区', 'name': '恵比寿ビュータワー'},
    '20_6480': {'ward': '目黒区', 'name': '中目黒ゲートタウンハイツ'},
    '20_7090': {'ward': '目黒区', 'name': '中目黒アトラスタワー'},
}

# --- ライブラリの動的インポート ---
# beautifulsoup4がインストールされていなくても動作するように、インポートを試みる
try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

# Seleniumのインポート
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False
    print("Warning: Selenium not available. UR vacancy checking will be disabled.")

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

# --- UR物件状態管理関数 ---

def read_ur_state():
    """
    ur_properties.json から前回のUR物件状態を読み込む。
    ファイルが存在しない場合は空の構造を返す。
    """
    if not os.path.exists(UR_STATE_FILE):
        return {'last_updated': None, 'properties': {}}

    try:
        with open(UR_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error reading UR state file: {e}")
        return {'last_updated': None, 'properties': {}}

def write_ur_state(state):
    """
    ur_properties.json に新しい状態を書き込む。
    """
    try:
        with open(UR_STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Error writing UR state file: {e}")

# --- UR物件空室取得関数（Selenium使用） ---

def setup_driver():
    """
    Seleniumのheadless Chromeドライバーをセットアップする。
    """
    if not SELENIUM_AVAILABLE:
        raise ImportError("Selenium is not available")

    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    # User-Agentを設定してブラウザとして認識させる
    options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.set_page_load_timeout(30)
        return driver
    except Exception as e:
        print(f"Error setting up Chrome driver: {e}")
        # GitHub Actionsの環境ではchromium-chromedriverを使用
        try:
            options.binary_location = '/usr/bin/chromium-browser'
            service = Service('/usr/bin/chromedriver')
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            return driver
        except Exception as e2:
            print(f"Error with fallback driver: {e2}")
            raise

def fetch_vacancy_count(property_id):
    """
    指定されたUR物件IDの空室数を取得する。
    Seleniumを使ってページを読み込み、レンダリング後のHTMLから空室数を抽出する。
    """
    if not SELENIUM_AVAILABLE:
        print("Selenium not available, skipping vacancy fetch")
        return 0

    driver = None
    try:
        driver = setup_driver()
        url = f"https://www.ur-net.go.jp/chintai/kanto/tokyo/{property_id}.html"
        print(f"  Fetching: {url}")

        driver.get(url)

        # JavaScriptのレンダリングを待つ
        import time
        time.sleep(3)

        # 空室がない場合のメッセージを確認
        try:
            no_vacancy_element = driver.find_element(By.XPATH, "//*[contains(text(), '当サイトからすぐにご案内できるお部屋がございません')]")
            if no_vacancy_element:
                print(f"    No vacancies available (message found)")
                return 0
        except:
            pass

        # 空室テーブルの行数をカウント
        # 通常、空室がある場合は「お部屋情報」テーブルに行が表示される
        try:
            # テーブルの行を探す（ヘッダー行を除く）
            vacancy_rows = driver.find_elements(By.CSS_SELECTOR, "table.bukken_table tbody tr")
            # データ行のみカウント（クラス名や内容で絞り込み）
            vacancy_count = 0
            for row in vacancy_rows:
                # 行にリンクやデータが含まれている場合のみカウント
                if row.find_elements(By.TAG_NAME, "a") or row.find_elements(By.CLASS_NAME, "price"):
                    vacancy_count += 1

            print(f"    Vacancy count: {vacancy_count}")
            return vacancy_count
        except Exception as e:
            print(f"    Error parsing vacancy table: {e}")

            # フォールバック：「○件」のような表示を探す
            try:
                page_text = driver.page_source
                # "空室" や "募集中" などのキーワードと数字を探す
                import re
                match = re.search(r'(\d+)\s*件', page_text)
                if match:
                    count = int(match.group(1))
                    print(f"    Found vacancy count via text pattern: {count}")
                    return count
            except Exception as e2:
                print(f"    Fallback parsing also failed: {e2}")

            return 0

    except Exception as e:
        print(f"  Error fetching vacancy for {property_id}: {e}")
        return 0
    finally:
        if driver:
            driver.quit()

def detect_vacancy_increases(old_state, new_state):
    """
    前回の状態と現在の状態を比較し、空室が増えた物件のリストを返す。
    """
    increases = []

    for prop_id in TARGET_UR_PROPERTIES:
        old_count = old_state.get(prop_id, {}).get('vacancy_count', 0)
        new_count = new_state.get(prop_id, {}).get('vacancy_count', 0)

        if new_count > old_count:
            increases.append({
                'property_id': prop_id,
                'old_count': old_count,
                'new_count': new_count,
                'name': new_state[prop_id]['name'],
                'ward': new_state[prop_id]['ward'],
                'url': new_state[prop_id]['url']
            })

    return increases

def create_ur_email_body(increases, recipient_email, sender_email):
    """
    UR空室増加通知のHTML形式のメール本文を生成する。
    """
    subject = f"UR空室情報更新: {len(increases)}件の物件に空きが増えました"

    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['To'] = recipient_email
    msg['From'] = sender_email

    html_body = """
    <html>
    <body>
        <h2>🏠 UR空室情報更新通知</h2>
        <h3>空室が増えた物件</h3>
        <ul>
    """

    for item in increases:
        html_body += f"""
            <li>
                <strong>{item['name']}</strong> ({item['ward']})<br>
                空室数: {item['old_count']}室 → {item['new_count']}室<br>
                <a href="{item['url']}">詳細を見る</a>
            </li>
        """

    html_body += """
        </ul>
        <p style="margin-top: 30px; color: #666; font-size: 12px;">
            このメールは自動送信されています。<br>
            対象エリア: 品川区、港区、目黒区
        </p>
    </body>
    </html>
    """

    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
    return msg

def check_ur_vacancies():
    """
    UR物件の空室状況をチェックし、空室が増えた場合は通知する。
    """
    if not SELENIUM_AVAILABLE:
        print("Selenium not available, skipping UR vacancy check")
        return

    print("--- UR Vacancy Check Start ---")

    # 前回の状態を読み込む
    old_state = read_ur_state()
    print(f"Loaded previous state for {len(old_state.get('properties', {}))} properties")

    # 現在の空室データを取得
    new_state = {
        'last_updated': datetime.now().isoformat(),
        'properties': {}
    }

    for prop_id, info in TARGET_UR_PROPERTIES.items():
        print(f"Checking property: {info['name']} ({prop_id})")
        try:
            vacancy_count = fetch_vacancy_count(prop_id)
            new_state['properties'][prop_id] = {
                'name': info['name'],
                'ward': info['ward'],
                'vacancy_count': vacancy_count,
                'url': f"https://www.ur-net.go.jp/chintai/kanto/tokyo/{prop_id}.html",
                'last_changed': datetime.now().isoformat()
            }
        except Exception as e:
            print(f"Error fetching {prop_id}: {e}")
            # エラーが発生した場合、古いデータがあればそれを使用
            if prop_id in old_state.get('properties', {}):
                print(f"  Using old data for {prop_id}")
                new_state['properties'][prop_id] = old_state['properties'][prop_id]
            else:
                # データがない場合は0として記録
                new_state['properties'][prop_id] = {
                    'name': info['name'],
                    'ward': info['ward'],
                    'vacancy_count': 0,
                    'url': f"https://www.ur-net.go.jp/chintai/kanto/tokyo/{prop_id}.html",
                    'last_changed': datetime.now().isoformat()
                }

    # 空室の増加を検出
    increases = detect_vacancy_increases(
        old_state.get('properties', {}),
        new_state['properties']
    )

    # 増加があった場合は通知を送信
    if increases:
        print(f"Found {len(increases)} properties with increased vacancies:")
        for item in increases:
            print(f"  - {item['name']}: {item['old_count']} → {item['new_count']}")

        # メール送信
        gmail_address, gmail_app_password, recipient_email = get_email_credentials()
        if gmail_address:
            print("Sending UR vacancy notification email...")
            email_msg = create_ur_email_body(increases, recipient_email, gmail_address)
            send_email(email_msg, gmail_address, gmail_app_password)
        else:
            print("Skipping email notification because credentials are not set.")
    else:
        print("No vacancy increases detected")

    # 状態ファイルを更新（変更がなくても最新の状態を保存）
    print(f"Updating UR state file...")
    write_ur_state(new_state)

    print("--- UR Vacancy Check End ---")

# --- メイン処理 ---

def check_blog_updates():
    """
    ブログの更新をチェックし、新しい記事があれば通知する。
    """
    print("--- Blog Update Check Start ---")

    # 1. 最新記事の情報を取得
    print(f"Fetching latest article from {BLOG_URL}...")
    html = fetch_blog_html(BLOG_URL)
    if not html:
        print("Error: Could not fetch blog page.")
        return

    latest_article = parse_latest_article(html)
    if not latest_article or latest_article.get('url') == 'No URL':
        print("Error: Could not parse the latest article.")
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
            print("Creating and sending blog update email...")
            email_msg = create_email_body(latest_article, recipient_email, gmail_address)
            send_email(email_msg, gmail_address, gmail_app_password)
        else:
            print("Skipping email notification because credentials are not set.")

        # 4. 最後に読み込んだ記事のURLをファイルに保存
        print(f"Updating last article URL to: {latest_article['url']}")
        write_last_article_url(latest_article['url'])

    print("--- Blog Update Check End ---")

def main():
    """
    スクリプトのメイン処理フロー
    ブログ更新とUR空室状況の両方をチェックする。
    """
    print("=== Notification Script Start ===")
    print()

    # ブログ更新チェック
    check_blog_updates()
    print()

    # UR空室チェック
    check_ur_vacancies()
    print()

    print("=== Notification Script End ===")

if __name__ == '__main__':
    main()
