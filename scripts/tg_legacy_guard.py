"""Блокирует старый пайплайн «банк тем → композитор»: он и давал одинаковые посты."""

import os
import sys

NEW_FLOW = """
╔══════════════════════════════════════════════════════════════════════╗
║  СТАРЫЙ ПАЙПЛАЙН TELEGRAM ОТКЛЮЧЁН (банк тем повторял одно и то же). ║
╚══════════════════════════════════════════════════════════════════════╝
Работай по новой редакционной системе (подробно: TELEGRAM-AGENTS.md):

  1. python3 scripts/tg_editorial.py plan
     → рубрика дня, форматы, темы на паузе, поисковые запросы, шаблон черновика
  2. Найди свежие факты в интернете по search_queries (WebSearch),
     проверь каждый источник: python3 scripts/tg_editorial.py fetch <url> --find "<фраза>"
  3. Запиши черновик JSON в memory/telegram_posts/drafts/<ГГГГ-ММ-ДД>.json по draft_template
  4. python3 scripts/tg_editorial.py validate memory/telegram_posts/drafts/<дата>.json
     → исправляй, пока не PASS (при тупике смени тему)
  5. python3 scripts/tg_editorial.py publish memory/telegram_posts/drafts/<дата>.json
     → картинка по реальному фото + публикация + память в main

Это не ошибка для Фиксика, а действующая инструкция. Не выставляй TG_ALLOW_LEGACY,
не чини и не запускай старый пайплайн, не публикуй в обход validate.
"""


def refuse_legacy() -> None:
    if os.environ.get("TG_ALLOW_LEGACY") == "1":
        return
    print(NEW_FLOW)
    sys.exit(3)
