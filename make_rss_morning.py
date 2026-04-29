import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import email.utils
import ssl
import json

# =====================
# 설정
# =====================
JTBC_RSS_URL  = "https://news-ex.jtbc.co.kr/v1/get/rss/newsflesh"
NEWS_MAX      = 10
OUTPUT_FILE   = "morning_briefing.xml"

# 고텐바시 위도/경도
LATITUDE  = 35.3081
LONGITUDE = 138.9328
CITY_NAME = "고텐바시 (御殿場市)"

# JST = UTC+9
JST = timezone(timedelta(hours=9))

def ssl_ctx():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx

# =====================
# 날씨 가져오기 (Open-Meteo, 무료·가입불필요)
# =====================
def fetch_weather():
    print("🌤  날씨 가져오는 중...")
    params = urllib.parse.urlencode({
        "latitude":       LATITUDE,
        "longitude":      LONGITUDE,
        "current":        "temperature_2m,apparent_temperature,weathercode,windspeed_10m,precipitation",
        "daily":          "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
        "timezone":       "Asia/Tokyo",
        "forecast_days":  1,
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    with urllib.request.urlopen(url, timeout=10) as r:
        data = json.loads(r.read())

    cur   = data["current"]
    daily = data["daily"]

    # 날씨 코드 → 한국어 설명
    def wcode(code):
        table = {
            0:"맑음☀️", 1:"대체로 맑음🌤", 2:"부분 흐림⛅", 3:"흐림☁️",
            45:"안개🌫", 48:"안개🌫",
            51:"이슬비🌦", 53:"이슬비🌦", 55:"이슬비🌦",
            61:"비🌧", 63:"비🌧", 65:"강한 비🌧",
            71:"눈🌨", 73:"눈🌨", 75:"강한 눈❄️",
            80:"소나기🌦", 81:"소나기🌦", 82:"강한 소나기⛈",
            95:"뇌우⛈", 96:"뇌우⛈", 99:"뇌우⛈",
        }
        return table.get(int(code), f"코드{code}")

    summary = (
        f"【현재】{wcode(cur['weathercode'])}  "
        f"기온 {cur['temperature_2m']}°C (체감 {cur['apparent_temperature']}°C)  "
        f"풍속 {cur['windspeed_10m']}km/h  강수 {cur['precipitation']}mm\n"
        f"【오늘 예보】최고 {daily['temperature_2m_max'][0]}°C / 최저 {daily['temperature_2m_min'][0]}°C  "
        f"강수량 {daily['precipitation_sum'][0]}mm  {wcode(daily['weathercode'][0])}"
    )
    print(f"  → {summary}")
    return summary

# =====================
# 뉴스 가져오기
# =====================
def fetch_news(url, max_items):
    print(f"📰 뉴스 가져오는 중: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10, context=ssl_ctx()) as r:
        raw = r.read()

    root    = ET.fromstring(raw)
    channel = root.find("channel")
    items   = channel.findall("item") if channel is not None else []

    def parse_date(item):
        pd = item.find("pubDate")
        if pd is not None and pd.text:
            try:
                return email.utils.parsedate_to_datetime(pd.text.strip())
            except Exception:
                pass
        return datetime.min.replace(tzinfo=timezone.utc)

    items = sorted(items, key=parse_date, reverse=True)[:max_items]
    print(f"  → {len(items)}개 뉴스 수집 완료")
    return items

# =====================
# RSS XML 생성
# =====================
def build_rss(weather_text, news_items, output_path):
    now_jst  = datetime.now(JST)
    now_str  = email.utils.format_datetime(now_jst)
    date_str = now_jst.strftime("%Y년 %m월 %d일")

    rss     = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text         = f"🌅 모닝 브리핑 — {date_str}"
    ET.SubElement(channel, "link").text          = "https://github.com"
    ET.SubElement(channel, "description").text   = f"{CITY_NAME} 날씨 + 오늘의 뉴스 10선"
    ET.SubElement(channel, "language").text      = "ko"
    ET.SubElement(channel, "lastBuildDate").text = now_str

    # ── 날씨 아이템 ──
    w_item = ET.SubElement(channel, "item")
    ET.SubElement(w_item, "title").text       = f"🌤 {CITY_NAME} 오늘의 날씨 ({date_str})"
    ET.SubElement(w_item, "link").text        = "https://open-meteo.com"
    ET.SubElement(w_item, "description").text = weather_text
    ET.SubElement(w_item, "pubDate").text     = now_str
    ET.SubElement(w_item, "guid").text        = f"weather-{now_jst.strftime('%Y%m%d')}"

    # ── 뉴스 아이템 ──
    for item in news_items:
        channel.append(item)

    ET.indent(rss, space="  ")
    ET.ElementTree(rss).write(output_path, encoding="utf-8", xml_declaration=True)
    print(f"\n💾 저장 완료: {output_path}")

# =====================
# 실행
# =====================
if __name__ == "__main__":
    weather = fetch_weather()
    news    = fetch_news(JTBC_RSS_URL, NEWS_MAX)
    build_rss(weather, news, OUTPUT_FILE)

    print("\n📋 최종 구성:")
    print(f"  날씨 : {weather[:60]}...")
    print(f"  뉴스 : {len(news)}개")
