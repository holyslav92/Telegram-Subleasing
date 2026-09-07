#!/usr/bin/env python3
"""Публикация выбранного варианта из bundle (1 изображение + 3 текста)."""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_telegram_post import send_to_telegram, record_published_id
from telegram_credentials import load_telegram_credentials
from telegram_content_gate import check_post
from telegram_post_history import load_ledger


def main():
    parser = argparse.ArgumentParser(description="Опубликовать вариант из post_bundle_*.json")
    parser.add_argument("--bundle", required=True, help="Путь к post_bundle_*.json")
    parser.add_argument("--variant", type=int, choices=[1, 2, 3], required=True, help="Номер варианта текста")
    args = parser.parse_args()

    bundle_path = Path(args.bundle)
    if not bundle_path.exists():
        raise SystemExit(f"Bundle не найден: {bundle_path}")

    with open(bundle_path, "r", encoding="utf-8") as f:
        bundle = json.load(f)

    variants = bundle.get("variants") or []
    chosen = next((v for v in variants if v.get("number") == args.variant), None)
    if not chosen:
        raise SystemExit(f"Вариант {args.variant} не найден в bundle")

    photo_url = bundle.get("photo_url", "")
    if not photo_url:
        raise SystemExit("В bundle нет photo_url")

    post = {
        "id": bundle.get("id", ""),
        "category_id": bundle.get("category_id", ""),
        "title": bundle.get("title", ""),
        "text_html": chosen["text_html"],
        "entities": bundle.get("entities", []),
        "event_date": bundle.get("event_date", ""),
        "evergreen": bundle.get("evergreen", True),
    }

    status, reasons = check_post(post, load_ledger())
    if status != "PASS":
        raise SystemExit(f"Gate FAIL: {reasons}")

    creds = load_telegram_credentials()
    if not creds["bot_token"] or not creds["chat_id"]:
        raise SystemExit("Нужны TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID")

    res = send_to_telegram(
        bot_token=creds["bot_token"],
        chat_id=creds["chat_id"],
        text=chosen["text_html"],
        reply_markup=bundle.get("reply_markup"),
        photo_url=photo_url,
        silent=True,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res.get("ok"):
        raise SystemExit("Ошибка публикации")

    record_published_id(
        post.get("id", ""),
        category_id=post.get("category_id", ""),
        title=post.get("title", ""),
        text_html=chosen["text_html"],
        entities=post.get("entities"),
        event_date=post.get("event_date", ""),
    )
    print(f"Опубликован вариант {args.variant} ({chosen.get('label', '')})")


if __name__ == "__main__":
    main()
