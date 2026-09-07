#!/usr/bin/env python3
"""Backfill ledger.json из всех post_*.json и существующего history.json."""

import argparse
import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_post_history import (
    LEDGER_FILE,
    HISTORY_FILE,
    load_ledger,
    rebuild_ledger_from_posts,
    save_ledger,
)


def main():
    parser = argparse.ArgumentParser(description="Восстановление ledger Telegram-постов")
    parser.add_argument("--dry-run", action="store_true", help="Только показать, не сохранять")
    args = parser.parse_args()

    rebuilt = rebuild_ledger_from_posts()
    print(f"Найдено записей для ledger: {len(rebuilt)}")
    for entry in rebuilt:
        ents = ", ".join(entry.get("entities") or []) or "—"
        ev = entry.get("event_date") or "—"
        print(
            f"  [{entry.get('published_at', '?')}] "
            f"{entry.get('id', '?')} | entities: {ents} | event: {ev}"
        )

    if args.dry_run:
        print("\n(dry-run: ledger не сохранён)")
        return

    save_ledger(rebuilt)
    print(f"\nLedger сохранён: {LEDGER_FILE}")
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            hist = json.load(f)
        print(f"history.json синхронизирован: {len(hist)} записей")


if __name__ == "__main__":
    main()
