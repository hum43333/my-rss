import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import email.utils
import ssl

SOURCE_URL = "https://news-ex.jtbc.co.kr/v1/get/rss/newsflesh"
OUTPUT_FILE = "jtbc_top20.xml"
MAX_ITEMS = 20

def fetch_and_trim_rss(url, max_items, output_path):
    print(f"📡 RSS 가져오는 중: {url}")

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
        raw = response.read()

    root = ET.fromstring(raw)
    channel = root.find("channel")

    if channel is None:
        print("❌ <channel> 태그를 찾을 수 없습니다.")
        return

    items = channel.findall("item")
    print(f"✅ 전체 아이템 수: {len(items)}")

    def parse_date(item):
        pd = item.find("pubDate")
        if pd is not None and pd.text:
            try:
                return email.utils.parsedate_to_datetime(pd.text.strip())
            except Exception:
                pass
        return datetime.min.replace(tzinfo=timezone.utc)

    items_sorted = sorted(items, key=parse_date, reverse=True)
    top_items = items_sorted[:max_items]

    for item in items:
        channel.remove(item)

    lbd = channel.find("lastBuildDate")
    now_str = email.utils.format_datetime(datetime.now(timezone.utc))
    if lbd is not None:
        lbd.text = now_str
    else:
        lbd_el = ET.SubElement(channel, "lastBuildDate")
        lbd_el.text = now_str

    for item in top_items:
        channel.append(item)

    ET.indent(root, space="  ")
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    print(f"💾 저장 완료: {output_path}  ({len(top_items)}개 아이템)")

    print("\n📋 포함된 뉴스 목록:")
    for i, item in enumerate(top_items, 1):
        title = item.find("title")
        pub   = item.find("pubDate")
        print(f"  {i:2}. {title.text if title is not None else '(제목없음)'}  [{pub.text.strip() if pub is not None else '날짜없음'}]")

if __name__ == "__main__":
    fetch_and_trim_rss(SOURCE_URL, MAX_ITEMS, OUTPUT_FILE)
