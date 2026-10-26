#!/usr/bin/env python3
"""Tạo public/digest.json từ RSS các báo chính thống và gửi thông báo qua OneSignal.

Cách dùng:
  python scripts/build_digest.py morning   # lấy tin, ghi digest.json, gửi thông báo sáng
  python scripts/build_digest.py evening   # chỉ gửi thông báo nhắc buổi tối

Biến môi trường:
  ONESIGNAL_APP_ID, ONESIGNAL_REST_KEY, SITE_URL   (để gửi thông báo)
  ANTHROPIC_API_KEY                                (tùy chọn: dịch và tóm tắt tiếng Việt)
"""
import html
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

VN = timezone(timedelta(hours=7))
OUT = os.path.join(os.path.dirname(__file__), "..", "public", "digest.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; BanTinSang/1.0)"}

# (mục, nguồn, địa chỉ RSS, ngôn ngữ). Thêm hoặc bớt nguồn tại đây.
FEEDS = [
    ("Việt Nam", "VnExpress", "https://vnexpress.net/rss/thoi-su.rss", "vi"),
    ("Việt Nam", "Tuổi Trẻ", "https://tuoitre.vn/rss/thoi-su.rss", "vi"),
    ("Việt Nam", "Thanh Niên", "https://thanhnien.vn/rss/thoi-su.rss", "vi"),
    ("Việt Nam", "VietNamNet", "https://vietnamnet.vn/rss/thoi-su.rss", "vi"),
    ("Thế giới", "VnExpress", "https://vnexpress.net/rss/the-gioi.rss", "vi"),
    ("Thế giới", "Tuổi Trẻ", "https://tuoitre.vn/rss/the-gioi.rss", "vi"),
    ("Thế giới", "BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml", "en"),
    ("Thế giới", "Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "en"),
    ("Thế giới", "The Guardian", "https://www.theguardian.com/world/rss", "en"),
    ("Thế giới", "NPR", "https://feeds.npr.org/1004/rss.xml", "en"),
    ("Kinh tế", "VnExpress", "https://vnexpress.net/rss/kinh-doanh.rss", "vi"),
    ("Kinh tế", "BBC News", "https://feeds.bbci.co.uk/news/business/rss.xml", "en"),
    ("Công nghệ", "VnExpress", "https://vnexpress.net/rss/so-hoa.rss", "vi"),
    ("Công nghệ", "BBC News", "https://feeds.bbci.co.uk/news/technology/rss.xml", "en"),
    ("Thể thao", "VnExpress", "https://vnexpress.net/rss/the-thao.rss", "vi"),
    ("Thể thao", "BBC Sport", "https://feeds.bbci.co.uk/sport/rss.xml", "en"),
    ("Sức khỏe", "VnExpress", "https://vnexpress.net/rss/suc-khoe.rss", "vi"),
    ("Sức khỏe", "BBC News", "https://feeds.bbci.co.uk/news/health/rss.xml", "en"),
    ("Giải trí", "VnExpress", "https://vnexpress.net/rss/giai-tri.rss", "vi"),
]
CATEGORIES = ["Việt Nam", "Thế giới", "Kinh tế", "Công nghệ", "Thể thao", "Sức khỏe", "Giải trí"]
LIMITS = {"Việt Nam": 6, "Thế giới": 6, "Kinh tế": 3, "Công nghệ": 3, "Thể thao": 3, "Sức khỏe": 2, "Giải trí": 2}
MAX_AGE_HOURS = 36


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    return re.sub(r"\s+", " ", html.unescape(s)).strip()


def parse_date(text):
    if not text:
        return None
    try:
        d = parsedate_to_datetime(text)
    except Exception:
        try:
            d = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
        except Exception:
            return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def child(el, name):
    for c in el:
        if c.tag.split("}")[-1] == name:
            return c
    return None


def first(el, *names):
    for n in names:
        c = child(el, n)
        if c is not None:
            return c
    return None


def excerpt(text, title, n=180):
    if not text or text.lower().startswith(title.lower()[:40]):
        return ""
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0] + "…"


