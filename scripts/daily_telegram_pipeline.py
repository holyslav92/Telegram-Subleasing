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

from generate_telegram_post import build_post, send_to_telegram, generate_image_grsai, save_post

CATEGORIES_SCHEDULE = [
    "afisha",            # Понедельник: афиша и события
    "district_guide",    # Вторник: гид по районам и ЖК
    "host_story",        # Среда: живой диалог и заметки радушного хозяина
    "service_lifehack",  # Четверг: сервис и бесконтактный заезд 24/7
    "afisha",            # Пятница: планы на выходные и отдых
    "special_offers",    # Суббота: скидки и тарифы
    "city_guide"         # Воскресенье: гид по термам и сибирским прогулкам
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
    print("Генерация изображения через GRSAI API (до 3 попыток)...")
    
    max_retries = 3
    retry_delay_seconds = 5
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Попытка генерации {attempt} из {max_retries}...")
            photo_url = generate_image_grsai(prompt)
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
        bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
        target_chat = os.environ.get("TELEGRAM_CHAT_ID", "")
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
