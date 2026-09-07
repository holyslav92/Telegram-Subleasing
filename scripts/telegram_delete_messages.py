#!/usr/bin/env python3
"""Удаление сообщений из Telegram-канала через Bot API."""

import argparse
import json
import sys
import urllib.request
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_credentials import load_telegram_credentials


def delete_message(bot_token: str, chat_id: str, message_id: int) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/deleteMessage"
    payload = json.dumps({"chat_id": chat_id, "message_id": message_id}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description="Удалить сообщения из Telegram")
    parser.add_argument("message_ids", nargs="+", type=int, help="ID сообщений для удаления")
    args = parser.parse_args()

    creds = load_telegram_credentials()
    if not creds["bot_token"] or not creds["chat_id"]:
        raise SystemExit("Нужны TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID")

    for mid in args.message_ids:
        res = delete_message(creds["bot_token"], creds["chat_id"], mid)
        print(json.dumps({"message_id": mid, **res}, ensure_ascii=False))
        if not res.get("ok"):
            raise SystemExit(f"Не удалось удалить message_id={mid}")


if __name__ == "__main__":
    main()
