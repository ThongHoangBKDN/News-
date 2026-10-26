import os
import requests
import feedparser

# Lấy các biến môi trường từ GitHub Actions Secrets
ONESIGNAL_APP_ID = os.environ.get("ONESIGNAL_APP_ID")
ONESIGNAL_REST_KEY = os.environ.get("ONESIGNAL_REST_KEY")
SITE_URL = os.environ.get("SITE_URL", "https://news-3sz.pages.dev")

# Danh sách nguồn RSS mẫu (bạn có thể thay đổi link RSS tùy ý)
RSS_FEEDS = [
    "https://vnexpress.net/rss/tin-moi-nhat.rss"
]

def fetch_news():
    articles = []
    for url in RSS_FEEDS:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]:  # Lấy 5 tin mới nhất mỗi nguồn
                articles.append({
                    "title": entry.title,
                    "link": entry.link
                })
            print(f"OK: Đã lấy tin từ {url}")
        except Exception as e:
            print(f"LỖI: Không thể lấy tin từ {url} - {e}")
    return articles

def generate_html(articles):
    items_html = ""
    for art in articles:
        items_html += f'<li><a href="{art["link"]}" target="_blank">{art["title"]}</a></li>\n'

    html_content = f"""<!DOCTYPE html>
<html lang="vi">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bản Tin Sáng</title>
    <script src="https://cdn.onesignal.com/sdks/web/v16/OneSignalSDK.page.js" defer></script>
    <script>
      window.OneSignalDeferred = window.OneSignalDeferred || [];
      window.OneSignalDeferred.push(async function(OneSignal) {{
        await OneSignal.init({{
          appId: "{ONESIGNAL_APP_ID}",
        }});
      }});
    </script>
</head>
<body>
    <h1>Bản Tin Tổng Hợp Mới Nhất</h1>
    <ul>
        {items_html}
    </ul>
</body>
</html>
"""
    # Ghi đè nội dung vào file public/index.html
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print("Đã cập nhật file public/index.html thành công!")

def send_onesignal_notification():
    if not ONESIGNAL_APP_ID or not ONESIGNAL_REST_KEY:
        print("Thiếu thông tin OneSignal App ID hoặc Rest Key, bỏ qua bước gửi thông báo.")
        return

    url = "https://onesignal.com/api/v1/notifications"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Authorization": f"Basic {ONESIGNAL_REST_KEY}"
    }
    payload = {
        "app_id": ONESIGNAL_APP_ID,
        "included_segments": ["All"],
        "contents": {"en": "Bản tin sáng mới nhất đã được cập nhật. Nhấn vào để xem ngay!"},
        "headings": {"en": "Bản Tin Sáng ☀️"},
        "url": SITE_URL
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            print("Đã gửi thông báo OneSignal thành công!")
        else:
            print(f"Lỗi gửi thông báo: {response.text}")
    except Exception as e:
        print(f"Lỗi kết nối tới OneSignal: {e}")

if __name__ == "__main__":
    news = fetch_news()
    if news:
        generate_html(news)
        send_onesignal_notification()
    else:
        print("Không có bài viết nào được cào về.")
