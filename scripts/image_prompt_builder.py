"""
Модуль формирования промптов для генерации изображений через GPT Image 2 (Kie.ai / GRSAI).
Формирует:
1. Точный визуальный промпт под тему поста и категорию.
2. Текст на русском языке (кириллицей) для аккуратного размещения на арте.
3. Указания по интеграции логотипа бренда (Добрый дом) в фирменных зеленых (#2E8B57) и коралловых (#E05244) тонах.
4. Формат 1:1, реалистичный фото-стиль интерьеров Тюмени или городских пейзажей.
"""

import os
from pexels_client import fetch_pexels_idea

def build_image_prompt(category_id: str, topic: str = "", text_on_image: str = "", visual_idea: str = "") -> dict:
    # Заголовок на картинке кириллицей
    if not text_on_image:
        titles_map = {
            "afisha": "Афиша и отдых в Тюмени",
            "district_guide": "Квартиры в лучших ЖК Тюмени",
            "service_lifehack": "Бесконтактный заезд 24/7",
            "special_offers": "Скидки до 10% на проживание",
            "city_guide": "Гид по Тюмени: термы и прогулки",
            "host_story": "С заботой о каждом госте"
        }
        text_on_image = titles_map.get(category_id, "Добрый дом Тюмень")

    pexels_image_url = ""
    # Если идея не передана явно, попробуем обогатить её через Pexels API
    if not visual_idea:
        search_terms = {
            "afisha": "cozy city evening cafe festival lights",
            "district_guide": "modern luxury scandinavian apartment interior living room",
            "service_lifehack": "hotel keys smart lock coffee cup warm morning",
            "special_offers": "bright modern apartment workspace laptop sunny",
            "city_guide": "outdoor hot thermal pool steam forest",
            "host_story": "cozy kitchen breakfast fresh coffee flowers table"
        }
        pexels_data = fetch_pexels_idea(search_terms.get(category_id, "cozy apartment interior"))
        if pexels_data and pexels_data.get("alt"):
            visual_idea = f"Realistic photography scene inspired by real life aesthetic: {pexels_data['alt']}."
            pexels_image_url = pexels_data.get("url", "")

    scene_prompts = {
        "afisha": "Cozy warm morning in a luxury apartment living room in Tyumen, soft sunlight through sheer curtains, steaming cup of herbal tea on a stylish wooden coffee table, background view of Tyumen city embankment. Elegant interior photography.",
        "district_guide": "Modern premium Scandinavian style studio apartment in Tyumen residential complex Novin or Evropeyskiy, floor-to-ceiling windows, king-size bed with crisp white luxury hotel bedding, designer emerald green curtains, warm ambient evening lights.",
        "service_lifehack": "Smart door lock with electronic keypad on modern apartment entrance door in Tyumen, hotel welcome tray with neat keys, fluffy towels, disposable hygiene amenities, cup of coffee, clean minimalistic aesthetic.",
        "special_offers": "Bright stylish studio apartment interior with comfortable sofa and laptop open on clean work desk, warm welcoming atmosphere, bouquet of flowers in a pot, warm sunlight.",
        "city_guide": "Outdoor thermal mineral spring pool with soothing steam in winter or autumn forest in Tyumen, cozy relaxation area with wooden loungers and warm blankets.",
        "host_story": "Warm, welcoming, sunlit dining area and kitchen of a premium Tyumen apartment, a cup of fresh morning coffee and a vase with small flowers on a wooden table, genuine home warmth and impeccable hotel cleanliness. Professional atmospheric photography."
    }

    base_scene = visual_idea or scene_prompts.get(category_id, scene_prompts["afisha"])

    full_prompt = (
        f"Commercial social media post banner, square 1:1 format. "
        f"Photo scene: {base_scene}. "
        f"Atmosphere & Setting: authentic cozy Scandinavian apartment interior in Tyumen, soft warm natural sunlight, genuine comfortable living space, wooden furniture, fresh flowers in a ceramic vase, crisp white bedding. Strictly low-rise green neighborhood outside or cozy room focus, absolutely no skyscrapers, no high-rise towers, no American or Moscow metropolis skyline in the window. "
        f"Typography: In the upper area, place a prominent, stylish Russian Cyrillic heading in crisp, uniform white modern bold sans-serif font: {text_on_image.upper()}. "
        f"Branding: Seamlessly place the exact brand logo badge from the first input reference image on a neat white card in the top right corner. The logo shows an emerald green curtain window icon with a red flower in pot, and exact lettering Добрый дом in muted terracotta red serif font. "
        f"Photorealistic 4k interior photography, 35mm lens, natural soft warm lighting, zero AI blur."
    )

    return {
        "prompt": full_prompt,
        "text_on_image": text_on_image,
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "pexels_reference_url": pexels_image_url
    }
