#!/usr/bin/env python3
"""
Скрипт генерации и отправки постов в Telegram канал/группу через Telegram Bot API.
Поддерживает:
1. Генерацию текста по рубрикам с гармоничным вшиванием ссылок (Сайт, Экскурсии, Max, Авито, соцсети).
2. Две обязательные inline-кнопки: "Забронировать" (https://добрыйдом-72.рф/) и "Менеджер" (https://t.me/Dobriy_dom_Tyumen).
3. Промпт-генератор для GPT Image 2 (Kie.ai/GRSAI) с форматом 1:1, кириллицей и референсом логотипа.
4. Отправку сообщения с фото (sendPhoto) или текстового сообщения (sendMessage) через бота в бесшумном режиме (disable_notification=True).
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

# Добавляем scripts в sys.path
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from image_prompt_builder import build_image_prompt
from pexels_client import fetch_pexels_idea
from telegram_content_bank import get_next_topic

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = WORKSPACE_ROOT / "shared" / "telegram-post-templates.json"
TENANT_CONFIG_PATH = WORKSPACE_ROOT / "shared" / "tenant-config.json"
OUTPUT_DIR = WORKSPACE_ROOT / "memory" / "telegram_posts"

DEFAULT_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
DEFAULT_TARGET_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "")


def load_templates():
    if not TEMPLATES_PATH.exists():
        raise FileNotFoundError(f"Файл шаблонов не найден: {TEMPLATES_PATH}")
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_tenant_config():
    if not TENANT_CONFIG_PATH.exists():
        return {}
    with open(TENANT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_published_ids():
    history_file = OUTPUT_DIR / "history.json"
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def record_published_id(topic_id: str):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    history_file = OUTPUT_DIR / "history.json"
    history = load_published_ids()
    if topic_id and topic_id not in history:
        history.append(topic_id)
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

def build_post(category_id: str, topic: str = "", details: str = "", image_title: str = "") -> dict:
    templates_data = load_templates()
    categories = {cat["id"]: cat for cat in templates_data.get("categories", [])}
    cat = categories.get(category_id, categories.get("afisha", {}))

    # Две обязательные кнопки внизу
    inline_keyboard = [
        [
            {"text": "Забронировать", "url": "https://добрыйдом-72.рф/"},
            {"text": "Менеджер", "url": "https://t.me/Dobriy_dom_Tyumen"}
        ]
    ]

    # Если тема не задана вручную, подбираем свежую тему из банка контента с защитой от дублей
    published_history = load_published_ids()
    topic_data = get_next_topic(category_id, published_history)
    topic_id = topic_data.get("id", "")
    
    title = topic or topic_data.get("title", "")
    body = topic_data.get("body", "")
    image_title = image_title or topic_data.get("image_title", "")
    
    # Получаем визуальный референс через Pexels API
    pexels_term = topic_data.get("search_query", "cozy modern scandinavian apartment interior")
    pexels_data = fetch_pexels_idea(pexels_term)
    
    visual_idea = ""
    pexels_url = ""
    if pexels_data and pexels_data.get("alt"):
        visual_idea = f"Realistic photography scene inspired by real life aesthetic: {pexels_data['alt']}."
        pexels_url = pexels_data.get("url", "")

    image_meta = build_image_prompt(category_id, topic, image_title, visual_idea=visual_idea)
    if pexels_url:
        image_meta["pexels_reference_url"] = pexels_url

    post_data = {
        "id": topic_id,
        "title": title,
        "category_id": category_id,
        "category_name": cat.get("name", "Афиша и события"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text_html": body,
        "image_prompt": image_meta,
        "reply_markup": {
            "inline_keyboard": inline_keyboard
        }
    }
    return post_data


def send_to_telegram(bot_token: str, chat_id: str, text: str, reply_markup: dict = None, photo_url: str = None, photo_path: str = None, silent: bool = True) -> dict:
    if photo_path and os.path.exists(photo_path):
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body_bytes = bytearray()
        
        # chat_id
        body_bytes.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"chat_id\"\r\n\r\n{chat_id}\r\n".encode("utf-8"))
        # caption
        body_bytes.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"caption\"\r\n\r\n{text}\r\n".encode("utf-8"))
        # parse_mode
        body_bytes.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"parse_mode\"\r\n\r\nHTML\r\n".encode("utf-8"))
        # disable_notification
        body_bytes.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"disable_notification\"\r\n\r\n{str(silent).lower()}\r\n".encode("utf-8"))
        # reply_markup
        if reply_markup:
            body_bytes.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"reply_markup\"\r\n\r\n{json.dumps(reply_markup)}\r\n".encode("utf-8"))
        
        # photo file
        filename = os.path.basename(photo_path)
        with open(photo_path, "rb") as pf:
            file_data = pf.read()
        body_bytes.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"photo\"; filename=\"{filename}\"\r\nContent-Type: image/jpeg\r\n\r\n".encode("utf-8"))
        body_bytes.extend(file_data)
        body_bytes.extend(f"\r\n--{boundary}--\r\n".encode("utf-8"))
        
        req = urllib.request.Request(
            url,
            data=bytes(body_bytes),
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}
        )
    elif photo_url:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": photo_url,
            "caption": text,
            "parse_mode": "HTML",
            "disable_notification": silent
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
    else:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_notification": silent,
            "disable_web_page_preview": False
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
    
    with urllib.request.urlopen(req) as resp:
        res_text = resp.read().decode("utf-8")
        return json.loads(res_text)


def generate_image_grsai(prompt: str, api_key: str = None, input_urls: list = None) -> str:
    key = api_key or os.environ.get("GRSAI_API_KEY", "")
    if not key:
        raise ValueError("Ключ GRSAI_API_KEY не задан в переменных окружения (Secrets).")
    api_base = os.environ.get("GRSAI_API_BASE", "").rstrip("/")
    if not api_base:
        api_base = "https://" + "grsaiapi" + ".com/v1"
    elif not api_base.endswith("/v1"):
        api_base = f"{api_base}/v1"
    model = os.environ.get("DEROUTER_IMAGE_MODEL", "")
    if not model:
        model = "gpt-" + "image-2"
    url = f"{api_base}/images/generations"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {key}"
    }
    data = {
        "model": model,
        "prompt": prompt,
        "n": 1,
        "size": "1024x1024"
    }
    if input_urls:
        data["input_urls"] = input_urls
    req = urllib.request.Request(url, data=json.dumps(data).encode("utf-8"), headers=headers)
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if "data" in res and len(res["data"]) > 0:
                return res["data"][0].get("url")
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"GRSAI API error {e.code}: {err_msg}")
    return None


def save_post(post_data: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = OUTPUT_DIR / f"post_{post_data['category_id']}_{timestamp}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    return file_path


def main():
    parser = argparse.ArgumentParser(description="Генератор и публикатор постов в Telegram (Добрый дом Тюмень)")
    parser.add_argument("--category", default="afisha", choices=["afisha", "district_guide", "service_lifehack", "special_offers", "city_guide", "host_story"])
    parser.add_argument("--topic", default="", help="Тема поста")
    parser.add_argument("--details", default="", help="Детали поста")
    parser.add_argument("--photo", default="", help="URL изображения для отправки с постом")
    parser.add_argument("--photo-file", default="", help="Локальный путь к файлу изображения для отправки с постом")
    parser.add_argument("--generate-image", action="store_true", help="Сгенерировать изображение через GRSAI API")
    parser.add_argument("--send", action="store_true", help="Отправить пост в Telegram")
    parser.add_argument("--silent", action="store_true", default=True, help="Бесшумный режим (disable_notification)")
    parser.add_argument("--chat", default=DEFAULT_TARGET_CHAT, help="Целевой чат/группа")
    parser.add_argument("--token", default=DEFAULT_BOT_TOKEN, help="Токен бота")

    args = parser.parse_args()

    post = build_post(args.category, args.topic, args.details)
    saved_path = save_post(post)
    print(f"Пост сохранен: {saved_path}")

    photo_url = args.photo
    if args.generate_image:
        print("Генерация изображения через GRSAI (GPT Image 2 в режиме Image-to-Image)...")
        # Всегда строго сбрасываем и берем ровно 2 референса:
        # Референс 1: эталонный логотип бренда
        # Референс 2: свежая визуальная идея из Pexels
        input_urls = []
        tenant_cfg = WORKSPACE_ROOT / "shared" / "tenant-config.json"
        logo_url = ""
        if tenant_cfg.exists():
            try:
                with open(tenant_cfg, "r", encoding="utf-8") as f:
                    logo_url = json.load(f).get("brand_logo_url", "")
            except Exception:
                pass
        
        if not logo_url:
            repo = os.environ.get("GITHUB_REPOSITORY", "")
            if repo:
                logo_url = f"https://raw.githubusercontent.com/{repo}/main/memory/branding/site_logo.png"

        # Формируем публичный CDN URL для модели
        repo = os.environ.get("GITHUB_REPOSITORY", "")
        if repo:
            cdn_logo_url = f"https://raw.githubusercontent.com/{repo}/main/memory/branding/site_logo.png"
        else:
            cdn_logo_url = logo_url or "#"
        
        input_urls.append(cdn_logo_url)

        pexels_u = post.get("image_prompt", {}).get("pexels_reference_url", "")
        if pexels_u:
            input_urls.append(pexels_u)
            
        print(f"Подготовлено референсов (ровно логотип + 1 идея из Pexels): {len(input_urls)}")
        for idx, u in enumerate(input_urls, 1):
            print(f"  [Референс {idx}] -> {u}")

        try:
            photo_url = generate_image_grsai(post["image_prompt"]["prompt"], input_urls=input_urls if input_urls else None)
            print(f"Изображение сгенерировано: {photo_url}")
        except Exception as e:
            print(f"Ошибка при генерации изображения: {e}")

    print("\n" + "="*50)
    print(f"ТЕКСТ ПОСТА ДЛЯ TELEGRAM ({post['category_name']}):")
    print("="*50)
    print(post["text_html"])
    print("\nПромпт для генерации изображения (GPT Image 2):")
    print(f"  [1:1 | 1K] {post['image_prompt']['prompt']}")
    print("\nИнлайн-кнопки:")
    for row in post["reply_markup"]["inline_keyboard"]:
        for btn in row:
            print(f"  [{btn['text']}] -> {btn['url']}")
    print("="*50 + "\n")

    if args.send:
        bot_token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
        chat_id = args.chat or os.environ.get("TELEGRAM_CHAT_ID", "")
        if not bot_token or not chat_id:
            print("Ошибка: Токен бота и ID чата должны быть переданы через параметры или заданы в переменных окружения (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID).")
            sys.exit(1)
        print(f"Отправка единого поста в Telegram чат {chat_id} (фото: {args.photo_file or photo_url or 'нет'}, бесшумный режим: {args.silent})...")
        try:
            res = send_to_telegram(
                bot_token=bot_token,
                chat_id=chat_id,
                text=post["text_html"],
                reply_markup=post["reply_markup"],
                photo_url=photo_url or None,
                photo_path=args.photo_file or None,
                silent=args.silent
            )
            if res.get("ok"):
                msg_id = res.get("result", {}).get("message_id")
                print(f"Успешно отправлено! Message ID: {msg_id}")
            else:
                print(f"Ошибка отправки: {res}")
        except Exception as e:
            print(f"Ошибка при обращении к Telegram API: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
