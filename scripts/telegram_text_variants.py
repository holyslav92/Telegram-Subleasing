"""
Три текстовых варианта поста на одну тему и одно изображение.
Каждый вариант — другая структура и заход, не обрезка одного текста.
"""

import hashlib
import json
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
LESSONS_FILE = WORKSPACE_ROOT / "memory" / "telegram_posts" / "lessons.json"

# Разные заходы по рубрикам (не шаблон «Ищете жильё…»)
CATEGORY_HOOKS = {
    "host_story": [
        "Представьте: вы только что переступили порог после долгой дороги.",
        "Мы в команде «Доброго дома» часто спрашиваем себя: что делает квартиру «домом», а не номером?",
        "Из нашей практики — одна деталь, которая меняет настроение гостя с первых минут.",
    ],
    "afisha": [
        "Вечер в Тюмени может быть тихим — или запомниться на годы. Вот один повод выйти из квартиры.",
        "Если даты поездки уже известны — имеет смысл заранее присмотреть, куда сходить в городе.",
    ],
    "district_guide": [
        "Выбор района в поездке — это не только адрес на карте, но и ритм ваших дней.",
    ],
    "service_standards": [
        "Мелочи, которые кажутся «само собой разумеющимися», — и есть наш стандарт.",
    ],
    "weekend_thermal": [
        "Выходные в Тюмени — это не только термальные комплексы, но и прогулки рядом с водой.",
    ],
    "special_offers": [
        "Иногда выгоднее бронировать заранее — и мы честно говорим об этом без «скидочного шума».",
    ],
    "siberian_hospitality": [
        "Сибирское гостеприимство — не лозунг, а конкретные вещи в квартире и на кухне.",
    ],
}


def _split_paragraphs(html: str) -> list[str]:
    parts = [p.strip() for p in re.split(r"\n\s*\n", html.strip()) if p.strip()]
    return parts


def _join_paragraphs(parts: list[str]) -> str:
    return "\n\n".join(parts)


def _strip_bold_title(html: str) -> tuple[str, str]:
    m = re.match(r"(<b>.*?</b>\s*)", html, flags=re.S)
    if m:
        return m.group(1).strip(), html[m.end() :].strip()
    return "", html.strip()


def _cta_paragraph(parts: list[str]) -> str:
    for p in reversed(parts):
        if "добрыйдом-72" in p.lower() or "avito.ru" in p.lower():
            return p
    return parts[-1] if parts else ""


def _load_used_hooks() -> list[str]:
    if not LESSONS_FILE.exists():
        return []
    try:
        with open(LESSONS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("used_opening_hooks") or []
    except Exception:
        return []


def _pick_hook(category_id: str, topic_id: str) -> str:
    """Выбирает hook, который ещё не использовали."""
    pool = CATEGORY_HOOKS.get(category_id, CATEGORY_HOOKS.get("host_story", []))
    if not pool:
        pool = ["Короткая история от команды «Доброго дома» — без шаблонов и воды."]
    used = set(h.lower() for h in _load_used_hooks())
    seed = int(hashlib.md5(f"{topic_id}:{category_id}".encode()).hexdigest()[:8], 16)
    for offset in range(len(pool)):
        candidate = pool[(seed + offset) % len(pool)]
        if candidate.lower() not in used:
            return f"<b>{candidate.rstrip('.?!')}?</b>" if "?" not in candidate else f"<b>{candidate}</b>"
    return f"<b>{pool[seed % len(pool)]}</b>"


def _extract_bullets(body_parts: list[str], max_items: int = 3) -> list[str]:
    """Вытаскивает смысловые фразы для списка."""
    bullets: list[str] = []
    for p in body_parts:
        plain = re.sub(r"<[^>]+>", " ", p)
        plain = re.sub(r"\s+", " ", plain).strip()
        if len(plain) < 40:
            continue
        sentences = re.split(r"(?<=[.!?])\s+", plain)
        for s in sentences:
            s = s.strip()
            if 25 < len(s) < 180 and not s.lower().startswith("брониру"):
                bullets.append(s)
            if len(bullets) >= max_items:
                return bullets
    return bullets[:max_items]


def build_text_variants(topic_data: dict) -> list[dict]:
    """
    Возвращает ровно 3 варианта: [{number, label, text_html}, ...].
    Структуры: классика | список-история | сцена + суть.
    """
    preset = topic_data.get("body_variants") or []
    if len(preset) >= 3:
        labels = topic_data.get("variant_labels") or [
            "Классический",
            "Список-история",
            "Сцена и суть",
        ]
        return [
            {
                "number": i + 1,
                "label": labels[i] if i < len(labels) else f"Вариант {i + 1}",
                "text_html": preset[i],
            }
            for i in range(3)
        ]

    base = topic_data.get("body", "")
    category_id = topic_data.get("category_id", "host_story")
    topic_id = topic_data.get("id", "")
    title_block, rest = _strip_bold_title(base)
    parts = _split_paragraphs(rest if title_block else base)
    if title_block and not parts:
        parts = _split_paragraphs(base)

    cta = _cta_paragraph(parts)
    body_parts = [p for p in parts if p != cta]
    title_line = title_block or (
        f"<b>{topic_data.get('title', '')}</b>" if topic_data.get("title") else ""
    )

    # Вариант 1 — классический полный текст
    v1 = base

    # Вариант 2 — заголовок + нумерованный список смыслов + CTA
    bullets = _extract_bullets(body_parts, max_items=3)
    if len(bullets) < 2 and body_parts:
        bullets = [
            re.sub(r"<[^>]+>", "", body_parts[0])[:160],
            re.sub(r"<[^>]+>", "", body_parts[-1])[:160] if len(body_parts) > 1 else "",
        ]
        bullets = [b.strip() for b in bullets if b.strip()]
    numbered = [f"{i + 1}️⃣ {b}" for i, b in enumerate(bullets[:3])]
    intro = body_parts[0] if body_parts else ""
    v2_parts = [title_line]
    if intro and intro not in bullets:
        v2_parts.append(intro)
    if numbered:
        v2_parts.append("\n".join(numbered))
    if cta:
        v2_parts.append(cta)
    v2 = _join_paragraphs(v2_parts)

    # Вариант 3 — другой hook + один сильный абзац + CTA (без дубля v1)
    hook = _pick_hook(category_id, topic_id)
    core = body_parts[1] if len(body_parts) > 1 else (body_parts[0] if body_parts else "")
    if core == intro:
        core = body_parts[-1] if len(body_parts) > 2 else core
    v3_parts = [hook]
    if core:
        v3_parts.append(core)
    if cta:
        v3_parts.append(cta)
    v3 = _join_paragraphs(v3_parts)

    return [
        {"number": 1, "label": "Классический", "text_html": v1},
        {"number": 2, "label": "Список-история", "text_html": v2},
        {"number": 3, "label": "Сцена и суть", "text_html": v3},
    ]
