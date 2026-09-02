#!/usr/bin/env python3
"""
Скрипт генерации и отправки постов в Telegram канал/группу через Telegram Bot API.
Требования к форматированию:
1. Без эмодзи в тексте (разрешена только цифровая нумерация 1️⃣, 2️⃣, 3️⃣ и т.д.).
2. Акцент на бронирование на официальном сайте (https://добрыйдом-72.рф/), где цены ниже и удобнее.
3. Органичная интеграция партнеров (экскурсии https://добрыйдом-72.рф/excursions/), Авито, Макс и соцсетей.
4. Две обязательные inline-кнопки: "Забронировать" (https://добрыйдом-72.рф/) и "Менеджер" (https://t.me/Dobriy_dom_Tyumen).
5. Бесшумный режим отправки по умолчанию (disable_notification=True).
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.parse
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = WORKSPACE_ROOT / "shared" / "telegram-post-templates.json"
TENANT_CONFIG_PATH = WORKSPACE_ROOT / "shared" / "tenant-config.json"
OUTPUT_DIR = WORKSPACE_ROOT / "memory" / "telegram_posts"

DEFAULT_BOT_TOKEN = "8724220345:AAH--Vc3ovIGDTlyr-yWRI6oqwHerrys-hU"
DEFAULT_TARGET_CHAT = "@SMM_ddom"


def load_templates():
    if not TEMPLATES_PATH.exists():
        raise FileNotFoundError(f"Файл шаблонов не найден: {TEMPLATES_PATH}")
    with open(TEMPLATES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_post(category_id: str, topic: str = "", details: str = "") -> dict:
    templates_data = load_templates()
    categories = {cat["id"]: cat for cat in templates_data.get("categories", [])}
    cat = categories.get(category_id, categories.get("afisha", {}))

    # Две кнопки внизу по строгому требованию
    inline_keyboard = [
        [
            {"text": "Забронировать", "url": "https://добрыйдом-72.рф/"},
            {"text": "Менеджер", "url": "https://t.me/Dobriy_dom_Tyumen"}
        ]
    ]

    if category_id == "afisha":
        title = topic or "Куда сходить в Тюмени: термальные источники, экскурсии и прогулки по городу"
        body = f"""<b>{title}</b>

Планируете визит в Тюмень или хотите насыщенно провести выходные? Собрали ключевые идеи для отдыха:

1️⃣ <b>Термальные комплексы</b> — «ЛетоЛето» и «Верхний бор». Минеральная горячая вода на открытом воздухе доступна в любое время года.
2️⃣ <b>Прогулки по историческому центру</b> — четырёхуровневая Набережная Туры и пешеходная улица Дзержинского со старинными купеческими усадьбами.
3️⃣ <b>Туры и экскурсии по Тюмени</b> — познакомиться с историей Сибири и необычными локациями города можно в рамках специальных <a href="https://добрыйдом-72.рф/excursions/">экскурсионных программ от наших партнеров</a>.

{details or 'После прогулок и экскурсий вас ждут уютные апартаменты, где есть всё необходимое: от мягкой кровати и отельного белья до скоростного Wi-Fi и оборудованной кухни.'}

<b>Сеть апартаментов «Добрый дом»:</b>
- Более 60 квартир во всех районах города (ЖК Новин, Европейский Берег, Видный, Центр)
- Круглосуточное бесконтактное заселение за 5 минут без ожидания
- Безупречная чистота, одноразовая гигиена, полотенца, фен и стиральная машина
- Полный пакет отчетных документов с QR-кодом для командировочных

Выбирать и бронировать квартиру напрямую выгоднее и удобнее всего на нашем <a href="https://добрыйдом-72.рф/">официальном сайте</a> — здесь действуют прямые цены без комиссий посредников.

Также отзывы гостей и каталог доступны в нашем <a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">профиле на Авито</a> и на витрине <a href="https://max.ru/id660300569233_biz">Макс</a>.

Наш канал с новостями и акциями: <a href="https://t.me/Dobriy_dom_72">@Dobriy_dom_72</a>"""

    elif category_id == "district_guide":
        title = topic or "Где остановиться в Тюмени: обзор районов и жилых комплексов"
        body = f"""<b>{title}</b>

Подготовили навигатор по основным локациям Тюмени для гостей города и деловых путешественников:

1️⃣ <b>ЖК «Новин» (Центральный район / 50 лет Октября)</b>
Деловой квартал с закрытой территорией, ресторанами и быстрым доступом к ключевым транспортным магистралям. Отличный выбор для командировок.

2️⃣ <b>ЖК «Европейский» и «Европейский Берег» (Заречная часть)</b>
Современный европейский квартал у реки Туры, в 5 минутах от аквапарка «ЛетоЛето». Прогулочные зоны, тишина и семейный уют.

3️⃣ <b>ЖК «Видный» и «Звёздный»</b>
Развитые современные микрорайоны рядом с крупными торгово-развлекательными центрами («Кристалл», «СитиМолл»).

{details or 'В каждом объекте «Доброго дома» действует круглосуточный заезд без ожидания администратора.'}

