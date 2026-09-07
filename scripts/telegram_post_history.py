"""
История публикаций Telegram-постов «Добрый дом Тюмень».
Ledger: id, entities, event_date, text_fingerprint — защита от повторов по смыслу.
"""

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = WORKSPACE_ROOT / "memory" / "telegram_posts"
HISTORY_FILE = POSTS_DIR / "history.json"
LEDGER_FILE = POSTS_DIR / "ledger.json"

TOPIC_COOLDOWN_DAYS = 60
ENTITY_COOLDOWN_DAYS = 45

# Известные сущности для анти-дубля (нижний регистр)
KNOWN_ENTITIES = [
    "озеро тихое",
    "тихое",
    "пошумим на тихом",
    "салют",
    "фейерверк",
    "nansi",
    "sidorov",
    "тбдт",
    "большой драматический",
    "филармония",
    "набережная туры",
    "мост влюбленных",
    "мост влюблённых",
    "летолето",
    "верхний бор",
    "дзержинского",
    "visit tyumen",
]

MONTHS_RU = {
    "январ": 1,
    "феврал": 2,
    "март": 3,
    "апрел": 4,
    "ма": 5,
    "июн": 6,
    "июл": 7,
    "август": 8,
    "сентябр": 9,
    "октябр": 10,
    "ноябр": 11,
    "декабр": 12,
}


def _parse_date(value: str) -> datetime | None:
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value[: len(fmt)], fmt)
        except ValueError:
            continue
    return None


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def text_fingerprint(text: str) -> str:
    plain = strip_html(text)[:500].lower()
    return hashlib.sha256(plain.encode("utf-8")).hexdigest()[:16]


def extract_entities_from_text(text: str, extra: list | None = None) -> list[str]:
    """Извлекает сущности из текста по словарю и явным тегам."""
    plain = strip_html(text).lower()
    found: set[str] = set()
    for entity in KNOWN_ENTITIES:
        if entity in plain:
            found.add(entity)
    if extra:
        for e in extra:
            e_norm = e.strip().lower()
            if e_norm and (e_norm in plain or len(e_norm) > 3):
                found.add(e_norm)
    return sorted(found)


def extract_event_dates_from_text(text: str, reference_year: int | None = None) -> list[str]:
    """Ищет даты событий в тексте; возвращает ISO-строки YYYY-MM-DD."""
    if not text:
        return []
    year = reference_year or datetime.now().year
    plain = strip_html(text).lower()
    dates: set[str] = set()

    # ISO: 2026-09-05
    for m in re.finditer(r"\b(20\d{2})-(\d{2})-(\d{2})\b", plain):
        dates.add(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")

    # DD.MM.YYYY или DD.MM
    for m in re.finditer(r"\b(\d{1,2})\.(\d{1,2})(?:\.(20\d{2}))?\b", plain):
        d, mo = int(m.group(1)), int(m.group(2))
        y = int(m.group(3)) if m.group(3) else year
        try:
            dates.add(datetime(y, mo, d).strftime("%Y-%m-%d"))
        except ValueError:
            pass

    # «5 сентября», «5 сентября 2026»
    for m in re.finditer(
        r"\b(\d{1,2})\s+(январ\w*|феврал\w*|март\w*|апрел\w*|ма\w*|июн\w*|июл\w*|"
        r"август\w*|сентябр\w*|октябр\w*|ноябр\w*|декабр\w*)\w*(?:\s+(20\d{2}))?\b",
        plain,
    ):
        day = int(m.group(1))
        month_word = m.group(2)
        y = int(m.group(3)) if m.group(3) else year
        month = None
        for prefix, num in MONTHS_RU.items():
            if month_word.startswith(prefix):
                month = num
                break
        if month:
            try:
                dates.add(datetime(y, month, day).strftime("%Y-%m-%d"))
            except ValueError:
                pass
    return sorted(dates)


def normalize_ledger_entry(entry) -> dict | None:
    if isinstance(entry, str):
        return {
            "id": entry,
            "category_id": "",
            "title": "",
            "published_at": "",
            "entities": [],
            "event_date": "",
            "text_fingerprint": "",
        }
    if not isinstance(entry, dict):
        return None
    topic_id = entry.get("id") or entry.get("topic_id") or ""
    if not topic_id and not entry.get("text_fingerprint"):
        return None
    text_src = entry.get("text_html") or entry.get("body") or entry.get("title") or ""
    entities = entry.get("entities") or extract_entities_from_text(text_src)
    event_date = entry.get("event_date") or ""
    if not event_date:
        ev_dates = extract_event_dates_from_text(text_src)
        if ev_dates:
            event_date = ev_dates[0]
    fp = entry.get("text_fingerprint") or text_fingerprint(text_src)
    return {
        "id": topic_id or f"anon_{fp}",
        "category_id": entry.get("category_id", ""),
        "title": entry.get("title", ""),
        "published_at": entry.get("published_at", ""),
        "entities": entities,
        "event_date": event_date,
        "text_fingerprint": fp,
    }


def load_ledger() -> list[dict]:
    """Загружает ledger.json; при отсутствии — мигрирует из history.json или post_*.json."""
    if LEDGER_FILE.exists():
        try:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                ledger = [e for e in (normalize_ledger_entry(x) for x in raw) if e]
                if ledger:
                    return ledger
        except Exception:
            pass

    # Миграция из history.json
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, list):
                ledger = [e for e in (normalize_ledger_entry(x) for x in raw) if e]
                if ledger:
                    save_ledger(ledger)
                    return ledger
        except Exception:
            pass

    rebuilt = rebuild_ledger_from_posts()
    if rebuilt:
        save_ledger(rebuilt)
    return rebuilt


