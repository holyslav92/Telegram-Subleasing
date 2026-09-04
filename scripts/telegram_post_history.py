"""
История публикаций Telegram-постов «Добрый дом Тюмень».
Хранит id тем с датой и рубрикой; не допускает повторов в течение cooldown.
"""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
HISTORY_FILE = WORKSPACE_ROOT / "memory" / "telegram_posts" / "history.json"
POSTS_DIR = WORKSPACE_ROOT / "memory" / "telegram_posts"

# Не публиковать ту же тему повторно в течение ~2 месяцев
TOPIC_COOLDOWN_DAYS = 60


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[: len(fmt)], fmt)
        except ValueError:
            continue
    return None


def normalize_history_entry(entry) -> dict | None:
    """Приводит запись истории к единому виду."""
    if isinstance(entry, str):
        return {"id": entry, "category_id": "", "published_at": ""}
    if isinstance(entry, dict) and entry.get("id"):
        return {
            "id": entry["id"],
            "category_id": entry.get("category_id", ""),
            "published_at": entry.get("published_at", ""),
        }
    return None


def load_history() -> list[dict]:
    """Загружает историю; при отсутствии файла восстанавливает из сохранённых post_*.json."""
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                history = [e for e in (normalize_history_entry(x) for x in raw) if e]
                if history:
                    return history
        except Exception:
            pass

    rebuilt = rebuild_history_from_posts()
    if rebuilt:
        save_history(rebuilt)
    return rebuilt


def rebuild_history_from_posts() -> list[dict]:
    """Собирает историю из ранее сохранённых черновиков post_<category>_<timestamp>.json."""
    if not POSTS_DIR.exists():
        return []

    entries: dict[str, dict] = {}
    pattern = re.compile(r"post_([a-z_]+)_(\d{8})_(\d{6})\.json$")

    for path in sorted(POSTS_DIR.glob("post_*.json")):
        match = pattern.match(path.name)
        if not match:
            continue
        category_id, date_part, time_part = match.groups()
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        topic_id = data.get("id") or ""
        if not topic_id:
            continue

        published_at = data.get("created_at") or f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} {time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
        existing = entries.get(topic_id)
        if existing:
            old_dt = _parse_date(existing.get("published_at", ""))
            new_dt = _parse_date(published_at)
            if old_dt and new_dt and new_dt <= old_dt:
                continue

        entries[topic_id] = {
            "id": topic_id,
            "category_id": data.get("category_id") or category_id,
            "published_at": published_at,
        }

    return sorted(entries.values(), key=lambda x: x.get("published_at", ""))


def save_history(history: list[dict]) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def record_publication(topic_id: str, category_id: str = "") -> None:
    """Добавляет или обновляет запись о публикации темы."""
    if not topic_id:
        return

    history = load_history()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = False

    for entry in history:
        if entry["id"] == topic_id:
            entry["published_at"] = now_str
            if category_id:
                entry["category_id"] = category_id
            updated = True
            break

    if not updated:
        history.append({
            "id": topic_id,
            "category_id": category_id,
            "published_at": now_str,
        })

    save_history(history)


def get_ids_in_cooldown(history: list[dict], category_id: str | None = None) -> set[str]:
    """Возвращает id тем, которые ещё нельзя повторять."""
    cutoff = datetime.now() - timedelta(days=TOPIC_COOLDOWN_DAYS)
    blocked: set[str] = set()

    for entry in history:
        if category_id and entry.get("category_id") and entry["category_id"] != category_id:
            continue
        published_dt = _parse_date(entry.get("published_at", ""))
        if published_dt is None or published_dt >= cutoff:
            blocked.add(entry["id"])

    return blocked


def get_all_published_ids(history: list[dict] | None = None) -> list[str]:
    """Список всех когда-либо опубликованных id (для обратной совместимости)."""
    history = history or load_history()
    return [e["id"] for e in history if e.get("id")]
