"""
Три текстовых варианта поста на одну тему и одно изображение.
Менеджер выбирает вариант перед публикацией в канал.
"""

import copy
import re


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
    """Последний абзац с CTA (сайт / Авито / Макс)."""
    for p in reversed(parts):
        if "добрыйдом-72" in p.lower() or "avito.ru" in p.lower():
            return p
    return parts[-1] if parts else ""


def build_text_variants(topic_data: dict) -> list[dict]:
    """
    Возвращает ровно 3 варианта: [{number, label, text_html}, ...].
    Если в банке есть body_variants — используем их.
    """
    preset = topic_data.get("body_variants") or []
    if len(preset) >= 3:
        labels = topic_data.get("variant_labels") or ["Классический", "Короткий", "С акцентом на заботу"]
        return [
            {
                "number": i + 1,
                "label": labels[i] if i < len(labels) else f"Вариант {i + 1}",
                "text_html": preset[i],
            }
            for i in range(3)
        ]

    base = topic_data.get("body", "")
    title_block, rest = _strip_bold_title(base)
    parts = _split_paragraphs(rest if title_block else base)
    if title_block and not parts:
        parts = _split_paragraphs(base)

    cta = _cta_paragraph(parts)
    body_parts = [p for p in parts if p != cta]
    title_line = title_block or (f"<b>{topic_data.get('title', '')}</b>" if topic_data.get("title") else "")

    v1 = base

    # Вариант 2 — короче: заголовок + суть (1–2 абзаца) + CTA
    short_core = body_parts[:2] if len(body_parts) >= 2 else body_parts[:1]
    v2 = _join_paragraphs([title_line] + short_core + ([cta] if cta else []))

    # Вариант 3 — другой заход: вопрос + основной абзац + CTA
    hook = "<b>Ищете жильё в Тюмени без суеты при заезде?</b>"
    if body_parts:
        alt_mid = body_parts[1:] if len(body_parts) > 1 else body_parts
        v3 = _join_paragraphs([hook] + alt_mid[:2] + ([cta] if cta else []))
    else:
        v3 = _join_paragraphs([hook, cta] if cta else [hook])

    return [
        {"number": 1, "label": "Классический", "text_html": v1},
        {"number": 2, "label": "Короткий", "text_html": v2},
        {"number": 3, "label": "С другим заходом", "text_html": v3},
    ]
