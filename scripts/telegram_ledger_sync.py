#!/usr/bin/env python3
"""Синхронизация ledger со всеми известными публикациями + post_*.json + bundles."""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_content_bank import TOPIC_BANK
from telegram_post_history import (
    rebuild_ledger_from_posts,
    save_ledger,
    text_fingerprint,
)
from telegram_similarity import opening_hook

POSTS_DIR = Path(__file__).resolve().parent.parent / "memory" / "telegram_posts"

# Публикации из канала / ручных прогонов (message id в комментарии для справки)
KNOWN_CHANNEL_PUBLICATIONS = [
    {
        "id": "city_thermal_pools",
        "category_id": "weekend_thermal",
        "title": "Планы на выходные в термальной столице",
        "published_at": "2026-09-04 08:00:00",
    },
    {
        "id": "city_dzerzhinskogo_excursions",
        "category_id": "weekend_thermal",
        "title": "Пешеходная улица Дзержинского и партнерские экскурсии",
        "published_at": "2026-09-04 04:58:21",
    },
    {
        "id": "special_early_booking",
        "category_id": "special_offers",
        "title": "Скидка 10% на раннее бронирование",
        "published_at": "2026-09-06 08:00:00",
    },
    {
        "id": "afisha_philharmonic_concerts",
        "category_id": "afisha",
        "title": "Музыкальные сезоны Тюменской Филармонии",
        "published_at": "2026-09-07 05:00:08",
    },
    {
        "id": "afisha_comedy_club",
        "category_id": "afisha",
        "title": "Stand-up и юмор: лёгкий вечер в Тюмени",
        "published_at": "2026-09-07 04:57:23",
    },
    {
        "id": "special_referral_friend",
        "category_id": "special_offers",
        "title": "Программа «Добрые рекомендации»",
        "published_at": "2026-09-09 07:18:35",
    },
    {
        "id": "manual_host_story_b28a35d1",
        "category_id": "host_story",
        "title": "Уют в деталях: почему мы встречаем гостей как старых друзей",
        "published_at": "2026-09-02 20:26:37",
        "post_file": "post_host_story_20260902_202637.json",
    },
    {
        "id": "afisha_tikhoe_fireworks",
        "category_id": "afisha",
        "title": "Куда сходить в Тюмени: салют и фестиваль на озере Тихое",
        "published_at": "2026-09-14 08:00:00",
    },
    {
        "id": "district_novin",
        "category_id": "district_guide",
        "title": "ЖК «Новин»: эталон комфорта для деловых поездок и командировок",
        "published_at": "2026-09-15 08:00:00",
    },
    {
        "id": "care_blanket",
        "category_id": "host_story",
        "title": "Заметки радушного «хозяина»: почему мы так придирчивы к отельному сатину",
        "published_at": "2026-09-16 08:00:00",
        "entities": ["сатин", "отельный сатин", "постельное белье"],
    },
    {
        "id": "embankment_evening_walk",
        "category_id": "weekend_thermal",
        "title": "Вечерняя прогулка по четырёхуровневой набережной Туры",
        "published_at": "2026-09-18 08:00:00",
        "entities": ["набережная туры"],
    },
    {
        "id": "special_long_stay",
        "category_id": "special_offers",
        "title": "Тариф «Длительное проживание»: скидка 10% от 10 ночей со сменой белья",
        "published_at": "2026-09-19 08:00:00",
    },
    {
        "id": "siberian_herbal_tea",
        "category_id": "siberian_hospitality",
        "title": "Сибирское чаепитие: как травяной сбор помогает снять усталость с дороги",
        "published_at": "2026-09-20 08:00:00",
    },
    {
        "id": "afisha_street_festivals",
        "category_id": "afisha",
        "title": "Уличные фестивали и ярмарки: атмосфера центра Тюмени",
        "published_at": "2026-09-21 08:00:00",
    },
]


def body_for_topic(topic_id: str) -> str:
    for topics in TOPIC_BANK.values():
        for t in topics:
            if t.get("id") == topic_id:
                return t.get("body", "")
    return ""


def text_from_post_file(filename: str) -> str:
    path = POSTS_DIR / filename
    if not path.exists():
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("text_html") or data.get("body") or ""
    except Exception:
        return ""


def enrich_entry(entry: dict) -> dict:
    text = entry.get("text_html") or entry.get("body") or ""
    if not text and entry.get("post_file"):
        text = text_from_post_file(entry["post_file"])
    if not text:
        text = body_for_topic(entry.get("id", ""))
    if text:
        entry["text_html"] = text
        entry["text_fingerprint"] = text_fingerprint(text)
        entry["opening_hook"] = opening_hook(text)
    entry.pop("post_file", None)
    return entry


def sync_all() -> list[dict]:
    rebuilt = rebuild_ledger_from_posts()
    by_id = {e["id"]: e for e in rebuilt if e.get("id")}

    for known in KNOWN_CHANNEL_PUBLICATIONS:
        tid = known["id"]
        merged = {**known}
        if tid in by_id:
            existing = by_id[tid]
            merged["published_at"] = known.get("published_at") or existing.get("published_at", "")
            if not merged.get("text_html") and existing.get("text_html"):
                merged["text_html"] = existing["text_html"]
            if not merged.get("entities") and existing.get("entities"):
                merged["entities"] = existing["entities"]
        by_id[tid] = enrich_entry(merged)

    for path in POSTS_DIR.glob("post_bundle_*.json"):
        try:
            with open(path, "r", encoding="utf-8") as f:
                bundle = json.load(f)
        except Exception:
            continue
        tid = bundle.get("id", "")
        if not tid or tid in by_id:
            continue
        variants = bundle.get("variants") or []
        text = variants[0].get("text_html", "") if variants else ""
        pub_at = bundle.get("published_at") or bundle.get("created_at", "")
        by_id[tid] = enrich_entry({
            "id": tid,
            "category_id": bundle.get("category_id", ""),
            "title": bundle.get("title", ""),
            "published_at": pub_at,
            "entities": bundle.get("entities", []),
            "event_date": bundle.get("event_date", ""),
            "text_html": text,
        })

    merged = sorted(by_id.values(), key=lambda x: x.get("published_at", ""))
    save_ledger(merged)
    return merged


def main():
    ledger = sync_all()
    print(f"Ledger синхронизирован: {len(ledger)} записей")
    for e in ledger:
        hook = (e.get("opening_hook") or "")[:50]
        print(f"  [{e.get('published_at', '?')}] {e.get('id')} · hook: {hook}…")


if __name__ == "__main__":
    main()
