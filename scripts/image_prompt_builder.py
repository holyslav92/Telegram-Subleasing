"""
Модуль формирования промптов для генерации изображений через GPT Image 2 (GRSAI).
Формирует стильный editorial-постер 1:1 с кириллическим заголовком и точным логотипом из референса.
"""

import os
from pexels_client import fetch_pexels_idea

# Жёсткое правило: логотип только копируется с reference image 1, без перерисовки
LOGO_COMPOSITE_RULE = (
    "LOGO RULE (CRITICAL, HIGHEST PRIORITY): Reference image 1 is the official brand logo asset. "
    "You MUST composite/copy this exact logo file onto the poster as-is — pixel-accurate, unchanged colors, "
    "unchanged shapes and Cyrillic lettering. DO NOT redraw, illustrate, recreate, stylize, simplify, or "
    "reinterpret the logo. DO NOT invent a new icon or wordmark. Scale proportionally only; no warp, skew, "
    "stretch, blur, or painterly treatment. Place in upper-right with comfortable margin; optional subtle "
    "soft drop shadow for legibility is allowed. The logo must look like a pasted PNG asset, not AI-generated art."
)

DESIGN_STYLE = (
    "Premium editorial social poster design: cinematic color grading, layered depth, subtle vignette, "
    "refined magazine layout, tasteful geometric accents, rich but natural lighting, high-end travel-brand aesthetic. "
    "Avoid flat stock-photo look; aim for polished art-directed campaign quality."
)

HEADLINE_STYLE = (
    "Headline typography: bold designer Cyrillic title in crisp white, modern editorial sans-serif, "
    "elegant letter-spacing, subtle soft shadow or gentle gradient mask for perfect legibility over the scene."
)


