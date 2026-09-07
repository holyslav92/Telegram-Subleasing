#!/usr/bin/env python3
"""
Preflight-gate перед публикацией Telegram-поста.
PASS / FAIL: duplicate id, duplicate entity, прошедшая дата события.
"""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_content_bank import TOPIC_BANK, get_next_topic
from telegram_content_rules import check_forbidden_content
from telegram_post_history import (
    extract_entities_from_text,
    extract_event_dates_from_text,
    get_entities_in_cooldown,
    get_ids_in_cooldown,
    is_event_date_past,
    load_ledger,
    text_fingerprint,
)


def check_post(
    post: dict,
    ledger: list | None = None,
    evergreen: bool | None = None,
) -> tuple[str, list[str]]:
    """
    Проверяет пост. Возвращает ('PASS'|'FAIL', [причины]).
    """
    ledger = ledger or load_ledger()
    reasons: list[str] = []

    topic_id = post.get("id", "")
    category_id = post.get("category_id", "")
    text = post.get("text_html") or post.get("body") or ""
    title = post.get("title", "")

    entities = post.get("entities") or extract_entities_from_text(text)
    event_date = post.get("event_date") or ""
    if not event_date:
        ev_dates = extract_event_dates_from_text(text)
        if ev_dates:
            event_date = ev_dates[0]

    if evergreen is None:
        evergreen = post.get("evergreen", True)
        if topic_id:
            for cat_topics in TOPIC_BANK.values():
                for t in cat_topics:
                    if t.get("id") == topic_id:
                        evergreen = t.get("evergreen", True)
                        break

    blocked_ids = get_ids_in_cooldown(ledger, category_id=category_id or None)
    if topic_id and topic_id in blocked_ids:
        reasons.append(f"topic_id '{topic_id}' в cooldown {60} дней")

    blocked_entities = get_entities_in_cooldown(ledger)
    overlap = [e for e in entities if e.lower() in blocked_entities]
    if overlap:
        reasons.append(f"сущности в cooldown: {', '.join(overlap)}")

    if event_date and not evergreen and is_event_date_past(event_date):
        reasons.append(f"дата события в прошлом: {event_date}")

    reasons.extend(check_forbidden_content(text=text, topic_id=topic_id, title=title))

    # Проверка fingerprint против недавних постов
    fp = post.get("text_fingerprint") or text_fingerprint(text)
    for entry in ledger[-10:]:
        if entry.get("text_fingerprint") == fp:
            reasons.append("дубликат text_fingerprint среди последних публикаций")
            break

    status = "FAIL" if reasons else "PASS"
    return status, reasons


def gate_topic(category_id: str, topic_id: str | None = None) -> tuple[str, dict, list[str]]:
    """Проверяет следующую тему из банка для рубрики."""
    ledger = load_ledger()
    topic = None
    if topic_id:
        for t in TOPIC_BANK.get(category_id, []):
            if t.get("id") == topic_id:
                topic = t
                break
    if not topic:
        topic = get_next_topic(category_id, ledger)

    post = {
        "id": topic.get("id", ""),
        "category_id": category_id,
        "title": topic.get("title", ""),
        "text_html": topic.get("body", ""),
        "entities": topic.get("entities", []),
        "event_date": topic.get("event_date", ""),
        "evergreen": topic.get("evergreen", True),
    }
    status, reasons = check_post(post, ledger)
    return status, post, reasons


def main():
    parser = argparse.ArgumentParser(description="Gate Telegram-контента перед публикацией")
    parser.add_argument("--category", default="afisha", help="Рубрика для проверки")
    parser.add_argument("--post", default="", help="Путь к post_*.json")
    parser.add_argument("--topic-id", default="", help="Проверить конкретный topic id")
    parser.add_argument("--dry-run", action="store_true", help="Только проверка")
    args = parser.parse_args()

    if args.post:
        post_path = Path(args.post)
        if not post_path.exists():
            print(f"FAIL: файл не найден: {post_path}")
            sys.exit(1)
        with open(post_path, "r", encoding="utf-8") as f:
            post = json.load(f)
        status, reasons = check_post(post)
        print(json.dumps({"status": status, "reasons": reasons, "id": post.get("id")}, ensure_ascii=False, indent=2))
        sys.exit(0 if status == "PASS" else 1)

    status, post, reasons = gate_topic(args.category, args.topic_id or None)
    result = {
        "status": status,
        "topic_id": post.get("id"),
        "title": post.get("title"),
        "entities": post.get("entities"),
        "event_date": post.get("event_date"),
        "evergreen": post.get("evergreen"),
        "reasons": reasons,
        "dry_run": args.dry_run,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if status == "PASS" else 1)


if __name__ == "__main__":
    main()
