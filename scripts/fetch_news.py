#!/usr/bin/env python3
"""MONO STUDIO v0.5: public RSS headline discovery + original abstract covers.

This is NOT article/full-text ingestion or image-reuse permission.
Source links, headlines and publication times are discovery metadata only.
"""
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/latest_news.json"
ART = ROOT / "assets/editorial"
FEEDS = [
    ("shopping", "국내", "패션 브랜드 출시 OR 컬렉션 when:1d", "KR", "ko", "패션"),
    ("shopping", "국내", "뷰티 화장품 신제품 OR 트렌드 when:1d", "KR", "ko", "뷰티"),
    ("shopping", "국내", "무신사 OR SPA OR 아웃도어 when:1d", "KR", "ko", "쇼핑"),
    ("shopping", "글로벌", "fashion brand collaboration OR collection when:1d", "US", "en", "패션"),
    ("shopping", "글로벌", "beauty skincare launch OR trend when:1d", "US", "en", "뷰티"),
    ("shopping", "글로벌", "retail apparel shopping trends when:1d", "US", "en", "유통"),
    ("lifestyle", "국내", "생활용품 살림 신제품 OR 가성비 when:1d", "KR", "ko", "생활템"),
    ("lifestyle", "글로벌", "home organization affordable products when:1d", "US", "en", "생활템"),
    ("food", "국내", "레시피 식품 신제품 OR 간편식 when:1d", "KR", "ko", "음식"),
    ("food", "글로벌", "food trends home cooking when:1d", "US", "en", "음식"),
    ("entertainment", "국내", "연예 영화 드라마 공식 발표 when:1d", "KR", "ko", "컬처"),
    ("entertainment", "글로벌", "movie pop culture entertainment release when:1d", "US", "en", "컬처"),
]
LIMITS = {"shopping": (12, 8), "lifestyle": (5, 3), "food": (5, 3), "entertainment": (7, 5)}
PALETTES = {
    "shopping": ("#161c20", "#e4eea3"), "lifestyle": ("#1b3640", "#b3d9e0"),
    "food": ("#432d28", "#f0cb9a"), "entertainment": ("#32223e", "#dcb9e7")
}

def clean(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def rss_url(term):
    theme, region, query, country, language, category = term
    return "https://news.google.com/rss/search?" + urllib.parse.urlencode({
        "q": query, "hl": "ko" if language == "ko" else "en-US",
        "gl": country, "ceid": country + ":" + language
    })

def download(url):
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 MONOStudio/0.5"})
    with urllib.request.urlopen(request, timeout=20) as response:
        return response.read(2_000_000)

def parse(xml_bytes, term, now):
    theme, region, query, country, language, category = term
    window_start = now - timedelta(hours=24)
    result = []
    for node in ET.fromstring(xml_bytes).findall(".//channel/item"):
        title = clean(node.findtext("title", ""))
        source_node = node.find("source")
        source = clean(source_node.text if source_node is not None else "") or "원문 확인"
        link = (node.findtext("link", "") or "").strip()
        if source and title.endswith(" - " + source):
            title = title[:-(len(source) + 3)]
        if not title or not link.startswith("https://"):
            continue
        try:
            date = parsedate_to_datetime(node.findtext("pubDate", "")).astimezone(timezone.utc)
        except (ValueError, TypeError, OverflowError):
            continue
        if not (window_start <= date <= now + timedelta(minutes=10)):
            continue
        key = re.sub(r"[^a-z0-9가-힣]", "", title.lower())
        if len(key) < 8:
            continue
        item_id = "rss-" + hashlib.sha256((theme + key).encode()).hexdigest()[:16]
        result.append({
            "id": item_id, "theme": theme, "region": region, "category": category,
            "title": title[:180], "source": source[:90], "url": link[:1100],
            "published": date.isoformat(), "summary": "RSS 헤드라인 발견 항목입니다. 원문을 열어 핵심 사실을 확인한 뒤 카드 문구를 완성하세요.",
            "factcheck": "required", "license_status": "unknown",
            "image_usage_allowed": False, "image_origin": "no_article_image",
            "discovery_provider": "Google News RSS"
        })
    return result

def choose(items, theme):
    domestic, global_max = LIMITS[theme]
    selected = []
    seen = set()
    for region, cap in (("국내", domestic), ("글로벌", global_max)):
        subset = sorted((x for x in items if x["theme"] == theme and x["region"] == region),
                        key=lambda x: x["published"], reverse=True)
        for item in subset:
            if item["id"] in seen:
                continue
            selected.append(item)
            seen.add(item["id"])
            if sum(i["region"] == region for i in selected) >= cap:
                break
    return selected

def create_art(item):
    """Our own original SVG design, not a photo or factual depiction."""
    item_id = item["id"]
    if not re.fullmatch(r"rss-[0-9a-f]{16}", item_id):
        raise ValueError("Unsafe editorial ID")
    base, accent = PALETTES[item["theme"]]
    seed = int(item_id[-8:], 16)
    x = 170 + seed % 460
    y = 230 + seed % 240
    rot = seed % 70 - 35
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1350" viewBox="0 0 1080 1350">'
           f'<rect width="1080" height="1350" fill="{base}"/>'
           f'<circle cx="{x}" cy="{y}" r="410" fill="{accent}" opacity=".12"/>'
           f'<circle cx="{x+260}" cy="{y+200}" r="260" fill="{accent}" opacity=".17"/>'
           f'<g transform="rotate({rot} 540 550)" fill="none" stroke="{accent}" stroke-width="9" opacity=".65">'
           f'<rect x="205" y="188" rx="190" width="625" height="690"/>'
           f'<rect x="270" y="260" rx="150" width="495" height="540"/>'
           f'<circle cx="520" cy="535" r="190"/></g>'
           f'<path d="M0 850 Q450 710 1080 965 L1080 1350 H0Z" fill="#080b13" opacity=".45"/>'
           '</svg>')
    ART.mkdir(parents=True, exist_ok=True)
    (ART / (item_id + ".svg")).write_text(svg, encoding="utf-8")
    item["cover_image"] = "./assets/editorial/" + item_id + ".svg"
    item["cover_image_rights"] = "studio_original_abstract"
    item["cover_image_notice"] = "자체 생성 추상 그래픽 · 기사 사진이 아님"

def collect(fetcher=download, now=None):
    now = now or datetime.now(timezone.utc)
    candidates, errors = [], []
    for term in FEEDS:
        try:
            candidates.extend(parse(fetcher(rss_url(term)), term, now))
        except Exception as exc:
            errors.append(f"{term[0]}/{term[1]}/{term[5]}: {type(exc).__name__} {str(exc)[:90]}")
    items = [x for theme in LIMITS for x in choose(candidates, theme)]
    return {
        "schema_version": 5, "generated_at": now.isoformat(),
        "window_from": (now - timedelta(hours=24)).isoformat(),
        "window_to": now.isoformat(), "count": len(items),
        "counts": {t: sum(x["theme"] == t for x in items) for t in LIMITS},
        "rights_policy": "discovery_only_no_article_photo_reuse",
        "ai_enabled": False, "items": items, "errors": errors
    }

def main():
    result = collect()
    if not result["items"]:
        print("No articles found: preserving previous feed; not inventing news.")
        for error in result["errors"]:
            print("WARN", error)
        return
    ART.mkdir(parents=True, exist_ok=True)
    for old in ART.glob("rss-*.svg"):
        old.unlink()
    for item in result["items"]:
        create_art(item)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Collected", result["counts"], "at", result["generated_at"])
    for error in result["errors"]:
        print("WARN", error)

if __name__ == "__main__":
    main()