def parse_feed(data, cat, source, lang):
    root = ET.fromstring(data)
    items = []
    for el in root.iter():
        if el.tag.split("}")[-1] not in ("item", "entry"):
            continue
        t = child(el, "title")
        title = clean(t.text if t is not None else "")
        link_el = child(el, "link")
        link = ((link_el.get("href") or link_el.text or "") if link_el is not None else "").strip()
        d = first(el, "description", "summary")
        desc = clean(d.text if d is not None else "")
        p = first(el, "pubDate", "published", "updated")
        ts = parse_date(p.text if p is not None else None)
        if not title or not link.startswith("http") or ts is None:
            continue
        words = {w for w in re.findall(r"\w+", title.lower()) if len(w) > 2}
        items.append({"c": cat, "t": title, "s": excerpt(desc, title), "n": source,
                      "u": link, "ts": ts, "w": words, "lang": lang})
    return items


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def pick(items, limit, now):
    clusters = []
    for it in items:
        for c in clusters:
            if jaccard(it["w"], c[0]["w"]) >= 0.5:
                c.append(it)
                break
        else:
            clusters.append([it])

    def score(c):
        sources = len({i["n"] for i in c})
        age = (now - max(i["ts"] for i in c)).total_seconds() / 3600
        return sources * 10 - age * 0.5

    chosen = []
    for c in sorted(clusters, key=score, reverse=True)[:limit]:
        chosen.append(max(c, key=lambda i: len(i["s"])))
    return chosen


def ai_vietnamese(items):
    """Tùy chọn: dịch tiêu đề sang tiếng Việt và viết lại tóm tắt bằng lời mới."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key or not items:
        return
    payload = [{"id": i, "title": it["t"], "summary": it["s"]} for i, it in enumerate(items)]
    prompt = (
        "Với mỗi bài tin dưới đây, viết tiêu đề tiếng Việt ngắn gọn (dịch nếu bài tiếng Anh) và một "
        "tóm tắt tiếng Việt tối đa 25 từ bằng lời của bạn, không chép nguyên văn. Chỉ trả về JSON "
        'dạng [{"id":0,"title":"...","summary":"..."}].\n\n' + json.dumps(payload, ensure_ascii=False)
    )
    body = json.dumps({"model": "claude-haiku-5-5", "max_tokens": 6000,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages", data=body,
        headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            text = json.loads(r.read())["content"][0]["text"]
        text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
        for row in json.loads(text):
            it = items[row["id"]]
            it["t"], it["s"] = row["title"], row["summary"]
    except Exception as e:
        print("Bỏ qua bước AI:", e)


def notify(message):
    app_id, key, site = (os.environ.get(k) for k in ("ONESIGNAL_APP_ID", "ONESIGNAL_REST_KEY", "SITE_URL"))
    if not (app_id and key):
        print("Chưa cấu hình OneSignal, bỏ qua thông báo.")
        return
    body = json.dumps({
        "app_id": app_id, "target_channel": "push", "included_segments": ["Subscribed Users"],
        "headings": {"en": "Bản tin sáng"}, "contents": {"en": message}, "url": site or None,
    }).encode()
    req = urllib.request.Request(
        "https://api.onesignal.com/notifications?c=push", data=body,
        headers={"Content-Type": "application/json", "Authorization": "Key " + key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print("Đã gửi thông báo:", r.status)
    except Exception as e:
        print("Gửi thông báo lỗi:", e)


def build():
    now = datetime.now(timezone.utc)
    by_cat = {c: [] for c in CATEGORIES}
    for cat, source, url, lang in FEEDS:
        try:
            got = parse_feed(fetch(url), cat, source, lang)
            fresh = [i for i in got if now - i["ts"] <= timedelta(hours=MAX_AGE_HOURS)]
            by_cat[cat] += fresh
            print(f"OK   {source} / {cat}: {len(fresh)} tin")
        except Exception as e:
            print(f"LỖI  {source} / {cat}: {e}")
    chosen = []
    for cat in CATEGORIES:
        chosen += pick(by_cat[cat], LIMITS[cat], now)
    ai_vietnamese(chosen)
    items = [{"c": i["c"], "t": i["t"], "s": i["s"], "n": i["n"], "u": i["u"]} for i in chosen]
    local = datetime.now(VN)
    data = {"date": local.strftime("%Y-%m-%d"), "updated": local.isoformat(timespec="minutes"),
            "categories": [c for c in CATEGORIES if any(i["c"] == c for i in items)], "items": items}
    if len(items) < 5:
        print("Quá ít tin, giữ nguyên digest.json cũ.")
        return None
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    return items


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "morning"
    if mode == "evening":
        notify("Hôm nay bạn đã đọc bản tin chưa? Mở app và đọc nhanh vài phút trước khi ngủ.")
    else:
        got = build()
        if got:
            top = got[0]["t"]
            notify(f"{len(got)} tin nóng hôm nay. Nổi bật: {top}")
