#!/usr/bin/env python3
"""
Скрипт генерации постов для Telegram-канала сети апартаментов «Добрый дом Тюмень».
Позволяет:
1. Задать тему или рубрику (афиша, ЖК, сервис, скидки, гид).
2. Выполнить поиск или принять входные данные из поиска.
3. Сформировать красиво оформленный пост в Telegram формате (HTML/Markdown) с кнопками и ссылками.
4. Сохранить пост в json/md для проверки или отправки через Telegram MCP.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_PATH = WORKSPACE_ROOT / "shared" / "telegram-post-templates.json"
TENANT_CONFIG_PATH = WORKSPACE_ROOT / "shared" / "tenant-config.json"
OUTPUT_DIR = WORKSPACE_ROOT / "memory" / "telegram_posts"


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


def build_sample_post(category_id: str, topic: str = "", details: str = "") -> dict:
    templates_data = load_templates()
    categories = {cat["id"]: cat for cat in templates_data.get("categories", [])}
    
    cat = categories.get(category_id, categories.get("afisha"))
    
    if category_id == "afisha":
        title = topic or "Куда сходить в Тюмени в ближайшие дни: главные события города 🎉"
        body = f"""🎭 <b>{title}</b>

Планируете поездку в Тюмень или хотите насыщенно провести выходные? Собрали для вас топ событий, которые точно стоит посетить:

1️⃣ <b>Прогулки и события на Набережной</b> — сердце города и единственная четырёхуровневая набережная в России.
2️⃣ <b>Термальные комплексы («ЛетоЛето», «Верхний бор»)</b> — визитная карточка Тюмени, где можно расслабиться в горячей минеральной воде под открытым небом.
3️⃣ <b>Пешеходная улица Дзержинского</b> — тюменский Арбат с деревянным зодчеством, атмосферными кофейнями и сувенирными лавками.

{details or 'После насыщенного дня так приятно вернуться в тёплую, уютную квартиру, принять душ и выпить чашку ароматного чая!'}

🏡 <b>«Добрый дом» — более 60 квартир во всех районах Тюмени:</b>
✅ Бесконтактное заселение 24/7 за 5 минут
✅ Отельное постельное бельё и полотенца
✅ Всё для гигиены, фен, утюг, Wi-Fi и посуда
✅ Отчётные документы с QR-кодом для командировок

💡 <i>Бронируйте заранее, чтобы выбрать квартиру в самом удобном для вас районе!</i>"""

    elif category_id == "district_guide":
        title = topic or "Где остановиться в Тюмени: уютные квартиры в ЖК «Новин» и «Европейский» 🏙"
        body = f"""🏙 <b>{title}</b>

Выбираете квартиру для поездки в Тюмень? Делимся лучшими локациями для отдыха и деловых поездок:

✨ <b>ЖК «Новин» (центр / 50 лет Октября)</b>
Идеально для командировок и тех, кому важна транспортная доступность. Закрытые дворы, стильная архитектура, кафе и супермаркеты прямо в доме.

🌿 <b>ЖК «Европейский» и «Европейский Берег» (Зарека / Газовиков)</b>
Лучший выбор для семей и пар: рядом благоустроенная набережная, аквапарк «ЛетоЛето», тихие дворы и красивый вид на реку Туру.

{details or 'В каждой квартире «Доброго дома» вас ждет безупречная чистота, удобные матрасы, быстрый Wi-Fi и всё необходимое для приготовления любимых блюд.'}

🔑 <b>Почему выбирают «Добрый дом»:</b>
• Круглосуточный заезд без ожидания ключей
• Ответ администратора в мессенджере за 5 минут
• Честные цены без скрытых комиссий"""

    elif category_id == "service_lifehack":
        title = topic or "Как заселиться в апартаменты в Тюмени за 5 минут без встреч и ожидания? 🗝"
        body = f"""⏱ <b>{title}</b>

Приехали в Тюмень поздней ночью или после долгой дороги и не хотите ждать администратора с ключами? 

В сети апартаментов <b>«Добрый дом»</b> действует быстрое и безопасное <b>бесконтактное заселение 24/7</b>!

<b>Как это работает:</b>
1. Бронируете квартиру на нашем сайте или в Telegram.
2. Получаете подробную понятную инструкцию с кодом доступа.
3. Заезжаете в любое удобное время — ключ ждет вас на месте.
4. Администратор всегда на связи в мессенджере и ответит на любой вопрос за 5 минут.

🧼 <b>Внутри вас уже ждут:</b>
• Свежее выглаженное бельё и полотенца
• Индивидуальные наборы (шампунь, гель, зубная паста и щётка, тапочки)
• Чай, сахар, посуда, техника и быстрый интернет

