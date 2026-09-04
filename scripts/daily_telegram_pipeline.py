#!/usr/bin/env python3
"""
Скрипт ежедневного пайплайна публикаций для сети апартаментов «Добрый дом Тюмень».
Автоматически:
1. Выбирает актуальную рубрику дня (ротация рубрик по дням недели).
2. Выполняет поиск актуальных событий / тем.
3. Формирует привлекательный текст с кнопками бронирования и акцентами.
4. Создает реалистичный промпт для GPT Image 2 / GRSAI с кириллицей и элементами бренда.
5. Генерирует изображение через GRSAI API и отправляет единым постом (фото + текст + кнопки) в целевой Telegram-канал/группу из настроек TELEGRAM_CHAT_ID.
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime
from pathlib import Path

# Добавляем scripts в sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from generate_telegram_post import build_post, send_to_telegram, generate_image_grsai, save_post, record_published_id
from telegram_credentials import load_telegram_credentials
from ftp_uploader import upload_file_to_ftp

CATEGORIES_SCHEDULE = [
    "afisha",                # 0 (Понедельник): Афиша и события Тюмени
    "district_guide",        # 1 (Вторник): Гид по районам и лучшим ЖК города
    "host_story",            # 2 (Среда): Заметки радушного "хозяина" (живой диалог от первого лица)
    "service_standards",     # 3 (Четверг): Сервис, забота и стандарты чистоты
    "weekend_thermal",       # 4 (Пятница): Планы на выходные и термальная столица (термы, экскурсии)
    "special_offers",        # 5 (Суббота): Акции, тарифы и спецпредложения (скидки 10%, выгода сайта)
    "siberian_hospitality"   # 6 (Воскресенье): Уютные истории и сибирское гостеприимство
]

def get_today_category():
    weekday = datetime.now().weekday()  # 0: Monday, 6: Sunday
    return CATEGORIES_SCHEDULE[weekday]

def run_daily_pipeline(category: str = None, topic: str = "", send: bool = True):
    cat = category or get_today_category()
    print(f"=== Запуск ежедневного пайплайна [Категория: {cat}] ===")
    
    post = build_post(category_id=cat, topic=topic)
    saved_path = save_post(post)
    print(f"Черновик поста сохранен в: {saved_path}")
    
    photo_url = None
    prompt = post["image_prompt"]["prompt"]
    
    # Подготовка референсов для Image-to-Image режима:
    # Всегда строго сбрасываем список и используем ровно 2 актуальных референса:
    # 1. Эталонный логотип бренда
    # 2. Новая уникальная идея из Pexels под тему сегодняшнего поста
    input_urls = []
    tenant_cfg = SCRIPT_DIR.parent / "shared" / "tenant-config.json"
    cfg_logo_url = ""
    if tenant_cfg.exists():
        try:
            with open(tenant_cfg, "r", encoding="utf-8") as f:
                cfg_logo_url = json.load(f).get("brand_logo_url", "")
        except Exception:
            pass
            
    # Референс 1: Эталонный логотип бренда
    # Приоритет 1: Прямой CDN/сайт URL логотипа для максимального качества Image-to-Image модели
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

    # 2. Свежий визуальный референс стиля и композиции из Pexels
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
            else:
                print(f"Попытка {attempt}: API не вернул URL изображения.")
        except Exception as e:
            print(f"Попытка {attempt} завершилась с ошибкой: {e}")
        
        if attempt < max_retries:
            print(f"Ожидание {retry_delay_seconds} сек перед следующей попыткой...")
            time.sleep(retry_delay_seconds)

    if not photo_url:
        print("КРИТИЧЕСКАЯ ОШИБКА: Не удалось сгенерировать изображение после 3 попыток.")
        print("В соответствии с правилами качества бренда публикация 'сухого' поста без сгенерированного фото или с одиночным логотипом отменена.")
        sys.exit(1)
    
    if send:
        creds = load_telegram_credentials()
        bot_token = creds["bot_token"]
        target_chat = creds["chat_id"]
        if not bot_token or not target_chat:
            print("Ошибка: Переменные TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID должны быть заданы в окружении (Secrets)!")
            sys.exit(1)
        print(f"Отправка единого поста в Telegram {target_chat}...")
        
        res = send_to_telegram(
            bot_token=bot_token,
            chat_id=target_chat,
            text=post["text_html"],
            reply_markup=post["reply_markup"],
            photo_url=photo_url,
            photo_path=None,
            silent=True
        )
        if res.get("ok"):
            msg_id = res.get("result", {}).get("message_id")
            print(f"Пост успешно опубликован! Telegram Message ID: {msg_id}")
            if post.get("id"):
                record_published_id(post["id"], category_id=post.get("category_id", cat))
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
