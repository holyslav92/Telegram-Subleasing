#!/usr/bin/env python3
"""Публикация сохранённого Telegram-поста с локальным изображением."""

import argparse
import json
import os
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_telegram_post import send_to_telegram, record_published_id

WORKSPACE_ROOT = SCRIPT_DIR.parent


def main():
    parser = argparse.ArgumentParser(description="Опубликовать сохранённый Telegram-пост")
    parser.add_argument("--post", required=True, help="Путь к post_*.json")
    parser.add_argument("--photo", required=True, help="Путь к PNG/JPG обложке")
    parser.add_argument("--token", default=os.environ.get("TELEGRAM_BOT_TOKEN", ""))
    parser.add_argument("--chat", default=os.environ.get("TELEGRAM_CHAT_ID", ""))
    args = parser.parse_args()

    post_path = Path(args.post)
    photo_path = Path(args.photo)
    if not post_path.exists():
        raise SystemExit(f"Файл поста не найден: {post_path}")
    if not photo_path.exists():
        raise SystemExit(f"Изображение не найдено: {photo_path}")
    if not args.token or not args.chat:
        raise SystemExit("Задайте TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID в Secrets или через --token / --chat")

    with open(post_path, "r", encoding="utf-8") as f:
        post = json.load(f)

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
    if topic_id:
        record_published_id(topic_id, category_id=post.get("category_id", ""))
        print(f"Тема {topic_id} записана в history.json")


if __name__ == "__main__":
    main()