📑 <i>Для командировочных предоставляем полный пакет закрывающих документов с кассовым чеком и QR-кодом.</i>"""

    elif category_id == "special_offers":
        title = topic or "Скидка 10% на проживание в Тюмени: как сэкономить на бронировании 🎁"
        body = f"""🔥 <b>{title}</b>

Путешествовать и останавливаться в Тюмени с комфортом можно ещё выгоднее! В сети <b>«Добрый дом»</b> действуют специальные тарифы:

💰 <b>Тариф «Раннее бронирование»:</b>
Планируете поездку заранее? Забронируйте квартиру за 20 дней до заезда и получите <b>скидку 10%</b>!

✈️ <b>Тариф «Длительное проживание»:</b>
При бронировании от 10 ночей — скидка 10% на весь период проживания. Полная уборка и смена белья включены.

🏠 Более 60 апартаментов на выбор: от компактных стильных студий до просторных 2-3 комнатных квартир в лучших ЖК Тюмени."""

    else:  # city_guide
        title = topic or "Топ горячих источников Тюмени: где согреться и отдохнуть душой ♨️"
        body = f"""♨️ <b>{title}</b>

Тюмень официально признана столицей термальных вод России! Если вы приехали в наш город, обязательно посетите горячие минеральные источники:

1. <b>ЛетоЛето</b> — крупнейший термальный курорт с аквапарком и спа-комплексом.
2. <b>Верхний бор</b> — легендарный источник в сосновом бору с минеральными бассейнами.
3. <b>Аван</b> — загородный клуб с целебной термальной водой и банным комплексом.

{details or 'После купания в термах — самое время отдохнуть в тёплой квартире «Добрый дом». У нас есть квартиры в 5 минутах от аквапарка «ЛетоЛето»!'}

✨ <b>Забронируйте апартаменты на нужные даты прямо сейчас:</b>"""

    buttons = [
        [
            {"text": "🌐 Забронировать на сайте", "url": "https://добрый-дом-тюмень.рф"},
            {"text": "💬 Написать администратору", "url": "https://t.me/dobrydom72"}
        ]
    ]

    post_data = {
        "title": title,
        "category_id": category_id,
        "category_name": cat.get("name", ""),
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text_html": body,
        "inline_buttons": buttons,
        "meta": {
            "source_topic": topic,
            "brand": "Добрый дом Тюмень",
            "phone": "+7 (993) 574-83-22",
            "website": "https://добрый-дом-тюмень.рф"
        }
    }
    return post_data


def save_post(post_data: dict, filename: str = None) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"post_{post_data['category_id']}_{timestamp}.json"
    
    file_path = OUTPUT_DIR / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(post_data, f, ensure_ascii=False, indent=2)
    
    # Также сохраняем читаемый markdown файл
    md_path = file_path.with_suffix(".md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# {post_data['title']}\n\n")
        f.write(f"**Категория:** {post_data['category_name']}\n")
        f.write(f"**Дата:** {post_data['created_at']}\n\n")
        f.write("---\n\n")
        f.write(post_data["text_html"])
        f.write("\n\n---\n**Кнопки:**\n")
        for row in post_data["inline_buttons"]:
            for btn in row:
                f.write(f"- [{btn['text']}]({btn['url']})\n")
                
    return file_path


def main():
    parser = argparse.ArgumentParser(description="Генератор постов для Telegram (Добрый дом Тюмень)")
    parser.add_argument("--category", choices=["afisha", "district_guide", "service_lifehack", "special_offers", "city_guide"], default="afisha", help="Категория поста")
    parser.add_argument("--topic", type=str, default="", help="Тема или заголовок поста")
    parser.add_argument("--details", type=str, default="", help="Дополнительные детали из поиска/новости")
    parser.add_argument("--save", action="store_true", help="Сохранить результат в memory/telegram_posts/")
    
    args = parser.parse_args()
    
    post = build_sample_post(args.category, args.topic, args.details)
    
    print("\n" + "="*50)
    print(f"СГЕНЕРИРОВАННЫЙ ПОСТ ДЛЯ TELEGRAM [{post['category_name']}]")
    print("="*50 + "\n")
    print(post["text_html"])
    print("\n" + "-"*50)
    print("Инлайн-кнопки:")
    for row in post["inline_buttons"]:
        for btn in row:
            print(f"  [{btn['text']}] -> {btn['url']}")
    print("="*50 + "\n")
    
    if args.save or True:
        saved_path = save_post(post)
        print(f"Пост успешно сохранён в: {saved_path}")


if __name__ == "__main__":
    main()
