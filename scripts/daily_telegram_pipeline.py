#!/usr/bin/env python3
"""
Скрипт ежедневного пайплайна публикаций для сети апартаментов «Добрый дом Тюмень».
Автоматически:
1. Выбирает актуальную рубрику дня (ротация рубрик по дням недели).
2. Выполняет поиск актуальных событий / тем.
3. Формирует привлекательный текст с кнопками бронирования и акцентами.
4. Создает реалистичный промпт для GPT Image 2 / GRSAI с кириллицей и элементами бренда.
5. Обогащает изображение через Pexels API (натуральное освещение, живые интерьеры).
6. Генерирует изображение через GRSAI API (до 3 попыток) и отправляет единым постом (фото + текст + кнопки) в Telegram-группу [REDACTED].
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

from generate_telegram_post import build_post, send_to_telegram, generate_image_grsai, save_post

CATEGORIES_SCHEDULE = [
    "afisha",            # Понедельник
    "district_guide",    # Вторник
    "host_story",        # Среда (живой диалог и заметки радушного хозяина)
    "service_lifehack",  # Четверг
    "afisha",            # Пятница
    "special_offers",    # Суббота
    "city_guide"         # Воскресенье
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
    print("Генерация изображения через GRSAI API (до 3 попыток с интервалом)...")
    
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            print(f"Попытка генерации {attempt}/{max_attempts}...")
            photo_url = generate_image_grsai(prompt)
            if photo_url and photo_url.startswith("http"):
                print(f"Изображение успешно получено: {photo_url}")
                break
            else:
                print(f"Предупреждение: получен пустой ответ при генерации (попытка {attempt})")
        except Exception as e:
            print(f"Предупреждение: Ошибка генерации изображения на попытке {attempt} ({e}).")
        
        if attempt < max_attempts:
            wait_sec = 5 * attempt
            print(f"Ожидание {wait_sec} сек перед повторной попыткой...")
            time.sleep(wait_sec)
    
    # Правило защиты качества: если фото не получено — сухой пост без фото или с одиночным логотипом не отправлять!
    if not photo_url:
        print("ОШИБКА: Фотообложка не получена после всех попыток генерации.")
        print("В соответствии с правилами качества бренда, сухой пост без фото или с одиночным логотипом не отправляется.")
        sys.exit(1)
    
    if send:
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "[REDACTED]")
        target_chat = os.environ.get("TELEGRAM_CHAT_ID", "[REDACTED]")
        print(f"Отправка единого поста с фото в Telegram {target_chat}...")
        
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
