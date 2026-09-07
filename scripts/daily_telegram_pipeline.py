#!/usr/bin/env python3
"""
Ежедневный пайплайн Telegram «Добрый дом Тюмень».
По умолчанию: 1 изображение + 3 текста → менеджер выбирает вариант.
Публикация в канал: --publish --variant 1|2|3
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent
OUTPUT_DIR = WORKSPACE_ROOT / "memory" / "telegram_posts"
sys.path.insert(0, str(SCRIPT_DIR))

from generate_telegram_post import (
    build_post,
    send_to_telegram,
    generate_image_grsai,
    record_published_id,
)
from telegram_credentials import load_telegram_credentials
from telegram_content_gate import check_post
from telegram_content_bank import get_next_topic
from telegram_post_history import load_ledger, strip_html
from telegram_text_variants import build_text_variants

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
    return CATEGORIES_SCHEDULE[datetime.now().weekday()]


def select_topic_with_gate(category: str, topic: str = "", use_scout: bool = False):
    ledger = load_ledger()
    exclude_ids: set[str] = set()

    if category == "afisha" and datetime.now().weekday() == 0 and not topic and use_scout:
        try:
            from telegram_afisha_scout import scout_afisha_topic, is_valid_event_title
            scout_topic = scout_afisha_topic()
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
                if status == "PASS" and is_valid_event_title(scout_topic.get("title", "")):
                    print(f"Scout: тема прошла gate — {scout_topic.get('id')}")
                    return scout_topic, None
                print(f"Scout FAIL — fallback на банк: {reasons}")
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


def save_bundle(bundle: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = OUTPUT_DIR / f"post_bundle_{bundle['category_id']}_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, ensure_ascii=False, indent=2)
    return path


def send_manager_preview(bundle: dict, bot_token: str, manager_chat_id: str) -> None:
    """Отправляет менеджеру фото + 3 текста для выбора."""
    header = (
        f"📋 <b>Черновик поста · {bundle.get('category_name', bundle.get('category_id'))}</b>\n"
        f"Тема: {bundle.get('title')}\n"
        f"id: <code>{bundle.get('id')}</code>\n\n"
        f"Выберите вариант текста (1–3). Публикация в канал:\n"
        f"<code>python3 scripts/publish_telegram_bundle.py --bundle {bundle.get('_bundle_path')} --variant N</code>"
    )
    send_to_telegram(
        bot_token=bot_token,
        chat_id=manager_chat_id,
        text=header,
        photo_url=bundle.get("photo_url"),
        reply_markup=None,
        silent=True,
    )
    for v in bundle.get("variants", []):
        plain = strip_html(v["text_html"])
        msg = f"<b>Вариант {v['number']} · {v.get('label', '')}</b>\n\n{plain[:3500]}"
        send_to_telegram(
            bot_token=bot_token,
            chat_id=manager_chat_id,
            text=msg,
            silent=True,
        )


def run_daily_pipeline(
    category: str = None,
    topic: str = "",
    use_scout: bool = False,
    publish: bool = False,
    variant: int = 0,
    bundle_path: str = "",
):
    cat = category or get_today_category()
    print(f"=== Пайплайн Telegram [Категория: {cat}] ===")

    if publish:
        if not bundle_path or variant not in (1, 2, 3):
            print("Для --publish укажите --bundle и --variant 1|2|3")
            sys.exit(1)
        import subprocess
        cmd = [
            sys.executable,
            str(SCRIPT_DIR / "publish_telegram_bundle.py"),
            "--bundle",
            bundle_path,
            "--variant",
            str(variant),
        ]
        subprocess.run(cmd, check=True)
        return

    topic_data, gate_error = select_topic_with_gate(cat, topic=topic, use_scout=use_scout)
    if gate_error:
        print(f"КРИТИЧЕСКАЯ ОШИБКА: {gate_error}")
        sys.exit(1)

    variants = build_text_variants(topic_data)
    for v in variants:
        probe = {
            "id": topic_data.get("id", ""),
            "category_id": cat,
            "title": topic_data.get("title", ""),
            "text_html": v["text_html"],
            "entities": topic_data.get("entities", []),
            "event_date": topic_data.get("event_date", ""),
            "evergreen": topic_data.get("evergreen", True),
        }
        status, reasons = check_post(probe, load_ledger())
        if status != "PASS":
            print(f"Gate FAIL для варианта {v['number']}: {reasons}")
            sys.exit(1)

    post = build_post(category_id=cat, topic=topic, topic_data=topic_data)
    prompt = post["image_prompt"]["prompt"]

    input_urls = []
    tenant_cfg = WORKSPACE_ROOT / "shared" / "tenant-config.json"
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
    else:
        logo_file = WORKSPACE_ROOT / "memory" / "branding" / "logo_full.jpg"
        if not logo_file.exists():
            logo_file = WORKSPACE_ROOT / "memory" / "branding" / "site_logo.png"
        if logo_file.exists():
            import base64
            with open(logo_file, "rb") as f:
                b64_logo = base64.b64encode(f.read()).decode("utf-8")
            input_urls.append(f"data:image/jpeg;base64,{b64_logo}")

    pexels_ref = post.get("image_prompt", {}).get("pexels_reference_url", "")
    if pexels_ref:
        input_urls.append(pexels_ref)

    print(f"Генерация одного изображения (GRSAI, до 3 попыток)...")
    photo_url = None
    for attempt in range(1, 4):
        try:
            photo_url = generate_image_grsai(prompt, input_urls=input_urls or None)
            if photo_url:
                print(f"Изображение: {photo_url}")
                break
        except Exception as e:
            print(f"Попытка {attempt}: {e}")
        if attempt < 3:
            time.sleep(5)

    if not photo_url:
        print("КРИТИЧЕСКАЯ ОШИБКА: не удалось сгенерировать изображение")
        sys.exit(1)

    bundle = {
        "id": post.get("id", ""),
        "title": post.get("title", ""),
        "category_id": cat,
        "category_name": post.get("category_name", ""),
        "entities": post.get("entities", []),
        "event_date": post.get("event_date", ""),
        "evergreen": post.get("evergreen", True),
        "photo_url": photo_url,
        "image_prompt": post.get("image_prompt"),
        "reply_markup": post.get("reply_markup"),
        "variants": variants,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "awaiting_manager_choice",
    }
    saved = save_bundle(bundle)
    bundle["_bundle_path"] = str(saved)
    with open(saved, "w", encoding="utf-8") as f:
        json.dump({k: v for k, v in bundle.items() if not k.startswith("_")}, f, ensure_ascii=False, indent=2)

    print(f"Bundle сохранён: {saved}")
    print("\n--- 3 варианта текста (одно изображение) ---")
    for v in variants:
        print(f"\n### Вариант {v['number']} · {v['label']}")
        print(strip_html(v["text_html"]))

    creds = load_telegram_credentials()
    manager_chat = creds.get("manager_chat_id") or os.environ.get("TELEGRAM_MANAGER_CHAT_ID", "")
    if manager_chat and creds.get("bot_token"):
        print(f"\nОтправка превью менеджеру {manager_chat}...")
        try:
            send_manager_preview(bundle, creds["bot_token"], manager_chat)
            print("Превью отправлено менеджеру.")
        except Exception as e:
            print(f"Не удалось отправить менеджеру: {e}")
    else:
        print("\nTELEGRAM_MANAGER_CHAT_ID не задан — превью только в bundle и в логе выше.")
        print(f"Публикация в канал: python3 scripts/publish_telegram_bundle.py --bundle {saved} --variant 1|2|3")

    print("\n=== Готово: менеджер выбирает вариант, в канал не публиковали ===")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Telegram-пайплайн Добрый дом")
    parser.add_argument("--category", default=None)
    parser.add_argument("--topic", default="")
    parser.add_argument("--use-scout", action="store_true")
    parser.add_argument("--publish", action="store_true", help="Опубликовать выбранный вариант в канал")
    parser.add_argument("--bundle", default="", help="Путь к post_bundle_*.json для --publish")
    parser.add_argument("--variant", type=int, default=0, choices=[0, 1, 2, 3])
    args = parser.parse_args()

    run_daily_pipeline(
        category=args.category,
        topic=args.topic,
        use_scout=args.use_scout,
        publish=args.publish,
        variant=args.variant,
        bundle_path=args.bundle,
    )
