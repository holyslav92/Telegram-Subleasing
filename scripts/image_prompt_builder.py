"""
Модуль формирования промптов для генерации изображений через GPT Image 2 (Kie.ai / GRSAI).
Формирует:
1. Точный визуальный промпт под тему поста и категорию.
2. Текст на русском языке (кириллицей) для аккуратного размещения на арте.
3. Указания по интеграции логотипа бренда (Добрый дом) в фирменных зеленых (#2E8B57) и коралловых (#E05244) тонах.
4. Формат 1:1, реалистичный фото-стиль интерьеров Тюмени или городских пейзажей.
"""

import os
import urllib.request
import urllib.parse
import json

def fetch_pexels_reference_idea(query: str = "apartment interior cozy modern") -> str:
    """
    Запрашивает Pexels API для получения реальных деталей композиции, света и интерьера,
    чтобы обогатить визуальный промпт для GPT Image 2 естественными фотореалистичными деталями.
    """
    api_key = os.environ.get("PEXELS_API_KEY", "").strip()
    if not api_key:
        return ""
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.pexels.com/v1/search?query={encoded_query}&per_page=3&orientation=square"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": api_key,
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            photos = data.get("photos", [])
            for p in photos:
                alt = p.get("alt", "").strip()
                if alt and len(alt) > 15:
                    return alt
    except Exception as e:
        print(f"Pexels fetch notice: {e}")
    return ""

def build_image_prompt(category_id: str, topic: str = "", text_on_image: str = "") -> dict:
    # Заголовок на картинке кириллицей
    if not text_on_image:
        titles_map = {
            "afisha": "Афиша и отдых в Тюмени",
            "district_guide": "Квартиры в лучших ЖК Тюмени",
            "host_story": "Уют и забота в деталях",
            "service_lifehack": "Бесконтактный заезд 24/7",
            "special_offers": "Скидки до 10% на проживание",
            "city_guide": "Гид по Тюмени: термы и прогулки"
        }
        text_on_image = titles_map.get(category_id, "Добрый дом Тюмень")

    scene_prompts = {
        "afisha": "Cozy warm morning in a luxury apartment living room in Tyumen, soft sunlight through sheer curtains, steaming cup of herbal tea on a stylish wooden coffee table, background view of Tyumen city embankment. Elegant interior photography.",
        "district_guide": "Modern premium Scandinavian style studio apartment in Tyumen residential complex Novin or Evropeyskiy, floor-to-ceiling windows, king-size bed with crisp white luxury hotel bedding, designer emerald green curtains, warm ambient evening lights.",
        "host_story": "Warm inviting Scandinavian apartment interior in Tyumen, comfortable reading armchair with a cozy woolen plaid, warm table lamp, open book, cup of tea with sweets, clean light background, home comfort.",
        "service_lifehack": "Smart door lock with electronic keypad on modern apartment entrance door in Tyumen, hotel welcome tray with neat keys, fluffy towels, disposable hygiene amenities, cup of coffee, clean minimalistic aesthetic.",
        "special_offers": "Bright stylish studio apartment interior with comfortable sofa and laptop open on clean work desk, warm welcoming atmosphere, bouquet of flowers in a pot, warm sunlight.",
        "city_guide": "Outdoor thermal mineral spring pool with soothing steam in winter or autumn forest in Tyumen, cozy relaxation area with wooden loungers and warm blankets."
    }

    base_scene = scene_prompts.get(category_id, scene_prompts["afisha"])

    # Обогащение идеи изображения через Pexels API
    pexels_queries = {
        "afisha": "luxury apartment living room cozy morning tea",
        "district_guide": "scandinavian modern studio apartment bedroom interior",
        "host_story": "cozy warm apartment living room reading armchair plaid",
        "service_lifehack": "modern smart hotel room doorway clean keyless entrance",
        "special_offers": "bright cozy apartment interior work desk sunlit",
        "city_guide": "outdoor hot springs bath steam forest autumn"
    }
    query = pexels_queries.get(category_id, "luxury apartment interior cozy")
    pexels_idea = fetch_pexels_reference_idea(query)
    enrichment = f" Real-life photography reference details: {pexels_idea}." if pexels_idea else ""

    full_prompt = (
        f"{base_scene}{enrichment} "
        f"Design layout for Telegram post, square 1:1 ratio. "
        f"Brand colors: emerald green (#2E8B57) and coral red (#E05244) accents on a clean light cream background. "
        f"Include a stylish brand banner or card with the exact Russian text in elegant, crisp, modern Cyrillic typography: '{text_on_image}'. "
        f"Incorporate the authentic brand logo 'Добрый дом' (featuring the signature emerald green curtain icon with a potted coral-red flower and clear 'Добрый дом' brand lettering) placed with crisp fidelity in the corner or on a neat branding tag, maintaining exact brand geometry and colors without distortion. "
        f"High resolution 4k, professional commercial photography, photorealistic, balanced natural lighting, cinematic composition."
    )

    return {
        "prompt": full_prompt,
        "text_on_image": text_on_image,
        "aspect_ratio": "1:1",
        "resolution": "1K"
    }
