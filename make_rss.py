import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import email.utils

SOURCE_URL = "https://www.yna.co.kr/rss/news.xml"
OUTPUT_FILE = "yonhap_top20.xml"
MAX_ITEMS = 20

def fetch_and_trim_rss(url, max_items, output_path):
    print(f"📡 RSS 가져오는 중: {url}")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        raw = response.read()

    # 파싱
    root = ET.fromstring(raw)
    channel = root.find("channel")

    if channel is None:
        print("❌ <channel> 태그를 찾을 수 없습니다.")
        return

    # item 목록 수집
    items = channel.findall("item")
    print(f"✅ 전체 아이템 수: {len(items)}")

    # pubDate 기준 정렬 (최신순)
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

    # channel에서 item 모두 제거 후 상위 20개만 다시 추가
    for item in items:
        channel.remove(item)

    # lastBuildDate 갱신
    lbd = channel.find("lastBuildDate")
    now_str = email.utils.format_datetime(datetime.now(timezone.utc))
    if lbd is not None:
        lbd.text = now_str
    else:
        lbd_el = ET.SubElement(channel, "lastBuildDate")
        lbd_el.text = now_str

    for item in top_items:
        channel.append(item)

    # XML 직렬화
    ET.indent(root, space="  ")  # Python 3.9+
    tree = ET.ElementTree(root)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)

    print(f"💾 저장 완료: {output_path}  ({len(top_items)}개 아이템)")

    # 미리보기
    print("\n📋 포함된 뉴스 목록:")
    for i, item in enumerate(top_items, 1):
        title = item.find("title")
        pub   = item.find("pubDate")
        print(f"  {i:2}. {title.text if title is not None else '(제목없음)'}  [{pub.text.strip() if pub is not None else '날짜없음'}]")

if __name__ == "__main__":
    fetch_and_trim_rss(SOURCE_URL, MAX_ITEMS, OUTPUT_FILE)
