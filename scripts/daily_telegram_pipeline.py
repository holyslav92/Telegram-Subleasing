#!/usr/bin/env python3
"""
Скрипт ежедневного пайплайна публикаций для сети апартаментов «Добрый дом Тюмень».
Gate + Afisha Scout (понедельник) + retry до 3 тем при FAIL.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_telegram_post import build_post, send_to_telegram, generate_image_grsai, save_post, record_published_id
from telegram_credentials import load_telegram_credentials
from telegram_content_gate import check_post
from telegram_content_bank import get_next_topic
from telegram_post_history import load_ledger

CATEGORIES_SCHEDULE = [
    "afisha",
    "district_guide",
    "host_story",
    "service_standards",
    "weekend_thermal",
    "special_offers",
    "siberian_hospitality",
]

MAX_GATE_RETRIES = 3


def get_today_category():
    weekday = datetime.now().weekday()
    return CATEGORIES_SCHEDULE[weekday]


def select_topic_with_gate(category: str, topic: str = ""):
    """Подбирает тему с прохождением gate; до MAX_GATE_RETRIES попыток."""
    ledger = load_ledger()
    exclude_ids: set[str] = set()

    if category == "afisha" and datetime.now().weekday() == 0 and not topic:
        try:
            from telegram_afisha_scout import scout_afisha_topic
            scout_topic = scout_afisha_topic(fallback_category=category)
            if scout_topic:
                post_probe = {
                    "id": scout_topic.get("id", ""),
                    "category_id": category,
                    "title": scout_topic.get("title", ""),
                    "text_html": scout_topic.get("body", ""),
                    "entities": scout_topic.get("entities", []),
                    "event_date": scout_topic.get("event_date", ""),
                    "evergreen": scout_topic.get("evergreen", True),
                }
                status, reasons = check_post(post_probe, ledger)
                if status == "PASS":
                    print(f"Scout: тема прошла gate — {scout_topic.get('id')}")
                    return scout_topic, None
                print(f"Scout FAIL: {reasons} — fallback на банк")
        except Exception as e:
            print(f"Scout недоступен: {e} — fallback на банк")

    for attempt in range(1, MAX_GATE_RETRIES + 1):
        if topic:
            from telegram_content_bank import TOPIC_BANK
            topic_data = None
            for t in TOPIC_BANK.get(category, []):
                if t.get("title") == topic or t.get("id") == topic:
                    topic_data = t
                    break
            if not topic_data:
                topic_data = get_next_topic(category, ledger, exclude_ids=exclude_ids)
        else:
            prefer_ev = category == "afisha"
            topic_data = get_next_topic(
                category, ledger, prefer_evergreen=prefer_ev, exclude_ids=exclude_ids
            )

        post_probe = {
            "id": topic_data.get("id", ""),
            "category_id": category,
            "title": topic_data.get("title", ""),
            "text_html": topic_data.get("body", ""),
            "entities": topic_data.get("entities", []),
            "event_date": topic_data.get("event_date", ""),
            "evergreen": topic_data.get("evergreen", True),
        }
        status, reasons = check_post(post_probe, ledger)
        print(f"Gate попытка {attempt}/{MAX_GATE_RETRIES}: {status} — {topic_data.get('id')}")
        if reasons:
            print(f"  Причины: {reasons}")

        if status == "PASS":
            return topic_data, None

        tid = topic_data.get("id")
        if tid:
            exclude_ids.add(tid)

    return None, f"Gate FAIL после {MAX_GATE_RETRIES} попыток"


def run_daily_pipeline(category: str = None, topic: str = "", send: bool = True):
    cat = category or get_today_category()
    print(f"=== Запуск ежедневного пайплайна [Категория: {cat}] ===")

    topic_data, gate_error = select_topic_with_gate(cat, topic=topic)
    if gate_error:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {gate_error}")
        sys.exit(1)

    post = build_post(category_id=cat, topic=topic, topic_data=topic_data)
    saved_path = save_post(post)
    print(f"Черновик поста сохранен в: {saved_path}")

    # Финальный gate перед генерацией изображения
    status, reasons = check_post(post, load_ledger())
    if status != "PASS":
        print(f"КРИТИЧЕСКАЯ ОШИБКА gate перед публикацией: {reasons}")
        sys.exit(1)

    photo_url = None
    prompt = post["image_prompt"]["prompt"]

    input_urls = []
    tenant_cfg = SCRIPT_DIR.parent / "shared" / "tenant-config.json"
    cfg_logo_url = ""
    if tenant_cfg.exists():
        try:
            with open(tenant_cfg, "r", encoding="utf-8") as f:
                cfg_logo_url = json.load(f).get("brand_logo_url", "")
        except Exception:
            pass

    cdn_logo_url = os.environ.get("BRAND_LOGO_URL", "") or cfg_logo_url
    if cdn_logo_url:
        input_urls.append(cdn_logo_url)
        print(f"Используем эталонный логотип (Image-to-Image URL): {cdn_logo_url}")
    else:
        logo_file = SCRIPT_DIR.parent / "memory" / "branding" / "logo_full.jpg"
        if not logo_file.exists():
            logo_file = SCRIPT_DIR.parent / "memory" / "branding" / "site_logo.png"
        if logo_file.exists():
            import base64
            with open(logo_file, "rb") as f:
                b64_logo = base64.b64encode(f.read()).decode("utf-8")
            input_urls.append(f"data:image/jpeg;base64,{b64_logo}")
            print(f"Используем локальный эталонный логотип (base64): {logo_file.name}")

    pexels_ref = post.get("image_prompt", {}).get("pexels_reference_url", "")
    if pexels_ref:
        input_urls.append(pexels_ref)
        print(f"Используем свежий стиль из Pexels (Image-to-Image reference): {pexels_ref}")

    print(f"Генерация изображения через GRSAI API (до 3 попыток, input_urls: {len(input_urls)})...")

    max_retries = 3
    retry_delay_seconds = 5
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Попытка генерации {attempt} из {max_retries}...")
            photo_url = generate_image_grsai(prompt, input_urls=input_urls if input_urls else None)
            if photo_url:
                print(f"Изображение успешно получено: {photo_url}")
                break
            print(f"Попытка {attempt}: API не вернул URL изображения.")
        except Exception as e:
            print(f"Попытка {attempt} завершилась с ошибкой: {e}")
        if attempt < max_retries:
            print(f"Ожидание {retry_delay_seconds} сек перед следующей попыткой...")
            time.sleep(retry_delay_seconds)

    if not photo_url:
        print("КРИТИЧЕСКАЯ ОШИБКА: Не удалось сгенерировать изображение после 3 попыток.")
        sys.exit(1)

    if send:
        creds = load_telegram_credentials()
        bot_token = creds["bot_token"]
        target_chat = creds["chat_id"]
        if not bot_token or not target_chat:
            print("Ошибка: TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID должны быть заданы!")
            sys.exit(1)
        print(f"Отправка единого поста в Telegram {target_chat}...")

        res = send_to_telegram(
            bot_token=bot_token,
            chat_id=target_chat,
            text=post["text_html"],
            reply_markup=post["reply_markup"],
            photo_url=photo_url,
            photo_path=None,
            silent=True,
        )
        if res.get("ok"):
            msg_id = res.get("result", {}).get("message_id")
            print(f"Пост успешно опубликован! Telegram Message ID: {msg_id}")
            record_published_id(
                post.get("id", ""),
                category_id=post.get("category_id", cat),
                title=post.get("title", ""),
                text_html=post.get("text_html", ""),
                entities=post.get("entities"),
                event_date=post.get("event_date", ""),
            )
        else:
            print(f"Ошибка публикации: {res}")
            sys.exit(1)

    print("=== Ежедневный пайплайн завершен успешно ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Запуск ежедневного поста Добрый дом Тюмень")
    parser.add_argument("--category", default=None, help="Принудительно выбрать рубрику")
    parser.add_argument("--topic", default="", help="Тема поста")
    parser.add_argument("--no-send", action="store_true", help="Не отправлять в Telegram, только сформировать")
    args = parser.parse_args()

    run_daily_pipeline(category=args.category, topic=args.topic, send=not args.no_send)
