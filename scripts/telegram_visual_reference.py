"""Правила референсов для реалистичных изображений Telegram-постов."""

from __future__ import annotations

import json
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = WORKSPACE_ROOT / "shared" / "telegram-visual-rules.json"


def load_visual_rules() -> dict:
    """Загружает настройки визуальных референсов."""
    if not RULES_FILE.exists():
        return {
            "reference_first": True,
            "require_two_references": True,
            "allow_prompt_only_generation": False,
            "curated_reference_required_topic_ids": [],
            "blocked_topic_ids": [],
        }
    with RULES_FILE.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_visual_blocked_topic_ids() -> set[str]:
    """Возвращает темы, навсегда исключённые из визуального пайплайна."""
    return {
        str(topic_id)
        for topic_id in load_visual_rules().get("blocked_topic_ids", [])
    }


def requires_curated_reference(topic: dict) -> bool:
    """Проверяет, нужна ли теме настоящая фотография конкретной локации."""
    topic_id = str(topic.get("id", ""))
    required_ids = {
        str(value)
        for value in load_visual_rules().get("curated_reference_required_topic_ids", [])
    }
    return topic_id in required_ids


def get_curated_reference_url(topic: dict) -> str:
    """Возвращает заданный для темы реальный референс."""
    return str(
        topic.get("visual_reference_url")
        or topic.get("reference_image_url")
        or ""
    ).strip()


def validate_reference_policy(reference_urls: list[str]) -> list[str]:
    """Возвращает причины, по которым нельзя запускать генерацию."""
    rules = load_visual_rules()
    reasons: list[str] = []
    clean_urls = [url for url in reference_urls if url]

    if rules.get("require_two_references", True) and len(clean_urls) != 2:
        reasons.append("нужны ровно два референса: логотип и исходное фото")
    if rules.get("allow_prompt_only_generation") is False and len(clean_urls) < 2:
        reasons.append("генерация только по текстовому описанию запрещена")
    return reasons
