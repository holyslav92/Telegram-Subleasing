"""Правила контента Telegram: запрещённые темы и формулировки."""

import json
import re
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
RULES_FILE = WORKSPACE_ROOT / "shared" / "telegram-content-rules.json"

_DEFAULT = {
    "blocked_topic_ids": [],
    "forbidden_phrases": [],
    "forbidden_reasons": {},
}


def load_content_rules() -> dict:
    if not RULES_FILE.exists():
        return dict(_DEFAULT)
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {**_DEFAULT, **data}
    except Exception:
        return dict(_DEFAULT)


def get_blocked_topic_ids() -> set[str]:
    rules = load_content_rules()
    return {str(x) for x in rules.get("blocked_topic_ids") or []}


def check_forbidden_content(
    text: str = "",
    topic_id: str = "",
    title: str = "",
) -> list[str]:
    """Возвращает список причин FAIL по правилам бренда."""
    rules = load_content_rules()
    reasons: list[str] = []
    blocked = get_blocked_topic_ids()
    if topic_id and topic_id in blocked:
        msg = rules.get("forbidden_reasons", {}).get(topic_id, "тема заблокирована правилами бренда")
        reasons.append(f"заблокированная тема '{topic_id}': {msg}")

    haystack = f"{title}\n{text}".lower()
    for phrase in rules.get("forbidden_phrases") or []:
        p = phrase.lower().strip()
        if p and p in haystack:
            msg = rules.get("forbidden_reasons", {}).get(p, f"запрещённая формулировка «{phrase}»")
            reasons.append(msg)
    return reasons
