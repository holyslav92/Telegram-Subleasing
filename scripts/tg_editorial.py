#!/usr/bin/env python3
"""
Редакционная система Telegram «Добрый дом» — единая точка входа.

Порядок работы (любая модель):
  1. python3 scripts/tg_editorial.py plan            → бриф на сегодня (рубрика, формат, запреты, запросы)
  2. исследование в интернете + python3 scripts/tg_editorial.py fetch <url>
  3. черновик JSON → memory/telegram_posts/drafts/<дата>.json
  4. python3 scripts/tg_editorial.py validate <draft> → исправлять, пока не PASS
  5. python3 scripts/tg_editorial.py publish <draft>  → картинка + публикация + память в main

Всё, что можно проверить кодом, проверяет код: свежесть, повторы тем/форматов/кластеров,
источники, длину, штампы, дубли фраз. Модель только ищет факты и пишет текст по схеме.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

ROOT = SCRIPT_DIR.parent
CONFIG_PATH = ROOT / "shared" / "telegram-editorial.json"
POSTS_DIR = ROOT / "memory" / "telegram_posts"
PUBLISHED_PATH = POSTS_DIR / "published.json"
LEDGER_PATH = POSTS_DIR / "ledger.json"
DRAFTS_DIR = POSTS_DIR / "drafts"
CHANNEL_URL = "https://t.me/s/Dobriy_dom_72"
USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
OWN_SITE_MARKERS = ("xn---72-9cdob8azaodt6k", "добрыйдом-72")

MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа",
              "сентября", "октября", "ноября", "декабря"]
MONTHS_NOM = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль", "август",
              "сентябрь", "октябрь", "ноябрь", "декабрь"]
WEEKDAYS = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]

EMOJI_RE = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\uFE0F\u20E3]")
URL_RE = re.compile(r"(https?://|www\.|t\.me/|@[A-Za-z0-9_]{4,})")
WORD_RE = re.compile(r"[а-яa-z0-9]+")

_CHANNEL_CACHE: list[dict] | None = None


# ───────────────────────── базовые утилиты ─────────────────────────

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def norm(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text).lower().replace("ё", "е")
    return re.sub(r"\s+", " ", text).strip()


def words(text: str) -> list[str]:
    return WORD_RE.findall(norm(text))


def today_local(cfg: dict | None = None) -> date:
    forced = os.environ.get("TG_TODAY", "").strip()
    if forced:
        return date.fromisoformat(forced)
    offset = (cfg or load_config()).get("timezone_offset_hours", 5)
    return (datetime.now(timezone.utc) + timedelta(hours=offset)).date()


def parse_day(value: str) -> date | None:
    if not value:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(value))
    if not m:
        return None
    try:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def to_ascii_url(url: str) -> str:
    parts = urllib.parse.urlsplit(url.strip())
    host = parts.hostname or ""
    try:
        host_ascii = host.encode("idna").decode("ascii")
    except UnicodeError:
        host_ascii = host
    netloc = host_ascii + (f":{parts.port}" if parts.port else "")
    path = urllib.parse.quote(parts.path, safe="/%:@!$&'()*+,;=-._~")
    query = urllib.parse.quote(parts.query, safe="=&%:@!$'()*+,;/?-._~")
    return urllib.parse.urlunsplit((parts.scheme, netloc, path, query, ""))


def http_get(url: str, timeout: int = 20, max_bytes: int = 3_000_000) -> tuple[int, str, str, bytes]:
    """Возвращает (status, final_url, content_type, body)."""
    req = urllib.request.Request(to_ascii_url(url), headers={
        "User-Agent": USER_AGENT,
        "Accept-Language": "ru-RU,ru;q=0.9",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(max_bytes)
            return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as e:
        return e.code, url, "", b""
    except Exception:
        return 0, url, "", b""


def decode_body(body: bytes, content_type: str) -> str:
    m = re.search(r"charset=([\w-]+)", content_type or "", re.I)
    enc = m.group(1) if m else "utf-8"
    try:
        return body.decode(enc, errors="ignore")
    except LookupError:
        return body.decode("utf-8", errors="ignore")


def html_to_text(raw: str) -> str:
    raw = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", html.unescape(raw)).strip()


def meta_content(raw: str, names: tuple[str, ...]) -> str:
    for name in names:
        for pattern in (
            rf'<meta[^>]+(?:property|name|itemprop)=["\']{re.escape(name)}["\'][^>]*content=["\']([^"\']+)',
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]*(?:property|name|itemprop)=["\']{re.escape(name)}["\']',
        ):
            m = re.search(pattern, raw, re.I)
            if m:
                return html.unescape(m.group(1)).strip()
    return ""


def fetch_page(url: str) -> dict:
    status, final_url, ctype, body = http_get(url)
    raw = decode_body(body, ctype) if body else ""
    title_m = re.search(r"(?is)<title[^>]*>(.*?)</title>", raw)
    og_image = meta_content(raw, ("og:image", "og:image:url", "twitter:image"))
    if og_image:
        og_image = urllib.parse.urljoin(final_url, og_image)
    published = meta_content(raw, ("article:published_time", "datePublished", "pubdate", "date"))
    if not published:
        m = re.search(r'"datePublished"\s*:\s*"([^"]+)"', raw)
        published = m.group(1) if m else ""
    return {
        "url": url,
        "final_url": final_url,
        "status": status,
        "ok": status == 200 and bool(raw),
        "title": html.unescape(title_m.group(1)).strip() if title_m else "",
        "og_image": og_image,
        "published": published,
        "text": html_to_text(raw),
    }


def is_image_url(url: str) -> bool:
    if not url or not url.startswith("http"):
        return False
    status, _, ctype, body = http_get(url, timeout=20, max_bytes=65536)
    return status == 200 and (ctype.startswith("image/") or body[:4] in (b"\xff\xd8\xff\xe0", b"\x89PNG", b"RIFF") or body[:3] == b"\xff\xd8\xff")


# ───────────────────────── кластеры и история ─────────────────────────

def _kw_regex(keyword: str) -> re.Pattern:
    kw = norm(keyword) if keyword.strip() == keyword else norm(keyword) + " "
    return re.compile(r"(?<![а-яa-z0-9])" + re.escape(kw))


def cluster_hits(text: str, cfg: dict) -> dict[str, int]:
    # дубли предложений (старые посты с шаблонной сценой) считаются один раз
    sentences = dict.fromkeys(
        re.sub(r"^[^а-яa-z]+", "", s.strip()) for s in re.split(r"(?<=[.!?…])\s+|\n+", norm(text)) if s.strip()
    )
    plain = " " + " ".join(sentences) + " "
    hits: dict[str, int] = {}
    for cid, cl in cfg["clusters"].items():
        n = sum(len(_kw_regex(kw).findall(plain)) for kw in cl["keywords"])
        if n:
            hits[cid] = n
    return hits


def strong_clusters(title: str, body: str, cfg: dict, min_hits: int = 2) -> list[str]:
    """Кластер — тема поста, если встречается в заголовке или ≥min_hits раз в тексте."""
    in_title = cluster_hits(title, cfg)
    in_all = cluster_hits(f"{title} {body}", cfg)
    return sorted(c for c, n in in_all.items() if c in in_title or n >= min_hits)


def load_json_list(path: Path) -> list:
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def fetch_channel_posts() -> list[dict]:
    """Публичный канал @Dobriy_dom_72 — страховка, если память в репозитории отстала."""
    global _CHANNEL_CACHE
    if _CHANNEL_CACHE is not None:
        return _CHANNEL_CACHE
    posts: list[dict] = []
    if os.environ.get("TG_OFFLINE") == "1":
        _CHANNEL_CACHE = posts
        return posts
    status, _, ctype, body = http_get(CHANNEL_URL, timeout=15)
    if status == 200 and body:
        raw = decode_body(body, ctype)
        blocks = raw.split('class="tgme_widget_message_wrap')
        for block in blocks[1:]:
            tm = re.search(r'tgme_widget_message_text[^>]*>(.*?)</div>', block, re.S)
            dm = re.search(r'<time[^>]+datetime="([^"]+)"', block)
            if not tm:
                continue
            text = html_to_text(tm.group(1).replace("<br/>", "\n").replace("<br>", "\n"))
            posts.append({
                "source": "channel",
                "date": (dm.group(1)[:10] if dm else ""),
                "title": text[:90],
                "text": text,
            })
    _CHANNEL_CACHE = posts
    return posts


def load_history(cfg: dict, include_channel: bool = True) -> list[dict]:
    """Объединённая история: published.json + ledger.json + публичный канал. Новые — последними."""
    items: list[dict] = []
    seen: set[str] = set()

    def add(item: dict) -> None:
        key = norm(item.get("title", ""))[:60] + "|" + (item.get("date") or "")
        fp = norm(item.get("text", ""))[:120]
        if key in seen or (fp and fp in seen):
            return
        seen.add(key)
        if fp:
            seen.add(fp)
        if not item.get("clusters"):
            # у старых постов CTA-хвосты многословны — нужен порог выше, чтобы не ловить случайные слова
            item["clusters"] = strong_clusters(item.get("title", ""), item.get("text", ""), cfg, min_hits=3)
        items.append(item)

    for e in load_json_list(PUBLISHED_PATH):
        add({
            "source": "published",
            "date": e.get("date") or (e.get("published_at") or "")[:10],
            "topic_id": e.get("topic_id", ""),
            "pillar": e.get("pillar", ""),
            "format": e.get("format", ""),
            "title": e.get("title", ""),
            "text": e.get("text", ""),
            "clusters": e.get("clusters") or [],
            "entities": e.get("entities") or [],
            "cta_id": e.get("cta_id", ""),
        })
    for e in load_json_list(LEDGER_PATH):
        if not isinstance(e, dict):
            continue
        add({
            "source": "ledger",
            "date": (e.get("published_at") or "")[:10],
            "topic_id": e.get("id", ""),
            "pillar": e.get("category_id", ""),
            "format": "",
            "title": e.get("title", ""),
            "text": norm(e.get("text_html") or e.get("body") or ""),
            "clusters": [],
            "entities": e.get("entities") or [],
        })
    if include_channel:
        for e in fetch_channel_posts():
            add(e)
    items.sort(key=lambda x: x.get("date") or "0000")
    return items


def recent(history: list[dict], today: date, days: int) -> list[dict]:
    border = today - timedelta(days=days)
    out = []
    for h in history:
        d = parse_day(h.get("date", ""))
        if d and border <= d <= today:
            out.append(h)
    return out


def cluster_last_used(history: list[dict]) -> dict[str, date]:
    last: dict[str, date] = {}
    for h in history:
        d = parse_day(h.get("date", ""))
        if not d:
            continue
        for c in h.get("clusters") or []:
            if c not in last or d > last[c]:
                last[c] = d
    return last


def blocked_clusters(history: list[dict], cfg: dict, today: date) -> dict[str, str]:
    """{cluster_id: 'занят до YYYY-MM-DD (был DATE)'}"""
    default_cd = cfg["novelty"]["cluster_cooldown_days_default"]
    out: dict[str, str] = {}
    for cid, last in cluster_last_used(history).items():
        cd = cfg["clusters"].get(cid, {}).get("cooldown_days", default_cd)
        until = last + timedelta(days=cd)
        if until > today:
            out[cid] = f"{cfg['clusters'].get(cid, {}).get('name', cid)}: был {last.isoformat()}, свободен с {until.isoformat()}"
    return out


def first_word(text: str) -> str:
    w = words(text)
    return w[0] if w else ""


def opening_words(text: str, n: int = 3) -> str:
    return " ".join(words(text)[:n])


# ───────────────────────── план дня ─────────────────────────

def _date_tokens(today: date) -> dict:
    monday = today - timedelta(days=today.weekday())
    sunday = monday + timedelta(days=6)
    saturday = monday + timedelta(days=5)
    nxt = (today.replace(day=1) + timedelta(days=32)).replace(day=1)

    def dm(d: date) -> str:
        return f"{d.day} {MONTHS_GEN[d.month - 1]}"

    return {
        "date_dm": dm(today),
        "year": str(today.year),
        "month_year": f"{MONTHS_NOM[today.month - 1]} {today.year}",
        "next_month_year": f"{MONTHS_NOM[nxt.month - 1]} {nxt.year}",
        "week_range": f"{dm(max(today, monday))} — {dm(sunday)} {today.year}",
        "weekend_range": f"{dm(saturday)}–{dm(sunday)} {today.year}",
    }


def pillar_for(today: date, cfg: dict) -> str:
    return cfg["weekday_pillars"][str(today.weekday())]


def build_plan(cfg: dict, today: date, history: list[dict] | None = None) -> dict:
    history = history if history is not None else load_history(cfg)
    nov = cfg["novelty"]
    pillar_id = pillar_for(today, cfg)
    pillar = cfg["pillars"][pillar_id]
    last_posts = history[-12:]
    recent_formats = [h.get("format") for h in last_posts if h.get("format")]
    avoid_formats = set(recent_formats[-nov["format_not_in_last_posts"]:])
    formats = [f for f in pillar["formats"] if f not in avoid_formats] or pillar["formats"][:]
    tokens = _date_tokens(today)
    blocked = blocked_clusters(history, cfg, today)
    entity_window = recent(history, today, nov["entity_cooldown_days"])
    blocked_entities = sorted({e for h in entity_window for e in (h.get("entities") or []) if e})
    last_titles = [h.get("title", "") for h in history[-20:] if h.get("title")]
    avoid_first_words = sorted({first_word(t) for t in last_titles[-nov["title_first_word_not_in_last_posts"]:] if t})
    draft_path = DRAFTS_DIR / f"{today.isoformat()}.json"
    fresh_clusters = [cid for cid in cfg["clusters"] if cid not in blocked]

    template = {
        "date": today.isoformat(),
        "pillar": pillar_id,
        "format": formats[0],
        "topic_id": "латиница_через_подчёркивание_уникально",
        "clusters": ["1–3 id из free_clusters, о чём пост на самом деле"],
        "title": "Заголовок 18–80 символов, живой, с конкретикой",
        "paragraphs": ["1–3 абзаца по 40–320 символов, каждый с новым фактом"],
        "list_items": ["только если формат требует список: 2–5 пунктов с датой/цифрой"],
        "question": "вопрос подписчикам (обязателен для fact_question/poll_question, иначе можно пусто)",
        "entities": ["ключевые имена собственные: площадка, событие, артист, место"],
        "event_date": "YYYY-MM-DD ближайшего события или пусто",
        "sources": [{"url": "https://…", "published": "YYYY-MM-DD если это новость", "must_contain": ["точная фраза/название со страницы"]}],
        "image_headline": "надпись на картинке до 34 символов",
        "image": {"kind": "city|event|apartment", "reference_url": "реальное фото места (og:image из fetch) или пусто", "scene": "описание сцены по-английски, реалистично"},
    }
    return {
        "date": today.isoformat(),
        "weekday": WEEKDAYS[today.weekday()],
        "pillar": pillar_id,
        "pillar_name": pillar["name"],
        "goal": pillar["goal"],
        "allowed_formats": {f: cfg["formats"][f] for f in formats},
        "fresh_source_required": pillar.get("fresh_source_required", False),
        "event_window_days": pillar.get("event_window_days", 0),
        "news_max_age_days": pillar.get("news_max_age_days"),
        "search_queries": [q.format(**tokens) for q in pillar["queries"]],
        "source_hints": pillar.get("source_hints", []),
        "blocked_clusters": blocked,
        "free_clusters": fresh_clusters,
        "blocked_entities": blocked_entities,
        "avoid_title_first_words": avoid_first_words,
        "recent_titles": last_titles,
        "limits": cfg["limits"],
        "writing_rules": cfg["writing_rules"],
        "gold_examples": cfg["gold_examples"],
        "draft_path": str(draft_path.relative_to(ROOT)),
        "draft_template": template,
        "next_steps": [
            "1. Найди 3–6 свежих источников по search_queries (WebSearch). Бери конкретику: даты, площадки, цены, адреса.",
            "2. Для каждого источника: python3 scripts/tg_editorial.py fetch <url> — проверь, что факт виден на странице; возьми og_image как reference_url.",
            "3. Выбери тему, которая НЕ попадает в blocked_clusters / blocked_entities / recent_titles.",
            f"4. Запиши черновик в {draft_path.relative_to(ROOT)} строго по draft_template.",
            f"5. python3 scripts/tg_editorial.py validate {draft_path.relative_to(ROOT)} — чини ошибки, пока не будет PASS (до 5 попыток, при тупике — смени тему).",
            f"6. python3 scripts/tg_editorial.py publish {draft_path.relative_to(ROOT)} — картинка, публикация, память в main.",
        ],
    }


# ───────────────────────── проверка черновика ─────────────────────────

def draft_body_text(d: dict) -> str:
    parts = list(d.get("paragraphs") or []) + list(d.get("list_items") or [])
    if d.get("question"):
        parts.append(d["question"])
    return "\n".join(p for p in parts if p)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?…])\s+|\n+", text) if len(s.strip()) > 15]


def check_internal_repeats(d: dict) -> list[str]:
    errors = []
    title = d.get("title", "")
    body = draft_body_text(d)
    seen: dict[str, str] = {}
    for s in _sentences(body):
        k = norm(s)
        if k in seen:
            errors.append(f"повтор предложения: «{s[:60]}…»")
        seen[k] = s
    w = words(body)
    shingles: dict[tuple, int] = {}
    for i in range(len(w) - 4):
        sh = tuple(w[i:i + 5])
        shingles[sh] = shingles.get(sh, 0) + 1
    rep = [" ".join(k) for k, v in shingles.items() if v > 1]
    if rep:
        errors.append(f"повтор фразы из 5+ слов: «{rep[0]}»")
    nt = norm(title)
    if nt and nt in norm(body):
        errors.append("заголовок дословно повторяется в тексте")
    for item in d.get("list_items") or []:
        if SequenceMatcher(None, norm(item), nt).ratio() > 0.7:
            errors.append("пункт списка повторяет заголовок")
    paras = d.get("paragraphs") or []
    for i in range(len(paras)):
        for j in range(i + 1, len(paras)):
            if SequenceMatcher(None, norm(paras[i]), norm(paras[j])).ratio() > 0.6:
                errors.append(f"абзацы {i + 1} и {j + 1} почти одинаковые")
    return errors


def check_banned(d: dict, cfg: dict) -> list[str]:
    text = norm(" ".join([d.get("title", ""), d.get("image_headline", ""), draft_body_text(d)]))
    errors = []
    for b in cfg["banned_phrases"]:
        if b.get("match") == "regex":
            if re.search(b["pattern"], text):
                errors.append(f"запрещено ({b['reason']}): «{b['pattern']}»")
        elif norm(b["text"]) in text:
            errors.append(f"запрещено ({b['reason']}): «{b['text']}»")
    return errors


def verify_sources(d: dict, today: date, pillar: dict, offline: bool) -> tuple[list[str], list[str], list[dict]]:
    errors, warnings, pages = [], [], []
    sources = d.get("sources") or []
    external = [s for s in sources if isinstance(s, dict) and s.get("url") and not any(m in to_ascii_url(s["url"]) for m in OWN_SITE_MARKERS)]
    if pillar.get("fresh_source_required") and not external:
        errors.append("нужен хотя бы один внешний источник (не сайт «Доброго дома»)")
    for s in sources:
        if not isinstance(s, dict) or not s.get("url", "").startswith("http"):
            errors.append(f"источник без корректного url: {s}")
            continue
        mc = [m for m in (s.get("must_contain") or []) if len(norm(m)) >= 4]
        if not mc:
            errors.append(f"у источника {s['url']} нет must_contain (точная фраза со страницы, ≥4 символов)")
    max_age = pillar.get("news_max_age_days")
    if max_age:
        fresh = False
        for s in external:
            pd = parse_day(s.get("published", ""))
            if pd and today - timedelta(days=max_age) <= pd <= today:
                fresh = True
        if not fresh:
            errors.append(f"новость должна быть не старше {max_age} дней: укажи sources[].published (YYYY-MM-DD) у свежего источника")
    if offline or errors:
        return errors, warnings, pages
    verified = 0
    for s in sources:
        page = fetch_page(s["url"])
        pages.append(page)
        if not page["ok"]:
            warnings.append(f"источник не открылся (HTTP {page['status']}): {s['url']}")
            continue
        text = norm(page["text"] + " " + page["title"])
        found = [m for m in s.get("must_contain", []) if norm(m) in text]
        if found:
            verified += 1
        else:
            warnings.append(f"на странице {s['url']} не нашлось ни одной фразы из must_contain {s.get('must_contain')}")
        pd = parse_day(s.get("published", ""))
        real_pd = parse_day(page.get("published", ""))
        if pd and real_pd and abs((pd - real_pd).days) > 1:
            errors.append(f"published у {s['url']} = {pd}, а на странице {real_pd}")
    if verified == 0:
        errors.append("ни один источник не подтвердил факты (must_contain не найден в HTML). Возьми источник, где факт виден в тексте страницы")
    return errors, warnings, pages


def validate_draft(d: dict, cfg: dict, today: date, history: list[dict] | None = None,
                   offline: bool = False) -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    lim = cfg["limits"]
    nov = cfg["novelty"]
    history = history if history is not None else load_history(cfg, include_channel=not offline)

    for key in ("date", "pillar", "format", "topic_id", "title", "paragraphs", "sources", "image_headline", "image"):
        if not d.get(key):
            errors.append(f"нет поля {key}")
    if errors:
        return {"ok": False, "errors": errors, "warnings": warnings}

    if parse_day(d["date"]) != today:
        errors.append(f"date={d['date']}, а сегодня {today.isoformat()} — черновик должен быть сегодняшним")
    expected_pillar = pillar_for(today, cfg)
    pillar_id = d["pillar"]
    if pillar_id not in cfg["pillars"]:
        errors.append(f"неизвестная рубрика {pillar_id}")
        return {"ok": False, "errors": errors, "warnings": warnings}
    if pillar_id != expected_pillar:
        if d.get("pillar_override_reason", "").strip():
            warnings.append(f"рубрика {pillar_id} вместо {expected_pillar}: {d['pillar_override_reason']}")
        else:
            errors.append(f"сегодня рубрика {expected_pillar}; другую можно только с pillar_override_reason (срочное большое событие)")
    pillar = cfg["pillars"][pillar_id]
    fmt_id = d["format"]
    fmt = cfg["formats"].get(fmt_id)
    if not fmt:
        errors.append(f"неизвестный формат {fmt_id}")
        return {"ok": False, "errors": errors, "warnings": warnings}
    if fmt_id not in pillar["formats"]:
        errors.append(f"формат {fmt_id} не входит в рубрику {pillar_id}: {pillar['formats']}")
    if not re.fullmatch(r"[a-z0-9_]{6,80}", d["topic_id"]):
        errors.append("topic_id: латиница/цифры/_ , 6–80 символов")

    title = d["title"].strip()
    paras = [p.strip() for p in d.get("paragraphs") or [] if p and p.strip()]
    items = [i.strip() for i in d.get("list_items") or [] if i and i.strip()]
    question = (d.get("question") or "").strip()
    if not lim["title_min"] <= len(title) <= lim["title_max"]:
        errors.append(f"заголовок {len(title)} симв., нужно {lim['title_min']}–{lim['title_max']}")
    if not lim["paragraphs_min"] <= len(paras) <= lim["paragraphs_max"]:
        errors.append(f"абзацев {len(paras)}, нужно {lim['paragraphs_min']}–{lim['paragraphs_max']}")
    for i, p in enumerate(paras, 1):
        if not lim["paragraph_min"] <= len(p) <= lim["paragraph_max"]:
            errors.append(f"абзац {i}: {len(p)} симв., нужно {lim['paragraph_min']}–{lim['paragraph_max']}")
    if len(items) > lim["list_items_max"]:
        errors.append(f"пунктов {len(items)}, максимум {lim['list_items_max']}")
    for i, it in enumerate(items, 1):
        if len(it) > lim["list_item_max"]:
            errors.append(f"пункт {i}: {len(it)} симв., максимум {lim['list_item_max']}")
    if fmt.get("needs_list") and len(items) < fmt.get("list_min", 2):
        errors.append(f"формат {fmt_id} требует список минимум из {fmt.get('list_min', 2)} пунктов")
    if not fmt.get("needs_list") and items:
        warnings.append(f"формат {fmt_id} обычно без списка")
    if fmt.get("needs_question") and not question.endswith("?"):
        errors.append(f"формат {fmt_id} требует question с «?» в конце")
    if pillar_id in ("week_afisha", "weekend") and items:
        no_date = [it for it in items if not re.search(r"\d", it)]
        if no_date:
            errors.append(f"в афише у каждого пункта нужна дата/время: «{no_date[0][:50]}»")
    body = draft_body_text({"paragraphs": paras, "list_items": items, "question": question})
    if not lim["body_min"] <= len(body) <= lim["body_max"]:
        errors.append(f"текст {len(body)} симв., нужно {lim['body_min']}–{lim['body_max']} (SMM: коротко)")
    if len(d.get("image_headline", "")) > lim["image_headline_max"]:
        errors.append(f"image_headline длиннее {lim['image_headline_max']} симв.")
    all_text = " ".join([title, body, d.get("image_headline", "")])
    if URL_RE.search(all_text):
        errors.append("ссылки и @упоминания в тексте запрещены — их добавляет рендер")
    if EMOJI_RE.search(all_text):
        errors.append("эмодзи в тексте запрещены — рендер сам оформит список")
    if re.search(r"<[a-z/][^>]*>", all_text, re.I):
        errors.append("HTML-теги в тексте запрещены — пиши чистый текст")

    errors += check_internal_repeats({"title": title, "paragraphs": paras, "list_items": items, "question": question})
    errors += check_banned(d, cfg)

    # Свежесть событий
    ev = parse_day(d.get("event_date", ""))
    window = pillar.get("event_window_days", 0)
    if d.get("event_date") and not ev:
        errors.append("event_date не в формате YYYY-MM-DD")
    if ev:
        if ev < today:
            errors.append(f"event_date {ev} уже прошла")
        elif window and ev > today + timedelta(days=window):
            errors.append(f"event_date {ev} дальше окна рубрики ({window} дн.)")
    elif pillar_id in ("week_afisha", "weekend") or fmt_id == "big_event":
        errors.append("для афиши/события нужен event_date ближайшего события")

    # Новизна
    declared = [c for c in d.get("clusters") or [] if c]
    unknown = [c for c in declared if c not in cfg["clusters"]]
    if unknown:
        errors.append(f"неизвестные clusters {unknown}; допустимые: {list(cfg['clusters'])}")
    if len(declared) > nov["max_clusters_per_post"]:
        errors.append(f"clusters: максимум {nov['max_clusters_per_post']}")
    strong = strong_clusters(title, body, cfg)
    missing = [c for c in strong if c not in declared]
    if missing:
        warnings.append(f"по тексту пост также про {missing} — они попадут в историю")
    topic_clusters = sorted(set(declared) | set(strong))
    blocked = blocked_clusters(history, cfg, today)
    for c in topic_clusters:
        if c in blocked:
            errors.append(f"тема на паузе — {blocked[c]}")

    if any(h.get("topic_id") == d["topic_id"] for h in recent(history, today, nov["topic_id_cooldown_days"])):
        errors.append(f"topic_id {d['topic_id']} уже был за {nov['topic_id_cooldown_days']} дней")

    ent_window = recent(history, today, nov["entity_cooldown_days"])
    for ent in d.get("entities") or []:
        ne = norm(ent)
        if len(ne) < 4:
            continue
        for h in ent_window:
            if ne in [norm(x) for x in h.get("entities") or []] or ne in norm(h.get("title", "")):
                errors.append(f"«{ent}» уже было {h.get('date')} («{h.get('title', '')[:50]}») — пауза {nov['entity_cooldown_days']} дн.")
                break

    last = history[-12:]
    last_formats = [h.get("format") for h in last if h.get("format")][-nov["format_not_in_last_posts"]:]
    if fmt_id in last_formats:
        errors.append(f"формат {fmt_id} был в последних {nov['format_not_in_last_posts']} постах — выбери другой из рубрики")
    last_pillars = [h.get("pillar") for h in last if h.get("pillar")][-nov["pillar_not_in_last_posts"]:]
    if pillar_id in last_pillars and pillar_id == expected_pillar and last and last[-1].get("date") == today.isoformat():
        errors.append("сегодня уже был пост этой рубрики")
    fw = first_word(title)
    recent_titles = [h.get("title", "") for h in history if h.get("title")]
    if fw and fw in {first_word(t) for t in recent_titles[-nov["title_first_word_not_in_last_posts"]:]}:
        errors.append(f"заголовок начинается с «{fw}», как один из последних {nov['title_first_word_not_in_last_posts']} — начни иначе")
    ow = opening_words(paras[0] if paras else "")
    if ow and ow in {opening_words(h.get("text", "")) for h in history[-15:]}:
        errors.append(f"первый абзац начинается так же, как недавний пост: «{ow}»")

    try:
        from telegram_similarity import similarity_score
    except Exception:
        similarity_score = None
    full = f"{title}. {body}"
    for h in history[-nov["similarity_window_posts"]:]:
        other = f"{h.get('title', '')}. {h.get('text', '')}"
        if similarity_score and h.get("text"):
            score = similarity_score(full, other)
            if score >= nov["similarity_threshold"]:
                errors.append(f"слишком похоже на пост {h.get('date')} «{h.get('title', '')[:50]}» (score={score:.2f})")
        if h.get("title") and SequenceMatcher(None, norm(title), norm(h["title"])).ratio() >= 0.62:
            errors.append(f"заголовок похож на «{h['title'][:60]}» ({h.get('date')})")

    src_errors, src_warnings, _ = verify_sources(d, today, pillar, offline)
    errors += src_errors
    warnings += src_warnings

    img = d.get("image") or {}
    if img.get("kind") not in ("city", "event", "apartment"):
        errors.append("image.kind: city | event | apartment")
    if not (img.get("scene") or "").strip():
        errors.append("image.scene: опиши сцену (по-английски)")
    if img.get("kind") == "apartment" and pillar_id not in ("guest_life",):
        warnings.append("картинка-квартира в городской рубрике — лучше реальное фото места из источника")

    caption = render_caption(d, cfg, history)
    visible = len(html_to_text(caption))
    if visible > 1000:
        errors.append(f"подпись {visible} симв. > 1000 (лимит Telegram 1024) — сократи текст")

    # уникальные, по порядку
    errors = list(dict.fromkeys(errors))
    warnings = list(dict.fromkeys(warnings))
    return {"ok": not errors, "errors": errors, "warnings": warnings, "clusters": topic_clusters,
            "caption_chars": visible}


# ───────────────────────── рендер ─────────────────────────

KEYCAPS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]


def pick_cta(cfg: dict, history: list[dict], forced: str = "") -> dict:
    variants = cfg["cta_variants"]
    if forced:
        for v in variants:
            if v["id"] == forced:
                return v
    used = [h.get("cta_id") for h in history if h.get("cta_id")]
    for v in variants:
        if v["id"] not in used:
            return v
    last_idx = {v["id"]: max(i for i, u in enumerate(used) if u == v["id"]) for v in variants}
    return min(variants, key=lambda v: last_idx[v["id"]])


def render_caption(d: dict, cfg: dict, history: list[dict] | None = None) -> str:
    esc = lambda s: html.escape((s or "").strip(), quote=False)
    history = history if history is not None else []
    parts = [f"<b>{esc(d.get('title'))}</b>"]
    for p in d.get("paragraphs") or []:
        if p and p.strip():
            parts.append(esc(p))
    items = [i for i in d.get("list_items") or [] if i and i.strip()]
    if items:
        parts.append("\n".join(f"{KEYCAPS[i]} {esc(it)}" for i, it in enumerate(items[:5])))
    if (d.get("question") or "").strip():
        parts.append(f"<i>{esc(d['question'])}</i>")
    cta = pick_cta(cfg, history, d.get("cta", ""))
    parts.append(cta["html"].format(**cfg["links"]))
    return "\n\n".join(parts)


def render_buttons(cfg: dict) -> dict:
    rows = []
    for row in cfg["buttons"]:
        rows.append([{"text": b["text"], "url": b["url"].format(**cfg["links"])} for b in row])
    return {"inline_keyboard": rows}


# ───────────────────────── картинка ─────────────────────────

def build_image_prompt(d: dict, has_reference: bool) -> str:
    img = d.get("image") or {}
    headline = d.get("image_headline", "").strip()
    scene = img.get("scene", "").strip()
    try:
        from image_prompt_builder import LOGO_COMPOSITE_RULE
    except Exception:
        LOGO_COMPOSITE_RULE = "Reference image 1 is the brand logo: paste it unchanged in the upper-right corner."
    ref_rule = (
        "Reference image 2 is a REAL photo of the actual place. Keep the real place, architecture, "
        "layout and key details recognizable; only improve light, color and composition naturally. "
        "Do not invent landmarks, do not add skyscrapers or luxury elements that are not in the reference. "
        if has_reference else
        "Create a realistic documentary photo of a real place in Tyumen, Russia (Siberian city, "
        "mix of historic brick and modern mid-rise buildings). No fantasy, no luxury exaggeration. "
    )
    return (
        "Square 1:1 editorial photo for a Telegram post of a Tyumen apartment rental brand. "
        f"{LOGO_COMPOSITE_RULE} "
        f"{ref_rule}"
        f"Scene: {scene}. "
        "Photorealistic, natural daylight or real evening light, true-to-life colors, looks like a good smartphone "
        "or DSLR photo, not an illustration, no 3D render look, no people faces close-up. "
        f"Typography: one short bold Cyrillic headline «{headline}» in clean white sans-serif with a soft dark "
        "gradient behind it at the bottom; spell every Cyrillic letter exactly as given; no other text, no watermarks."
    )


def choose_reference(d: dict, cfg: dict, pages: list[dict] | None = None) -> str:
    img = d.get("image") or {}
    candidates = []
    if img.get("reference_url"):
        candidates.append(img["reference_url"])
    for p in pages or []:
        if p.get("og_image"):
            candidates.append(p["og_image"])
    if img.get("kind") == "apartment":
        candidates += cfg.get("site_photos", [])
    for c in candidates:
        if is_image_url(c):
            return c
    return ""


def make_image(d: dict, cfg: dict, pages: list[dict] | None = None) -> tuple[str, str, str]:
    """→ (image_url, reference_url, способ)"""
    from generate_telegram_post import generate_image_grsai
    tenant = json.loads((ROOT / "shared" / "tenant-config.json").read_text(encoding="utf-8"))
    logo = tenant.get("brand_logo_url", "")
    ref = choose_reference(d, cfg, pages)
    prompt = build_image_prompt(d, bool(ref))
    inputs = [u for u in (logo, ref) if u]
    last_err = ""
    for attempt in range(3):
        try:
            url = generate_image_grsai(prompt, input_urls=inputs)
            if url:
                return url, ref, "generated"
        except Exception as e:
            last_err = str(e)
            print(f"  генерация картинки, попытка {attempt + 1}: {last_err[:200]}")
            time.sleep(5 * (attempt + 1))
    if ref:
        return ref, ref, "reference_photo"
    raise RuntimeError(f"картинку сделать не удалось: {last_err}")


# ───────────────────────── память ─────────────────────────

def record_published(d: dict, cfg: dict, caption: str, message_id, image_url: str,
                     clusters: list[str], cta_id: str) -> dict:
    POSTS_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "date": d["date"],
        "published_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
        "message_id": message_id,
        "pillar": d["pillar"],
        "format": d["format"],
        "topic_id": d["topic_id"],
        "title": d["title"],
        "clusters": clusters,
        "entities": d.get("entities") or [],
        "event_date": d.get("event_date", ""),
        "sources": [s.get("url") for s in d.get("sources") or [] if isinstance(s, dict)],
        "cta_id": cta_id,
        "image_url": image_url,
        "text": html_to_text(caption),
    }
    data = load_json_list(PUBLISHED_PATH)
    data.append(entry)
    PUBLISHED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        from telegram_post_history import record_publication
        record_publication(d["topic_id"], category_id=d["pillar"], title=d["title"], text_html=caption,
                           entities=d.get("entities") or [], event_date=d.get("event_date", ""))
    except Exception as e:
        print(f"  ledger.json не обновлён: {e}")
    return entry


def _entry_key(e) -> str:
    if not isinstance(e, dict):
        return json.dumps(e, ensure_ascii=False, sort_keys=True)
    if e.get("message_id"):
        return f"m{e['message_id']}"
    return f"{e.get('id') or e.get('topic_id', '')}|{e.get('published_at') or e.get('date', '')}"


def merge_lists(remote: list, local: list) -> list:
    out, seen = [], set()
    for e in remote + local:
        k = _entry_key(e)
        if k in seen:
            continue
        seen.add(k)
        out.append(e)
    out.sort(key=lambda e: (e.get("published_at") or e.get("date") or "") if isinstance(e, dict) else "")
    return out


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True)


def sync_memory_to_main(message: str) -> bool:
    """Кладёт память публикаций прямо в origin/main, не трогая текущую ветку.
    Без этого следующий ежедневный запуск (он стартует от main) не видит, что уже вышло, — и повторяет темы."""
    rel_lists = ["memory/telegram_posts/published.json", "memory/telegram_posts/ledger.json",
                 "memory/telegram_posts/history.json"]
    for attempt in range(5):
        fetch = _git(["fetch", "origin", "main"], ROOT)
        if fetch.returncode != 0:
            print(f"  git fetch: {fetch.stderr.strip()[:200]}")
            time.sleep(4 * 2 ** attempt)
            continue
        tmp = Path(tempfile.mkdtemp(prefix="tg-memory-"))
        try:
            wt = _git(["worktree", "add", "--detach", str(tmp), "origin/main"], ROOT)
            if wt.returncode != 0:
                print(f"  git worktree: {wt.stderr.strip()[:200]}")
                return False
            for rel in rel_lists:
                local = load_json_list(ROOT / rel)
                if not local:
                    continue
                target = tmp / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                merged = merge_lists(load_json_list(target), local)
                target.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
            if DRAFTS_DIR.exists():
                dst = tmp / "memory" / "telegram_posts" / "drafts"
                dst.mkdir(parents=True, exist_ok=True)
                for f in DRAFTS_DIR.glob("*.json"):
                    if not (dst / f.name).exists():
                        shutil.copy2(f, dst / f.name)
            _git(["add", "memory/telegram_posts"], tmp)
            if _git(["diff", "--cached", "--quiet"], tmp).returncode == 0:
                print("  память в main уже актуальна")
                return True
            commit = _git(["commit", "-m", message], tmp)
            if commit.returncode != 0:
                print(f"  git commit: {commit.stderr.strip()[:200]}")
                return False
            push = _git(["push", "origin", "HEAD:main"], tmp)
            if push.returncode == 0:
                print("  память публикаций записана в main")
                return True
            print(f"  git push (попытка {attempt + 1}): {push.stderr.strip()[:200]}")
        finally:
            _git(["worktree", "remove", "--force", str(tmp)], ROOT)
            shutil.rmtree(tmp, ignore_errors=True)
        time.sleep(4 * 2 ** attempt)
    return False


# ───────────────────────── команды ─────────────────────────

def load_draft(path: str) -> dict:
    p = Path(path)
    if not p.is_absolute():
        p = ROOT / p
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def print_report(res: dict) -> None:
    if res["ok"]:
        print("PASS — черновик готов к публикации")
    else:
        print("FAIL — исправь и запусти validate снова:")
        for e in res["errors"]:
            print(f"  ✗ {e}")
    for w in res.get("warnings", []):
        print(f"  ! {w}")


def cmd_plan(args) -> int:
    cfg = load_config()
    today = date.fromisoformat(args.date) if args.date else today_local(cfg)
    plan = build_plan(cfg, today)
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    (DRAFTS_DIR / f"{today.isoformat()}.brief.json").write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(plan, ensure_ascii=False, indent=2))
    return 0


def cmd_fetch(args) -> int:
    page = fetch_page(args.url)
    out = {k: page[k] for k in ("url", "final_url", "status", "title", "og_image", "published")}
    out["og_image_ok"] = is_image_url(page["og_image"]) if page["og_image"] else False
    text = page["text"]
    if args.find:
        hits = []
        for q in args.find:
            i = norm(text).find(norm(q))
            hits.append({"query": q, "found": i >= 0, "context": text[max(0, i - 120): i + 200] if i >= 0 else ""})
        out["find"] = hits
    out["text"] = text[: args.chars]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0 if page["ok"] else 1


def cmd_validate(args) -> int:
    cfg = load_config()
    d = load_draft(args.draft)
    today = date.fromisoformat(args.date) if args.date else today_local(cfg)
    res = validate_draft(d, cfg, today, offline=args.offline)
    print_report(res)
    if res["ok"]:
        print("\n--- предпросмотр подписи ---\n")
        print(render_caption(d, cfg, load_history(cfg, include_channel=False)))
    return 0 if res["ok"] else 1


def cmd_render(args) -> int:
    cfg = load_config()
    print(render_caption(load_draft(args.draft), cfg, load_history(cfg, include_channel=False)))
    return 0


def cmd_history(args) -> int:
    cfg = load_config()
    today = today_local(cfg)
    for h in load_history(cfg)[-args.limit:]:
        print(f"{h.get('date', '?'):10} [{h.get('source', ''):9}] {h.get('pillar', '') or '-':12} {','.join(h.get('clusters') or []) or '-':28} {h.get('title', '')[:70]}")
    print("\nНа паузе:")
    for c, why in blocked_clusters(load_history(cfg), cfg, today).items():
        print(f"  {c}: {why}")
    return 0


def cmd_publish(args) -> int:
    cfg = load_config()
    d = load_draft(args.draft)
    today = date.fromisoformat(args.date) if args.date else today_local(cfg)
    history = load_history(cfg)
    res = validate_draft(d, cfg, today, history=history)
    print_report(res)
    if not res["ok"]:
        return 1
    pillar = cfg["pillars"][d["pillar"]]
    _, _, pages = verify_sources(d, today, pillar, offline=False)
    caption = render_caption(d, cfg, history)
    cta = pick_cta(cfg, history, d.get("cta", ""))
    image_url, ref, how = "", "", "text_only"
    if args.image_url:
        if not is_image_url(args.image_url):
            print(f"--image-url не открывается как картинка: {args.image_url}")
            return 1
        image_url, how = args.image_url, "preapproved"
    elif not args.no_image:
        print("Готовлю картинку…")
        image_url, ref, how = make_image(d, cfg, pages)
        print(f"  картинка ({how}): {image_url}")
    if args.dry_run:
        print("\n--- DRY RUN, не публикую ---\n")
        print(caption)
        return 0
    from generate_telegram_post import send_to_telegram
    from telegram_credentials import load_telegram_credentials
    creds = load_telegram_credentials()
    if not creds.get("bot_token") or not creds.get("chat_id"):
        print("Нет TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (Cursor Dashboard → Cloud Agents → Secrets)")
        return 2
    resp = send_to_telegram(creds["bot_token"], creds["chat_id"], caption, reply_markup=render_buttons(cfg),
                            photo_url=image_url or None, silent=True)
    if not resp.get("ok"):
        print(f"Telegram отказал: {resp}")
        return 3
    msg_id = resp["result"]["message_id"]
    print(f"Опубликовано: message_id={msg_id}")
    d.setdefault("_published", {}).update({"message_id": msg_id, "image_url": image_url, "image_mode": how, "reference": ref})
    draft_path = Path(args.draft) if Path(args.draft).is_absolute() else ROOT / args.draft
    draft_path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    record_published(d, cfg, caption, msg_id, image_url, res["clusters"], cta["id"])
    if not args.no_sync:
        if not sync_memory_to_main(f"Telegram: память публикации {d['date']} — {d['title'][:60]}"):
            print("ВНИМАНИЕ: память не попала в main. Выполни: python3 scripts/tg_editorial.py sync-memory")
            return 4
    return 0


def cmd_sync(args) -> int:
    return 0 if sync_memory_to_main(args.message or "Telegram: синхронизация памяти публикаций") else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Редакционная система Telegram «Добрый дом»")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("plan", help="бриф на сегодня")
    p.add_argument("--date")
    p.set_defaults(fn=cmd_plan)
    p = sub.add_parser("fetch", help="открыть источник: заголовок, og:image, дата, текст")
    p.add_argument("url")
    p.add_argument("--find", nargs="*", help="проверить, что фразы есть на странице")
    p.add_argument("--chars", type=int, default=2500)
    p.set_defaults(fn=cmd_fetch)
    p = sub.add_parser("validate", help="проверить черновик")
    p.add_argument("draft")
    p.add_argument("--date")
    p.add_argument("--offline", action="store_true", help="без проверки источников по сети (только для тестов)")
    p.set_defaults(fn=cmd_validate)
    p = sub.add_parser("render", help="показать подпись")
    p.add_argument("draft")
    p.set_defaults(fn=cmd_render)
    p = sub.add_parser("history", help="последние посты и темы на паузе")
    p.add_argument("--limit", type=int, default=25)
    p.set_defaults(fn=cmd_history)
    p = sub.add_parser("publish", help="картинка + публикация + память в main")
    p.add_argument("draft")
    p.add_argument("--date")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--no-image", action="store_true", help="только если заказчик прямо попросил пост без картинки")
    p.add_argument("--no-sync", action="store_true")
    p.add_argument("--image-url", help="готовая картинка из предыдущего --dry-run (не генерировать заново)")
    p.set_defaults(fn=cmd_publish)
    p = sub.add_parser("sync-memory", help="записать память публикаций в main")
    p.add_argument("--message")
    p.set_defaults(fn=cmd_sync)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
