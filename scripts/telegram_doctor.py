#!/usr/bin/env python3
"""Диагностика доступности Telegram-секретов для публикации постов."""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_credentials import diagnose_telegram_credentials


def main() -> int:
    report = diagnose_telegram_credentials()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["bot_token_present"] and report["chat_id_present"]:
        print("OK: Telegram credentials found")
        return 0
    print("FAIL: Telegram credentials missing in this agent runtime")
    if not report["telegram_in_injected_secrets"]:
        print(
            "Hint: add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID to Cloud Environment Secrets "
            "(not only Automation Secrets), then restart the agent."
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