def build_image_prompt(
    category_id: str,
    topic: str = "",
    text_on_image: str = "",
    visual_idea: str = "",
    topic_id: str = "",
    scene_override: str = "",
) -> dict:
    if not text_on_image:
        titles_map = {
            "afisha": "Афиша и события Тюмени",
            "district_guide": "Квартиры в лучших ЖК Тюмени",
            "host_story": "Уют в каждой детали",
            "service_standards": "Отельный стандарт чистоты",
            "service_lifehack": "Отельный стандарт чистоты",
            "weekend_thermal": "Планы на выходные в Тюмени",
            "city_guide": "Планы на выходные в Тюмени",
            "special_offers": "Скидки до 10% на проживание",
            "siberian_hospitality": "Сибирское гостеприимство",
        }
        text_on_image = titles_map.get(category_id, "Добрый дом Тюмень")

    pexels_image_url = ""
    if not visual_idea:
        search_terms = {
            "afisha": "city evening concert theater celebration warm lights",
            "district_guide": "modern luxury scandinavian apartment interior living room",
            "host_story": "steaming herbal tea cup wooden table morning sunlight bedroom",
            "service_standards": "clean luxury hotel bathroom fluffy white towels amenities",
            "service_lifehack": "clean luxury hotel bathroom fluffy white towels amenities",
            "weekend_thermal": "historic wooden architecture pedestrian street evening warm lights",
            "city_guide": "historic wooden architecture pedestrian street evening warm lights",
            "special_offers": "bright modern apartment sunny cozy comfortable sofa",
            "siberian_hospitality": "cozy warm scandinavian living room armchair lamp book blanket",
        }
        pexels_data = fetch_pexels_idea(search_terms.get(category_id, "cozy apartment interior"))
        if pexels_data and pexels_data.get("alt"):
            visual_idea = f"Realistic photography scene inspired by real life aesthetic: {pexels_data['alt']}."
            pexels_image_url = pexels_data.get("url", "")

    scene_by_topic = {
        "city_thermal_pools": (
            "Modern open-air thermal mineral resort in Tyumen, Russia (LetoLeto / Verkhniy Bor style): "
            "large outdoor pool with clean steaming water, Siberian pine forest, wooden decks, warm evening lanterns. "
            "No volcanic craters, no geysers, no skyscrapers."
        ),
        "city_dzerzhinskogo_excursions": (
            "Atmospheric historic pedestrian street in Tyumen: ornate wooden merchant houses with carved facades, "
            "warm golden evening light, cobblestone walkway, cozy lanterns, authentic Siberian old-town charm. "
            "Low-rise historic architecture only, no skyscrapers, no generic European old town."
        ),
        "weekend_siberian_gastronomy": (
            "Elegant cozy Siberian restaurant table: beautifully plated local dishes, warm candlelight, "
            "wooden interior, wine glasses, intimate gastronomic weekend mood."
        ),
        "weekend_embankment_walk": (
            "Tyumen four-level embankment of Tura river at blue hour: layered walkways, bridge lights, "
            "reflections on water, romantic city stroll atmosphere, low-rise skyline."
        ),
        "weekend_letoleto_spa": (
            "Luxury spa relaxation zone after thermal bathing: soft towels, warm ambient light, "
            "calm wellness interior with hints of pine forest outside the windows."
        ),
    }

    scene_prompts = {
        "afisha": "Atmospheric evening culture in Tyumen, soft warm lighting, grand theater foyer or concert hall ambiance.",
        "district_guide": "Modern premium Scandinavian studio in Tyumen residential complex, floor-to-ceiling windows, designer emerald curtains, warm evening light.",
        "host_story": "Warm sunlit dining area, steaming morning tea, wooden table, genuine home warmth and hotel cleanliness.",
        "service_standards": "Immaculately clean hotel-standard bathroom, fluffy white towels, branded amenities, sparkling fixtures.",
        "service_lifehack": "Immaculately clean hotel-standard bathroom, fluffy white towels, sparkling cleanliness.",
        "weekend_thermal": scene_by_topic.get(topic_id, scene_by_topic["city_dzerzhinskogo_excursions"]),
        "city_guide": scene_by_topic.get(topic_id, scene_by_topic["city_dzerzhinskogo_excursions"]),
        "special_offers": "Bright stylish studio interior, comfortable sofa, warm sunlight, welcoming atmosphere.",
        "siberian_hospitality": "Tranquil cozy Sunday morning in Scandinavian apartment, soft sunlight on white linens, calm mood.",
    }

    base_scene = scene_override or visual_idea or scene_prompts.get(category_id, scene_prompts["afisha"])

    headline_prompt = (
        f"{HEADLINE_STYLE} Text: {text_on_image.upper()}."
    )

    if category_id in ("weekend_thermal", "city_guide"):
        subject = scene_by_topic.get(topic_id) or base_scene
        full_prompt = (
            f"Square 1:1 premium travel editorial poster for a Russian apartment brand in Tyumen. "
            f"{DESIGN_STYLE} "
            f"Scene: {subject} "
            f"Reference image 2 may inspire mood, lighting and composition only — not the logo. "
            f"{headline_prompt} "
            f"{LOGO_COMPOSITE_RULE} "
            f"Photorealistic 4K, 35mm lens, natural cinematic lighting, no text other than the headline and logo."
        )
    else:
        full_prompt = (
            f"Square 1:1 premium interior editorial poster for a Russian apartment brand in Tyumen. "
            f"{DESIGN_STYLE} "
            f"Subject: {base_scene} "
            f"Authentic cozy Scandinavian apartment in Tyumen, low-rise neighborhood outside windows, absolutely no skyscrapers. "
            f"Reference image 2 may inspire mood and composition only — not the logo. "
            f"{headline_prompt} "
            f"{LOGO_COMPOSITE_RULE} "
            f"Photorealistic 4K interior photography, 35mm lens, natural soft warm lighting."
        )

    return {
        "prompt": full_prompt,
        "text_on_image": text_on_image,
        "aspect_ratio": "1:1",
        "resolution": "1K",
        "pexels_reference_url": pexels_image_url,
    }