Прямое бронирование по самым низким ценам доступно на <a href="https://добрыйдом-72.рф/">официальном сайте</a>. Каталог квартир и отзывы гостей также представлены на <a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">Авито</a> и в сервисе <a href="https://max.ru/id660300569233_biz">Макс</a>."""

    elif category_id == "service_lifehack":
        title = topic or "Бесконтактный заезд 24/7: как заселиться в квартиру за 5 минут"
        body = f"""<b>{title}</b>

При позднем рейсе или плотном графике поездки не нужно подстраиваться под встречи с администратором.

1️⃣ <b>Быстрый выбор</b>: оформляете бронь на нашем <a href="https://добрыйдом-72.рф/">официальном сайте</a> (по лучшим прямым ценам) или через <a href="https://t.me/Dobriy_dom_Tyumen">менеджера</a>.
2️⃣ <b>Понятная инструкция</b>: получаете подробное руководство с кодом доступа.
3️⃣ <b>Круглосуточный заезд</b>: заходите в квартиру в любое удобное время суток за 5 минут.

<b>Стандарты подготовки каждого номера:</b>
- Отельное постельное белье и свежие полотенца
- Индивидуальные гигиенические наборы (зубная щетка, паста, шампунь, гель)
- Скоростной Wi-Fi, фен, утюг, стиральная машина и посуда
- Кассовый чек с QR-кодом для бухгалтерии

Ознакомиться с отзывами можно на <a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">Авито</a>, а актуальные предложения всегда доступны в нашем канале <a href="https://t.me/Dobriy_dom_72">@Dobriy_dom_72</a>."""

    elif category_id == "special_offers":
        title = topic or "Специальные тарифы и скидки на проживание в Тюмени"
        body = f"""<b>{title}</b>

Бронировать квартиры напрямую на официальном сайте «Доброго дома» всегда выгоднее:

1️⃣ <b>Тариф «Раннее бронирование»</b>: скидка 10% при заказе за 20 дней до даты заезда.
2️⃣ <b>Тариф «Длительное проживание»</b>: скидка 10% на все бронирования от 10 ночей со включенной регулярной уборкой и сменой белья.

Все актуальные цены и свободные даты без посредников и комиссий представлены на <a href="https://добрыйдом-72.рф/">сайте добрыйдом-72.рф</a>. 

Посмотреть витрину можно также в сервисе <a href="https://max.ru/id660300569233_biz">Макс</a> и в <a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">профиле Авито</a>."""

    else:
        title = topic or "Гид по Тюмени: термальные воды, экскурсионные туры и гастрономия"
        body = f"""<b>{title}</b>

Тюмень — первый русский город Сибири и термальная столица страны. Что обязательно включить в маршрут:

1️⃣ <b>Термальные источники</b> — горячие минеральные бассейны на свежем воздухе в «ЛетоЛето» и «Верхнем бору».
2️⃣ <b>Экскурсии по городу и окрестностям</b> — тематические пешеходные и автобусные маршруты от наших партнеров собраны на странице <a href="https://добрыйдом-72.рф/excursions/">экскурсий</a>.
3️⃣ <b>Сибирская кухня</b> — строганина, блюда из дичи и сибирские десерты в заведениях исторического центра.

Для комфортного проживания выбирайте любую из 60+ квартир «Доброго дома». Прямые цены без наценок всегда ждут вас на <a href="https://добрыйдом-72.рф/">официальном сайте</a>."""

    post_data = {
        "title": title,
        "category_id": category_id,
        "category_name": cat.get("name", "Афиша и события"),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text_html": body,
        "reply_markup": {
            "inline_keyboard": inline_keyboard
        }
    }
    return post_data


def send_to_telegram(bot_token: str, chat_id: str, text: str, reply_markup: dict = None, silent: bool = True) -> dict:
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


def save_post(post_data: dict) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = OUTPUT_DIR / f"post_{post_data['category_id']}_{timestamp}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    return file_path


def main():
    parser = argparse.ArgumentParser(description="Генератор и публикатор постов в Telegram (Добрый дом Тюмень)")
    parser.add_argument("--category", default="afisha", choices=["afisha", "district_guide", "service_lifehack", "special_offers", "city_guide"])
    parser.add_argument("--topic", default="", help="Тема поста")
    parser.add_argument("--details", default="", help="Детали поста")
    parser.add_argument("--send", action="store_true", help="Отправить пост в Telegram")
    parser.add_argument("--silent", action="store_true", default=True, help="Бесшумный режим (disable_notification)")
    parser.add_argument("--chat", default=DEFAULT_TARGET_CHAT, help="Целевой чат/группа")
    parser.add_argument("--token", default=DEFAULT_BOT_TOKEN, help="Токен бота")

    args = parser.parse_args()

    post = build_post(args.category, args.topic, args.details)
    saved_path = save_post(post)
    print(f"Пост сохранен: {saved_path}")

    print("\n" + "="*50)
    print(f"ТЕКСТ ПОСТА ДЛЯ TELEGRAM ({post['category_name']}):")
    print("="*50)
    print(post["text_html"])
    print("\nИнлайн-кнопки:")
    for row in post["reply_markup"]["inline_keyboard"]:
        for btn in row:
            print(f"  [{btn['text']}] -> {btn['url']}")
    print("="*50 + "\n")

    if args.send:
        print(f"Отправка в Telegram чат {args.chat} (бесшумный режим: {args.silent})...")
        try:
            res = send_to_telegram(
                bot_token=args.token,
                chat_id=args.chat,
                text=post["text_html"],
                reply_markup=post["reply_markup"],
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
