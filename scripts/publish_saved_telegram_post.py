#!/usr/bin/env python3
"""Публикация сохранённого Telegram-поста с локальным изображением и gate."""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_telegram_post import send_to_telegram, record_published_id
from telegram_credentials import load_telegram_credentials
from telegram_content_gate import check_post
from telegram_post_history import load_ledger, extract_entities_from_text, extract_event_dates_from_text

WORKSPACE_ROOT = SCRIPT_DIR.parent


def main():
    parser = argparse.ArgumentParser(description="Опубликовать сохранённый Telegram-пост")
    parser.add_argument("--post", required=True, help="Путь к post_*.json")
    parser.add_argument("--photo", required=True, help="Путь к PNG/JPG обложке")
    parser.add_argument("--skip-gate", action="store_true", help="Обойти gate (не рекомендуется)")
    creds = load_telegram_credentials()
    parser.add_argument("--token", default=creds["bot_token"])
    parser.add_argument("--chat", default=creds["chat_id"])
    args = parser.parse_args()

    post_path = Path(args.post)
    photo_path = Path(args.photo)
    if not post_path.exists():
        raise SystemExit(f"Файл поста не найден: {post_path}")
    if not photo_path.exists():
        raise SystemExit(f"Изображение не найдено: {photo_path}")
    if not args.token or not args.chat:
        raise SystemExit(
            "Задайте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в Secrets окружения, "
            "memory/site.env.local или через --token / --chat"
        )

    with open(post_path, "r", encoding="utf-8") as f:
        post = json.load(f)

    text = post.get("text_html") or post.get("body") or ""
    if not post.get("entities"):
        post["entities"] = extract_entities_from_text(text)
    if not post.get("event_date"):
        evs = extract_event_dates_from_text(text)
        post["event_date"] = evs[0] if evs else ""

    if not args.skip_gate:
        status, reasons = check_post(post, load_ledger())
        print(json.dumps({"gate": status, "reasons": reasons}, ensure_ascii=False, indent=2))
        if status != "PASS":
            raise SystemExit(f"Gate FAIL: {reasons}. Используйте другую тему или --skip-gate (не для automation).")

    res = send_to_telegram(
        bot_token=args.token,
        chat_id=args.chat,
        text=post["text_html"],
        reply_markup=post.get("reply_markup"),
        photo_path=str(photo_path),
        silent=True,
    )
    print(json.dumps(res, ensure_ascii=False, indent=2))
    if not res.get("ok"):
        raise SystemExit("Ошибка отправки в Telegram")

    topic_id = post.get("id", "")
    record_published_id(
        topic_id or f"manual_{post_path.stem}",
        category_id=post.get("category_id", ""),
        title=post.get("title", ""),
        text_html=text,
        entities=post.get("entities"),
        event_date=post.get("event_date", ""),
    )
    print(f"Запись добавлена в ledger.json (id={topic_id or post_path.stem})")


if __name__ == "__main__":
    main()
