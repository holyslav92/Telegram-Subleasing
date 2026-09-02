#!/usr/bin/env python3
"""
Скрипт генерации и отправки постов в Telegram канал/группу через Telegram Bot API.
Поддерживает:
1. Генерацию текста по рубрикам с гармоничным вшиванием ссылок (Max, Авито, сайт, соцсети).
2. Две обязательные inline-кнопки: "Забронировать" (https://добрыйдом-72.рф/) и "Менеджер" (https://t.me/Dobriy_dom_Tyumen).
3. Бесшумный режим отправки (disable_notification=True).
4. Отправку через указанного бота в группу/канал @SMM_ddom.
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


def load_tenant_config():
    if not TENANT_CONFIG_PATH.exists():
        return {}
    with open(TENANT_CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def build_post(category_id: str, topic: str = "", details: str = "") -> dict:
    templates_data = load_templates()
    categories = {cat["id"]: cat for cat in templates_data.get("categories", [])}
    cat = categories.get(category_id, categories.get("afisha", {}))

    # Стандартные две кнопки внизу по требованию
    inline_keyboard = [
        [
            {"text": "Забронировать", "url": "https://добрыйдом-72.рф/"},
            {"text": "Менеджер", "url": "https://t.me/Dobriy_dom_Tyumen"}
        ]
    ]

    if category_id == "afisha":
        title = topic or "Куда сходить в Тюмени: яркие события и уютный отдых 🎉"
        body = f"""🎭 <b>{title}</b>

Планируете поездку в Тюмень или хотите отлично провести выходные? Собрали для вас главные точки притяжения города:

1️⃣ <b>Термальные источники</b> — визитная карточка Тюмени («ЛетоЛето», «Верхний бор»). Расслабиться в горячей минеральной воде под открытым небом — лучший сибирский релакс!
2️⃣ <b>Прогулки по 4-уровневой Набережной и улице Дзержинского</b> — уникальное деревянное зодчество, уютные кофейни и неповторимая атмосфера.
3️⃣ <b>Культурный вечер</b> — спектакли в Тюменском драматическом театре или выставки в Музейном комплексе им. Словцова.

{details or 'А после насыщенного дня так приятно вернуться в тёплую и чистую квартиру, выпить чашку чая и как следует выспаться на мягкой кровати с отельным бельём.'}

🏠 <b>«Добрый дом» — сервис №1 по посуточной аренде в Тюмени:</b>
• Более 60 квартир и студий во всех районах (ЖК Новин, Европейский, Видный, Центр)
• Бесконтактное заселение 24/7 — заезжайте в любое время за 5 минут
• Одноразовые наборы гигиены, полотенца, фен, Wi-Fi и вся посуда
• Честные отчетные документы с QR-кодом для командировок

⭐️ Читайте реальные отзывы гостей и смотрите все квартиры в нашем <a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">профиле на Авито</a>, а также заглядывайте на нашу витрину в <a href="https://max.ru/id660300569233_biz">Макс</a>!

💡 <i>Подписывайтесь на наш канал <a href="https://t.me/Dobriy_dom_72">@Dobriy_dom_72</a>, чтобы не пропускать скидки и афишу!</i>"""

    elif category_id == "district_guide":
        title = topic or "Где остановиться в Тюмени: гид по районам и лучшим ЖК 🏙"
        body = f"""🏙 <b>{title}</b>

Выбираете, в каком районе Тюмени снять квартиру посуточно? Подготовили краткий путеводитель по популярным локациям:

✨ <b>ЖК «Новин» (Центр / 50 лет Октября)</b>
Деловой центр города. Идеально для командировок: закрытая территория, кафе, супермаркеты и удобный выезд во все стороны.

🌊 <b>ЖК «Европейский» и «Европейский Берег» (Зарека)</b>
Европейская архитектура, набережная Туры, тихие дворы и всего 5 минут до аквапарка «ЛетоЛето». Любимый выбор семей и туристов!

🌿 <b>ЖК «Видный» и «Звёздный»</b>
Современные районы с прекрасной инфраструктурой, парками и близостью к крупным ТРЦ («СитиМолл», «Кристалл»).

{details or 'В каждой из 60+ квартир «Доброго дома» вас ждёт домашний уют со стандартами хорошего отеля.'}

⭐️ Посмотреть фото и честные отзывы по каждому адресу можно на <a href="https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4">Авито</a> или в каталоге <a href="https://max.ru/id660300569233_biz">Макс</a>."""

    elif category_id == "service_lifehack":
        title = topic or "Бесконтактное заселение за 5 минут: как устроен сервис в «Добром доме» 🗝"
        body = f"""⏱ <b>{title}</b>

Приехали в Тюмень глубокой ночью или после долгой дороги? Вам не нужно никого ждать или подстраиваться под график администратора!

В сети апартаментов <b>«Добрый дом»</b> всё работает быстро, прозрачно и безопасно:

1. Выбираете квартиру на <a href="https://добрыйдом-72.рф/">сайте</a> или через <a href="https://t.me/Dobriy_dom_Tyumen">менеджера</a>.
2. Получаете простую и понятную инструкцию по заселению.
3. Заезжаете в любое время суток 24/7 без ожидания!

🧼 <b>В каждой квартире подготовлено всё:</b>
✅ Свежее постельное бельё и полотенца отельного качества
✅ Одноразовые гигиенические наборы (зубная щетка, паста, шампунь, гель)
✅ Скоростной Wi-Fi, стиральная машина, утюг, фен и чай
✅ Отчетные документы с чеком и QR-кодом для командировочных

Мы на связи в нашем канале <a href="https://t.me/Dobriy_dom_72">@Dobriy_dom_72</a> и в <a href="https://vk.com/dobryi_dom_tyumen">группе ВК</a>!"""

    else:
        title = topic or "Спецпредложения и скидки на проживание в Тюмени 🎁"
        body = f"""🔥 <b>{title}</b>

Останавливаться в лучших апартаментах Тюмени можно не только с комфортом, но и с приятной выгодой!

💰 <b>Тариф «Раннее бронирование»:</b>
Планируете визит заранее? Бронируйте за 20 дней до заезда и получайте <b>скидку 10%</b>!

✈️ <b>Тариф «Длительное проживание»:</b>
Для гостей, которые останавливаются от 10 ночей — скидка 10% на весь срок проживания + регулярная смена белья и уборка.

Более 60 вариантов квартир под любые задачи — на нашем <a href="https://добрыйдом-72.рф/">официальном сайте</a> и в профиле <a href="https://max.ru/id660300569233_biz">Макс</a>."""

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
