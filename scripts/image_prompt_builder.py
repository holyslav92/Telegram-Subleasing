"""
Модуль формирования промптов для генерации изображений через GPT Image 2 (GRSAI).
Формирует:
1. Точный визуальный промпт под тему поста и категорию.
2. Текст на русском языке (кириллицей) для аккуратного размещения на арте.
3. Указания по интеграции логотипа бренда (Добрый дом) в фирменных зеленых (#2E8B57) и коралловых (#E05244) тонах.
4. Формат 1:1, реалистичный фото-стиль интерьеров Тюмени или аутентичных городских пейзажей (без небоскребов).
"""

import os
from pexels_client import fetch_pexels_idea

def build_image_prompt(category_id: str, topic: str = "", text_on_image: str = "", visual_idea: str = "") -> dict:
    # Заголовок на картинке кириллицей под каждую из рубрик недели
    if not text_on_image:
        titles_map = {
            "afisha": "Афиша и события Тюмени",
            "district_guide": "Квартиры в лучших ЖК Тюмени",
            "host_story": "Уют в каждой детали",
            "service_standards": "Отельный стандарт чистоты",
            "service_lifehack": "Отельный стандарт чистоты",
            "weekend_thermal": "Термальная столица России",
            "city_guide": "Термальная столица России",
            "special_offers": "Скидки до 10% на проживание",
            "siberian_hospitality": "Сибирское гостеприимство"
        }
        text_on_image = titles_map.get(category_id, "Добрый дом Тюмень")

    pexels_image_url = ""
    # Если идея не передана явно, подбираем поисковый запрос для Pexels API
    if not visual_idea:
        search_terms = {
            "afisha": "city evening concert theater celebration warm lights",
            "district_guide": "modern luxury scandinavian apartment interior living room",
            "host_story": "steaming herbal tea cup wooden table morning sunlight bedroom",
            "service_standards": "clean luxury hotel bathroom fluffy white towels amenities",
            "service_lifehack": "clean luxury hotel bathroom fluffy white towels amenities",
            "weekend_thermal": "outdoor steaming hot mineral spring forest spa resort",
            "city_guide": "outdoor steaming hot mineral spring forest spa resort",
            "special_offers": "bright modern apartment sunny cozy comfortable sofa",
            "siberian_hospitality": "cozy warm scandinavian living room armchair lamp book blanket"
        }
        pexels_data = fetch_pexels_idea(search_terms.get(category_id, "cozy apartment interior"))
        if pexels_data and pexels_data.get("alt"):
            visual_idea = f"Realistic photography scene inspired by real life aesthetic: {pexels_data['alt']}."
            pexels_image_url = pexels_data.get("url", "")

    scene_prompts = {
        "afisha": "Atmospheric evening culture in Tyumen, soft warm lighting, grand theater foyer or concert hall ambiance with gentle golden glow, elegant city atmosphere. Authentic editorial photography.",
        "district_guide": "Modern premium Scandinavian style studio apartment in Tyumen residential complex Novin or Evropeyskiy, floor-to-ceiling windows, king-size bed with crisp white luxury hotel bedding, designer emerald green curtains, warm ambient evening lights.",
        "host_story": "Warm, welcoming, sunlit dining area and kitchen of a premium Tyumen apartment, a steaming cup of fresh morning tea and a vase with small delicate flowers on a wooden table, genuine home warmth and immaculate hotel cleanliness.",
        "service_standards": "Immaculately clean hotel-standard bathroom in modern apartment, neatly rolled fluffy white cotton towels, branded toiletries and amenities tray, sparkling mirror and polished fixtures, soothing spa atmosphere.",
        "service_lifehack": "Immaculately clean hotel-standard bathroom in modern apartment, neatly rolled fluffy white cotton towels, branded toiletries, sparkling cleanliness.",
        "weekend_thermal": "Outdoor natural thermal mineral spring pool with soothing steam in snowy pine forest in Tyumen, cozy wooden deck with warm ambient lanterns.",
        "city_guide": "Outdoor natural thermal mineral spring pool with soothing steam in pine forest in Tyumen, cozy wooden relaxation terrace.",
        "special_offers": "Bright stylish studio apartment interior with comfortable sofa and laptop open on clean work desk, warm welcoming atmosphere, bouquet of flowers in a pot, warm sunlight.",
        "siberian_hospitality": "Tranquil cozy Sunday morning in a warm Scandinavian apartment bedroom in Tyumen, soft morning sunlight casting gentle shadows on crisp white cotton sheets, cup of coffee on bedside nightstand, calm and peaceful mood."
    }

    base_scene = visual_idea or scene_prompts.get(category_id, scene_prompts["afisha"])

    # Если тема про термальные источники, формируем уличную сцену термального курорта
    if category_id in ["weekend_thermal", "city_guide"]:
        full_prompt = (
            f"Social media promotional poster, square 1:1 aspect ratio. "
            f"Subject: {base_scene}. "
            f"Atmosphere: Authentic Siberian outdoor thermal hot spring mineral pool in Tyumen surrounded by peaceful coniferous pine trees, soothing rising mist and steam over warm mineral water, wooden lounge terrace, ambient warm lanterns, crisp clean air, absolutely no high-rise buildings or skyscrapers. "
            f"Headline: In the upper area, place a prominent, stylish Russian Cyrillic heading in crisp, uniform white modern bold sans-serif font: {text_on_image.upper()}. "
            f"Brand Logo Placement: Place the official brand logo from reference image url 1 directly onto a clean white rectangular badge with rounded corners in the top right corner. The logo must keep its exact green curtains window icon, small red potted flower, and Добрый дом brand lettering intact with crisp professional clarity. "
            f"Photorealistic 4k photography, 35mm lens, natural soft warm lighting."
        )
    else:
        full_prompt = (
            f"Social media promotional poster, square 1:1 aspect ratio. "
            f"Subject: {base_scene}. "
            f"Interior details: authentic cozy Scandinavian apartment in Tyumen, soft morning sunlight, comfortable authentic living space, wooden furniture, vase with delicate white flowers, crisp hotel bed linens. Solid wall and cozy warm room ambiance, strictly low-rise green neighborhood outside, absolutely no skyscrapers, no high-rise glass towers in any window. "
            f"Headline: In the upper area, place a prominent, stylish Russian Cyrillic heading in crisp, uniform white modern bold sans-serif font: {text_on_image.upper()}. "
            f"Brand Logo Placement: Place the official brand logo from reference image url 1 directly onto a clean white rectangular badge with rounded corners in the top right corner. The logo must keep its exact green curtains window icon, small red potted flower, and Добрый дом brand lettering intact with crisp professional clarity. "
            f"Photorealistic 4k interior photography, 35mm lens, natural soft warm lighting."
        )

    return {
        "prompt": full_prompt,
        "text_on_image": text_on_image,
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "pexels_reference_url": pexels_image_url
    }