def save_ledger(ledger: list[dict]) -> None:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    normalized = [normalize_ledger_entry(e) for e in ledger]
    normalized = [e for e in normalized if e]
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, ensure_ascii=False, indent=2)
    # Обратная совместимость: history.json без entities
    history_compat = [
        {
            "id": e["id"],
            "category_id": e.get("category_id", ""),
            "published_at": e.get("published_at", ""),
        }
        for e in normalized
        if e.get("id") and not e["id"].startswith("anon_")
    ]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_compat, f, ensure_ascii=False, indent=2)


def load_history() -> list[dict]:
    """Обратная совместимость: возвращает ledger как history."""
    return load_ledger()


def save_history(history: list[dict]) -> None:
    save_ledger(history)


def rebuild_ledger_from_posts() -> list[dict]:
    """Собирает ledger из всех post_*.json, включая посты без id."""
    if not POSTS_DIR.exists():
        return []

    entries_by_key: dict[str, dict] = {}
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

        text = data.get("text_html") or data.get("body") or ""
        topic_id = data.get("id") or ""
        fp = text_fingerprint(text)
        if not topic_id:
            topic_id = f"manual_{category_id}_{fp[:8]}"

        published_at = data.get("created_at") or (
            f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} "
            f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}"
        )
        entities = data.get("entities") or extract_entities_from_text(text)
        event_dates = extract_event_dates_from_text(text)
        event_date = data.get("event_date") or (event_dates[0] if event_dates else "")

        entry = {
            "id": topic_id,
            "category_id": data.get("category_id") or category_id,
            "title": data.get("title", ""),
            "published_at": published_at,
            "entities": entities,
            "event_date": event_date,
            "text_fingerprint": fp,
        }
        key = topic_id if not topic_id.startswith("manual_") else fp
        existing = entries_by_key.get(key)
        if existing:
            old_dt = _parse_date(existing.get("published_at", ""))
            new_dt = _parse_date(published_at)
            if old_dt and new_dt and new_dt <= old_dt:
                continue
        entries_by_key[key] = entry

    return sorted(entries_by_key.values(), key=lambda x: x.get("published_at", ""))


def rebuild_history_from_posts() -> list[dict]:
    return rebuild_ledger_from_posts()


def record_publication(
    topic_id: str,
    category_id: str = "",
    title: str = "",
    text_html: str = "",
    entities: list | None = None,
    event_date: str = "",
) -> None:
    """Добавляет или обновляет запись в ledger после публикации."""
    if not topic_id and not text_html:
        return

    ledger = load_ledger()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    fp = text_fingerprint(text_html) if text_html else ""
    ent = entities or extract_entities_from_text(text_html)
    ev = event_date
    if not ev and text_html:
        evs = extract_event_dates_from_text(text_html)
        ev = evs[0] if evs else ""

    updated = False
    for entry in ledger:
        if topic_id and entry.get("id") == topic_id:
            entry["published_at"] = now_str
            if category_id:
                entry["category_id"] = category_id
            if title:
                entry["title"] = title
            if ent:
                entry["entities"] = ent
            if ev:
                entry["event_date"] = ev
            if fp:
                entry["text_fingerprint"] = fp
            updated = True
            break

    if not updated:
        ledger.append({
            "id": topic_id or f"anon_{fp}",
            "category_id": category_id,
            "title": title,
            "published_at": now_str,
            "entities": ent,
            "event_date": ev,
            "text_fingerprint": fp,
        })

    save_ledger(ledger)


def get_ids_in_cooldown(ledger: list[dict], category_id: str | None = None) -> set[str]:
    cutoff = datetime.now() - timedelta(days=TOPIC_COOLDOWN_DAYS)
    blocked: set[str] = set()
    for entry in ledger:
        if category_id and entry.get("category_id") and entry["category_id"] != category_id:
            continue
        published_dt = _parse_date(entry.get("published_at", ""))
        if published_dt is None or published_dt >= cutoff:
            tid = entry.get("id", "")
            if tid and not tid.startswith("anon_"):
                blocked.add(tid)
    return blocked


def get_entities_in_cooldown(ledger: list[dict] | None = None) -> set[str]:
    """Сущности, опубликованные недавно — нельзя повторять."""
    ledger = ledger or load_ledger()
    cutoff = datetime.now() - timedelta(days=ENTITY_COOLDOWN_DAYS)
    blocked: set[str] = set()
    for entry in ledger:
        published_dt = _parse_date(entry.get("published_at", ""))
        if published_dt is None or published_dt >= cutoff:
            for ent in entry.get("entities") or []:
                blocked.add(ent.lower())
    return blocked


def get_all_published_ids(ledger: list[dict] | None = None) -> list[str]:
    ledger = ledger or load_ledger()
    return [e["id"] for e in ledger if e.get("id") and not e["id"].startswith("anon_")]


def is_event_date_past(event_date: str) -> bool:
    if not event_date:
        return False
    dt = _parse_date(event_date)
    if not dt:
        return False
    return dt.date() < datetime.now().date()
