"""
Три текстовых варианта поста на одну тему и одно изображение.
Композитор craft: сцена, аудитория, proof, контраст, save-worthy, ротирующий CTA.
"""

from telegram_post_composer import compose_variant, enrich_topic_data, load_craft_memory


def build_text_variants(topic_data: dict) -> list[dict]:
    """
    Возвращает ровно 3 варианта: [{number, label, text_html, craft_meta}, ...].
    """
    preset = topic_data.get("body_variants") or []
    if len(preset) >= 3:
        labels = topic_data.get("variant_labels") or [
            "История",
            "Чек-лист",
            "Диалог",
        ]
        return [
            {
                "number": i + 1,
                "label": labels[i] if i < len(labels) else f"Вариант {i + 1}",
                "text_html": preset[i],
                "craft_meta": {},
            }
            for i in range(3)
        ]

    category_id = topic_data.get("category_id", "host_story")
    memory = load_craft_memory()
    enriched = enrich_topic_data(topic_data, category_id)

    specs = [
        (1, "История", "narrative"),
        (2, "Чек-лист", "save_guide"),
        (3, "Диалог", "dialogue"),
    ]
    variants = []
    for number, label, _style in specs:
        text_html, craft_meta = compose_variant(enriched, category_id, variant=number, memory=memory)
        variants.append({
            "number": number,
            "label": label,
            "text_html": text_html,
            "craft_meta": craft_meta,
        })
    return variants
