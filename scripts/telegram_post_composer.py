#!/usr/bin/env python3
"""
Композитор постов Telegram: сцена, срочность, аудитория, proof, контраст,
save-worthy блоки и ротирующие CTA — без роботизированных шаблонов.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
CRAFT_FILE = WORKSPACE_ROOT / "shared" / "telegram-content-craft.json"
TOPIC_CRAFT_FILE = WORKSPACE_ROOT / "shared" / "telegram-topic-craft.json"
LESSONS_FILE = WORKSPACE_ROOT / "memory" / "telegram_posts" / "lessons.json"

BANNED_OPENERS = [
    "планируете поездку в тюмень",
    "планируете визит в тюмень",
    "ищете жильё в тюмени",
    "собрали для вас",
    "собрали ключевые идеи",
]

SITE = "https://добрыйдом-72.рф/"
AVITO = "https://www.avito.ru/brands/dobriydomtymen/all?sellerId=5a9944e5fd6eca88b3c4f0864c03f0b4"
MAX = "https://max.ru/id660300569233_biz"
EXCURSIONS = "https://добрыйдом-72.рф/excursions/"
MANAGER = "https://t.me/Dobriy_dom_Tyumen"


def _seed(*parts: str) -> int:
    raw = "|".join(str(p) for p in parts)
    return int(hashlib.md5(raw.encode()).hexdigest()[:8], 16)


def _load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_craft_config() -> dict:
    return _load_json(CRAFT_FILE)


def load_craft_memory() -> dict:
    data = _load_json(LESSONS_FILE)
    return {
        "used_cta_ids": data.get("used_cta_ids") or [],
        "used_scene_ids": data.get("used_scene_ids") or [],
        "used_audience_lines": data.get("used_audience_lines") or [],
        "used_contrast_ids": data.get("used_contrast_ids") or [],
        "used_save_worthy_ids": data.get("used_save_worthy_ids") or [],
        "used_micro_proof_ids": data.get("used_micro_proof_ids") or [],
        "save_worthy_weeks": data.get("save_worthy_weeks") or [],
        "used_urgency_ids": data.get("used_urgency_ids") or [],
    }


def get_topic_craft(topic_id: str, category_id: str, topic_data: dict) -> dict:
    """Метаданные темы: overlay + defaults категории."""
    craft = load_craft_config()
    overlay = (_load_json(TOPIC_CRAFT_FILE).get("topics") or {}).get(topic_id, {})
    cat_defaults = (craft.get("category_defaults") or {}).get(category_id, {})
    merged = {**cat_defaults, **overlay}
    if not merged.get("audience_tag"):
        merged["audience_tag"] = "general"
    if not merged.get("scene_detail") and topic_data.get("title"):
        merged["scene_detail"] = _infer_scene_detail(topic_data)
    if not merged.get("benefit_line"):
        merged["benefit_line"] = _infer_benefit(topic_data, category_id)
    return merged


def _infer_scene_detail(topic_data: dict) -> str:
    core = extract_body_core(topic_data.get("body", ""))
    if core:
        plain = strip_html(core[0])
        if len(plain) > 30:
            return plain[:120].rstrip(".") + ("…" if len(plain) > 120 else "")
    title = re.sub(r"<[^>]+>", "", topic_data.get("title", "")).strip()
    if title:
        # без повтора заголовка целиком
        if ":" in title:
            return title.split(":", 1)[1].strip().lower()
        return title.lower()
    return "в поездке мелочи решают больше, чем кажется"


def _infer_benefit(topic_data: dict, category_id: str) -> str:
    defaults = {
        "afisha": "после события — тихая квартира с <b>бесконтактным заездом 24/7</b>",
        "district_guide": "квартира в нужном районе — без суеты при заезде",
        "host_story": "забота в деталях — не лозунг, а стандарт перед каждым заездом",
        "service_standards": "отельная чистота и документы для командировочных — без сюрпризов",
        "weekend_thermal": "термы + уютная квартира рядом — выходные без спешки",
        "special_offers": "<b>прямые цены</b> на сайте — без комиссий агрегаторов",
        "siberian_hospitality": "сибирское гостеприимство — в чайнике, белье и тишине",
    }
    return defaults.get(category_id, "<b>бесконтактный заезд 24/7</b> и отельный уют")


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text or "")).strip()


def _is_cta_paragraph(p: str) -> bool:
    low = p.lower()
    return any(x in low for x in ("добрыйдом-72", "avito.ru", "max.ru", "брониру", "отзывы гостей"))


def extract_body_core(body: str) -> list[str]:
    """Вырезает заголовок и CTA — оставляет смысловые абзацы."""
    parts = [p.strip() for p in re.split(r"\n\s*\n", body.strip()) if p.strip()]
    if not parts:
        return []
    if parts[0].startswith("<b>"):
        parts = parts[1:]
    core = [p for p in parts if not _is_cta_paragraph(p)]
    cleaned = []
    for p in core:
        plain = strip_html(p).lower()
        if any(b in plain for b in BANNED_OPENERS):
            continue
        cleaned.append(p)
    return cleaned[:4]


def _pick_from_pool(pool: list, used_ids: list, seed_key: str, id_field: str = "id") -> dict | str | None:
    if not pool:
        return None
    used = set(used_ids)
    start = _seed(seed_key) % len(pool)
    for offset in range(len(pool)):
        item = pool[(start + offset) % len(pool)]
        item_id = item[id_field] if isinstance(item, dict) else item
        if item_id not in used:
            return item
    return pool[start % len(pool)]


def _pick_cta(category_id: str, topic_id: str, variant: int, memory: dict, craft: dict) -> tuple[str, str]:
    cfg = load_craft_config()
    pool_ids = craft.get("cta_pool") or (cfg.get("category_defaults", {}).get(category_id, {}) or {}).get("cta_pool") or []
    all_ctas = {c["id"]: c for c in cfg.get("cta_endings", [])}
    pool = [all_ctas[cid] for cid in pool_ids if cid in all_ctas]
    if not pool:
        pool = cfg.get("cta_endings", [])
    picked = _pick_from_pool(pool, memory.get("used_cta_ids", []), f"{topic_id}:cta:{variant}")
    if not picked:
        picked = pool[0]
    return picked["html"], picked["id"]


def _compose_scene(topic_craft: dict, topic_data: dict, variant: int, memory: dict) -> tuple[str, str]:
    cfg = load_craft_config()
    detail = topic_craft.get("scene_detail") or _infer_scene_detail(topic_data)
    feeling = topic_craft.get("scene_feeling") or "выдохнуть и почувствовать, что вас ждут"
    custom = topic_craft.get("scene_seeds") or []
    if custom:
        idx = _seed(topic_data.get("id", ""), "scene", variant) % len(custom)
        return custom[idx], f"custom_scene_{idx}"

    styles = cfg.get("scene_styles", [])
    picked = _pick_from_pool(styles, memory.get("used_scene_ids", []), f"{topic_data.get('id')}:scene:{variant}")
    if not picked:
        return f"Короткая сцена из поездки: {detail}.", "fallback_scene"
    text = picked["template"].format(detail=detail, feeling=feeling, pain=topic_craft.get("pain", "опоздали и устали"))
    return text, picked["id"]


def _compose_urgency(topic_data: dict, topic_craft: dict, memory: dict) -> tuple[str | None, str | None]:
    if topic_craft.get("urgency_skip"):
        return None, None
    custom = topic_craft.get("urgency")
    if custom:
        return custom, "topic_urgency"
    event_date = topic_data.get("event_date") or ""
    cfg = load_craft_config()
    pool = cfg.get("urgency_phrases", [])
    if event_date:
        try:
            ev = datetime.strptime(event_date[:10], "%Y-%m-%d")
            if ev.date() >= datetime.now().date():
                return f"Событие {ev.strftime('%d.%m')} — если даты совпадают с вашей поездкой, лучше забронировать жильё заранее.", "urgency_event_date"
        except ValueError:
            pass
    if not topic_data.get("evergreen", True):
        picked = _pick_from_pool(pool, memory.get("used_urgency_ids", []), topic_data.get("id", ""))
        if picked:
            return picked["template"], picked["id"]
    # evergreen: urgency реже (~40%)
    if _seed(topic_data.get("id", ""), "urgency") % 5 >= 2:
        return None, None
    picked = _pick_from_pool(pool, memory.get("used_urgency_ids", []), f"{topic_data.get('id')}:urg")
    if picked:
        return picked["template"], picked["id"]
    return None, None


def _compose_audience(audience_tag: str, topic_id: str, variant: int, memory: dict) -> tuple[str | None, str | None]:
    cfg = load_craft_config()
    lines = (cfg.get("audience_lines") or {}).get(audience_tag) or (cfg.get("audience_lines") or {}).get("general", [])
    if not lines:
        return None, None
    # не в каждом посте — вариант 2 чаще, вариант 1 ~50%
    if variant == 1 and _seed(topic_id, "aud") % 2 == 0:
        return None, None
    used = memory.get("used_audience_lines", [])
    start = _seed(topic_id, audience_tag, variant) % len(lines)
    for offset in range(len(lines)):
        line = lines[(start + offset) % len(lines)]
        if line not in used:
            return line, f"{audience_tag}_{hash(line) % 10000}"
    return lines[start], f"{audience_tag}_repeat"


def _compose_micro_proof(topic_craft: dict, topic_id: str, variant: int, memory: dict) -> tuple[str | None, str | None]:
    cfg = load_craft_config()
    if topic_craft.get("micro_proof"):
        return topic_craft["micro_proof"], "topic_proof"
    # proof не всегда: ~60% постов
    if _seed(topic_id, "proof", variant) % 5 == 0:
        return None, None
    pool = cfg.get("micro_proofs", [])
    picked = _pick_from_pool(pool, memory.get("used_micro_proof_ids", []), f"{topic_id}:proof:{variant}")
    if picked:
        return picked["text"], picked["id"]
    return None, None


def _compose_contrast(topic_craft: dict, topic_id: str, variant: int, memory: dict) -> tuple[str | None, str | None]:
    if not topic_craft.get("contrast_ok"):
        return None, None
    if topic_craft.get("contrast_skip"):
        return None, None
    # контраст только ~35% и не в save-варианте каждый раз
    if variant == 2:
        return None, None
    if _seed(topic_id, "contrast") % 3 != 0:
        return None, None
    cfg = load_craft_config()
    specific = topic_craft.get("contrast_specific") or topic_craft.get("benefit_line", "")
    if topic_craft.get("contrast_before") and topic_craft.get("contrast_after"):
        text = f"{topic_craft['contrast_before']} {topic_craft['contrast_after']}"
        return text, "topic_contrast"
    templates = cfg.get("contrast_templates", [])
    picked = _pick_from_pool(templates, memory.get("used_contrast_ids", []), f"{topic_id}:contrast")
    if not picked:
        return None, None
    text = f"{picked['before']} {picked['after'].format(specific=specific)}"
    return text, picked["id"]


def _iso_week() -> str:
    return datetime.now().strftime("%G-W%V")


def _compose_save_block(category_id: str, topic_id: str, topic_craft: dict, memory: dict, variant: int) -> tuple[str | None, str | None]:
    # save-worthy — в основном вариант 2 (чек-лист)
    if variant != 2 and not topic_craft.get("save_worthy"):
        return None, None
    cfg = load_craft_config()
    week = _iso_week()
    force = topic_craft.get("save_worthy")
    if not force and week in memory.get("save_worthy_weeks", []):
        return None, None
    if not force and _seed(category_id, week) % 7 != 0:
        return None, None
    pool_ids = topic_craft.get("save_worthy_pool") or []
    blocks = {b["id"]: b for b in cfg.get("save_worthy_blocks", [])}
    pool = [blocks[bid] for bid in pool_ids if bid in blocks]
    if not pool:
        pool = cfg.get("save_worthy_blocks", [])
    picked = _pick_from_pool(pool, memory.get("used_save_worthy_ids", []), f"{topic_id}:save")
    if not picked:
        return None, None
    items = "\n".join(f"{i + 1}️⃣ {item}" for i, item in enumerate(picked.get("items", [])))
    text = f"<b>{picked['title']}</b>\n{items}"
    return text, picked["id"]


def _dedupe_paragraphs(parts: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        key = strip_html(p).lower()[:120]
        if not key or key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _too_similar(a: str, b: str, threshold: float = 0.72) -> bool:
    from telegram_similarity import similarity_score
    return similarity_score(a, b) >= threshold


def compose_variant(
    topic_data: dict,
    category_id: str,
    variant: int = 1,
    memory: dict | None = None,
) -> tuple[str, dict]:
    """
    variant 1 — narrative (сцена → суть → benefit → proof? → CTA)
    variant 2 — save/guide (аудитория → чек-лист или список → мягкий CTA)
    variant 3 — dialogue (вопрос → контраст? → proof → insight → другой CTA)
    """
    memory = memory or load_craft_memory()
    craft_cfg = load_craft_config()
    topic_id = topic_data.get("id", "")
    title = topic_data.get("title", "")
    topic_craft = get_topic_craft(topic_id, category_id, topic_data)
    core_paragraphs = topic_craft.get("insight_paragraphs") or extract_body_core(topic_data.get("body", ""))
    if not core_paragraphs and topic_data.get("body"):
        core_paragraphs = extract_body_core(topic_data.get("body", ""))

    title_html = f"<b>{title}</b>" if title else ""
    craft_meta: dict = {"variant": variant, "topic_id": topic_id}

    scene, scene_id = _compose_scene(topic_craft, topic_data, variant, memory)
    craft_meta["scene_id"] = scene_id

    urgency, urgency_id = _compose_urgency(topic_data, topic_craft, memory)
    if urgency_id:
        craft_meta["urgency_id"] = urgency_id

    audience, aud_id = _compose_audience(topic_craft.get("audience_tag", "general"), topic_id, variant, memory)
    if aud_id:
        craft_meta["audience_id"] = aud_id

    proof, proof_id = _compose_micro_proof(topic_craft, topic_id, variant, memory)
    if proof_id:
        craft_meta["micro_proof_id"] = proof_id

    contrast, contrast_id = _compose_contrast(topic_craft, topic_id, variant, memory)
    if contrast_id:
        craft_meta["contrast_id"] = contrast_id
        craft_meta["contrast_used"] = True

    save_block, save_id = _compose_save_block(category_id, topic_id, topic_craft, memory, variant)
    if save_id:
        craft_meta["save_worthy_id"] = save_id

    cta_html, cta_id = _pick_cta(category_id, topic_id, variant, memory, topic_craft)
    craft_meta["cta_id"] = cta_id

    benefit = topic_craft.get("benefit_line", "")

    parts: list[str] = []

    if variant == 1:
        # narrative: заголовок после сцены или сцена первой
        if _seed(topic_id, "v1order") % 2 == 0:
            block = [scene, title_html]
        else:
            block = [title_html, scene]
        if core_paragraphs and _too_similar(scene, core_paragraphs[0]):
            block = [title_html] + core_paragraphs[:1]
        parts.extend(block)
        if urgency:
            parts.append(urgency)
        if audience:
            parts.append(audience)
        parts.extend(core_paragraphs[1:3] if _too_similar(scene, core_paragraphs[0]) else core_paragraphs[:2])
        if benefit and _seed(topic_id, "ben") % 3 != 0:
            parts.append(f"Для нас это не мелочь: {benefit}.")
        if proof:
            parts.append(proof)
        if contrast:
            parts.append(contrast)
        parts.append(cta_html)

    elif variant == 2:
        parts.append(title_html)
        if audience:
            parts.append(audience)
        if save_block:
            parts.append(save_block)
            if core_paragraphs:
                parts.append(core_paragraphs[0])
        else:
            bullets = core_paragraphs[:3]
            if bullets:
                numbered = "\n".join(f"{i + 1}️⃣ {strip_html(b)[:160]}" for i, b in enumerate(bullets))
                parts.append(numbered)
        if proof:
            parts.append(proof)
        if urgency:
            parts.append(urgency)
        parts.append(cta_html)

    else:
        # variant 3 — диалог / proof-first (без дубля сцены)
        if core_paragraphs:
            opener = strip_html(core_paragraphs[0])
            if not opener.endswith("?"):
                opener = opener.rstrip(".") + " — знакомо?"
            parts.append(f"<b>{opener}</b>" if len(opener) < 120 else opener)
        else:
            parts.append(scene if "?" in scene else f"{scene.rstrip('.')} — знакомо?")
        if contrast:
            parts.append(contrast)
        elif len(core_paragraphs) > 1:
            parts.append(core_paragraphs[1])
        if proof:
            parts.append(proof)
        if len(core_paragraphs) > 2:
            parts.append(core_paragraphs[2])
        elif benefit and not contrast:
            parts.append(benefit + ".")
        parts.append(cta_html)

    text_html = "\n\n".join(p for p in _dedupe_paragraphs(parts) if p and p.strip())
    craft_meta["audience_tag"] = topic_craft.get("audience_tag", "general")
    return text_html, craft_meta


def compose_topic_body(topic_data: dict, category_id: str) -> tuple[str, dict]:
    """Основной текст поста (вариант 1) для build_post."""
    return compose_variant(topic_data, category_id, variant=1)


def enrich_topic_data(topic_data: dict, category_id: str) -> dict:
    """Добавляет composed body и craft_meta в topic_data."""
    body, craft_meta = compose_topic_body(topic_data, category_id)
    enriched = {**topic_data, "category_id": category_id, "body": body, "craft_meta": craft_meta}
    return enriched
