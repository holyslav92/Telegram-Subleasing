#!/usr/bin/env python3
"""
Afisha Scout для понедельника: живые события Тюмени на ближайшие 7–14 дней.
Источники: visittyumen.ru, afisha.72.ru (из tenant-config scout_signal_urls).
"""

import json
import re
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta
from html import unescape
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_post_history import (
    extract_entities_from_text,
    extract_event_dates_from_text,
    get_entities_in_cooldown,
    load_ledger,
)
from telegram_content_bank import get_next_topic, TOPIC_BANK

WORKSPACE_ROOT = SCRIPT_DIR.parent
TENANT_CONFIG = WORKSPACE_ROOT / "shared" / "tenant-config.json"

CTA_BLOCK = """
Бронируйте по <b>прямым ценам</b> на <b><a href="https://добрыйдом-72.рф/">нашем сайте</a></b>. <b><a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">Отзывы гостей</a></b> читайте на <b><a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">Авито</a></b>, новости — в <b><a href="https://max.ru/id660300569233_biz">Макс</a></b>."""


def load_scout_urls() -> list[str]:
    urls = ["https://visittyumen.ru", "https://afisha.72.ru"]
    if TENANT_CONFIG.exists():
        try:
            with open(TENANT_CONFIG, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            extra = cfg.get("scout_signal_urls") or []
            for u in extra:
                if u and u not in urls:
                    urls.append(u.rstrip("/"))
        except Exception:
            pass
    return urls


def fetch_page(url: str, timeout: int = 15) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; DobryDomTelegramScout/1.0)",
            "Accept-Language": "ru-RU,ru;q=0.9",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def strip_tags(html: str) -> str:
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return unescape(re.sub(r"\s+", " ", text)).strip()


def parse_events_from_html(html: str, source: str) -> list[dict]:
    """Извлекает кандидатов событий из HTML (эвристика)."""
    text = strip_tags(html)
    today = datetime.now().date()
    horizon = today + timedelta(days=14)
    events: list[dict] = []

    # Блоки с датой + заголовком рядом
    patterns = [
        r"(\d{1,2}\s+(?:январ\w+|феврал\w+|март\w+|апрел\w+|ма\w+|июн\w+|"
        r"июл\w+|август\w+|сентябр\w+|октябр\w+|ноябр\w+|декабр\w+)\w*)"
        r"[^.]{0,120}?([А-ЯЁA-Z][^.]{10,80})",
        r"(\d{1,2}\.\d{1,2}(?:\.\d{4})?)[^.]{0,80}?([А-ЯЁA-Z][^.]{10,80})",
    ]
    for pat in patterns:
        for m in re.finditer(pat, text, flags=re.I):
            date_str = m.group(1).strip()
            title = m.group(2).strip()
            if len(title) < 12:
                continue
            snippet = f"{date_str} {title}"
            ev_dates = extract_event_dates_from_text(snippet)
            if not ev_dates:
                continue
            ev_dt = datetime.strptime(ev_dates[0], "%Y-%m-%d").date()
            if ev_dt < today or ev_dt > horizon:
                continue
            entities = extract_entities_from_text(snippet + " " + title)
            events.append({
                "title": title[:120],
                "event_date": ev_dates[0],
                "entities": entities,
                "source": source,
                "snippet": snippet[:200],
            })
    return events


WEEKDAY_ABBR = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")


def is_valid_event_title(title: str) -> bool:
    if len(title) < 12 or len(title) > 100:
        return False
    junk = (
        "удалить", "избранн", "cookie", "войти", "регистрац",
        "javascript", "click", "banner", "modal", "уверен",
        "все события", "место из", "купить", "18+", "16+", "билет",
    )
    lower = title.lower()
    if any(j in lower for j in junk):
        return False
    if title.count("•") >= 2:
        return False
    # Календарная сетка: «пн 8 вт 9 ср 10…»
    weekday_hits = sum(1 for w in WEEKDAY_ABBR if re.search(rf"\b{w}\b", lower))
    if weekday_hits >= 2:
        return False
    digit_count = sum(c.isdigit() for c in title)
    if digit_count > len(title) * 0.25:
        return False
    # Должно быть хотя бы одно осмысленное слово (5+ букв, не день недели)
    words = re.findall(r"[а-яёa-z]{5,}", lower)
    meaningful = [w for w in words if w not in WEEKDAY_ABBR]
    return len(meaningful) >= 1


def filter_fresh_events(events: list[dict]) -> list[dict]:
    blocked = get_entities_in_cooldown(load_ledger())
    fresh = []
    seen_titles: set[str] = set()
    for ev in events:
        if not is_valid_event_title(ev.get("title", "")):
            continue
        title_key = ev["title"].lower()[:40]
        if title_key in seen_titles:
            continue
        overlap = [e for e in ev.get("entities") or [] if e in blocked]
        if overlap:
            continue
        seen_titles.add(title_key)
        fresh.append(ev)
    return fresh


def build_dynamic_post(event: dict) -> dict:
    date_human = event["event_date"]
    title = event["title"]
    body = f"""<b>{title}</b>

<b>Афиша Тюмени:</b> {date_human} — повод спланировать визит в город. {event.get('snippet', '')}

Остановиться удобнее всего в апартаментах «Добрый дом»: отельный сатин, чистота и <b>бесконтактный заезд 24/7</b> в шаговой доступности от центра и набережной.{CTA_BLOCK}"""
    return {
        "id": f"scout_{event['event_date'].replace('-', '')}_{hash(title) % 100000:05d}",
        "title": title,
        "body": body,
        "image_title": "Афиша Тюмени",
        "search_query": "tyumen city cultural event evening lights cozy atmosphere",
        "entities": event.get("entities") or extract_entities_from_text(body),
        "event_date": event["event_date"],
        "evergreen": False,
        "scout_source": event.get("source", ""),
    }


def scout_afisha_topic(fallback_category: str = "afisha") -> dict | None:
    """
    Ищет свежее событие на 7–14 дней вперёд.
    Возвращает topic dict или None (тогда caller использует банк).
    """
    all_events: list[dict] = []
    for url in load_scout_urls():
        try:
            html = fetch_page(url)
            all_events.extend(parse_events_from_html(html, url))
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            print(f"Scout: не удалось загрузить {url}: {e}")

    fresh = filter_fresh_events(all_events)
    if fresh:
        fresh.sort(key=lambda x: x["event_date"])
        chosen = fresh[0]
        print(f"Scout: найдено событие «{chosen['title']}» на {chosen['event_date']}")
        return build_dynamic_post(chosen)

    print("Scout: свежих событий не найдено — fallback на evergreen из банка")
    ledger = load_ledger()
    topic = get_next_topic(fallback_category, ledger, prefer_evergreen=True)
    return topic


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Afisha Scout — живые события Тюмени")
    parser.add_argument("--json", action="store_true", help="Вывести topic как JSON")
    args = parser.parse_args()

    topic = scout_afisha_topic()
    if args.json:
        print(json.dumps(topic, ensure_ascii=False, indent=2))
    else:
        print(f"Topic: {topic.get('id')} — {topic.get('title')}")
        print(f"evergreen={topic.get('evergreen')} event_date={topic.get('event_date', '—')}")


if __name__ == "__main__":
    main()
