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
            "hook_type": e.get("hook_type", ""),
            "audience": e.get("audience", ""),
            "topic_seed": e.get("topic_seed", ""),
            "apartment_code": e.get("apartment_code", ""),
            "image_reference": e.get("image_reference", ""),
            "message_id": e.get("message_id"),
            "sources": e.get("sources") or [],
            "deleted": e.get("deleted", False),
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
    """14-дневный цикл рубрик: неделя A с anchor_monday, затем неделя B."""
    cyc = cfg["cycle"]
    anchor = date.fromisoformat(cyc["anchor_monday"])
    return cyc["days"][(today - anchor).days % len(cyc["days"])]


BLOG_INDEX_PATH = ROOT / "shared" / "tg-blog-index.json"
APARTMENTS_PATH = ROOT / "shared" / "tg-apartments.json"
TL_HOTEL_CODE = "25160"
TL_API = "https://ru-ibe.tlintegration.ru/ApiWebDistribution/BookingForm/hotel_info?hotels[0].code={code}&language=ru-ru"
APARTMENT_SITE = "https://добрыйдомтюмень.рф/booking/?room-type={code}"


def refresh_apartments() -> list[dict]:
    """Каталог всех квартир с реальными фото из TravelLine (то же, что на добрыйдомтюмень.рф)."""
    st, _, _, body = http_get(TL_API.format(code=TL_HOTEL_CODE), timeout=40, max_bytes=30_000_000)
    if st != 200 or not body:
        raise RuntimeError(f"TravelLine не ответил: HTTP {st}")
    hotel = json.loads(body)["hotels"][0]
    out = []
    for rt in hotel.get("room_types", []):
        name = re.sub(r"\s+", " ", rt.get("name", "")).strip()
        m = re.search(r"\(([^)]+)\)\s*$", name)
        desc = re.sub(r"[✅❗️🔹🔸⭐️]+", "", rt.get("description", "") or "")
        desc = re.sub(r"\n{2,}", "\n", desc).strip()
        out.append({
            "code": str(rt.get("code")),
            "name": name,
            "address": m.group(1).strip() if m else "",
            "size_m2": (rt.get("size") or {}).get("value"),
            "max_occupancy": rt.get("max_occupancy"),
            "amenities": [a.get("name") for a in rt.get("amenities") or [] if a.get("name")],
            "pets": next((a.get("description", "") for a in rt.get("amenities") or [] if a.get("kind") == "possible_with_pets"), ""),
            "description": desc[:1500],
            "images": [i["url"] for i in rt.get("images") or [] if i.get("url")],
            "url": APARTMENT_SITE.format(code=rt.get("code")),
        })
    APARTMENTS_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def load_apartments() -> list[dict]:
    return load_json_list(APARTMENTS_PATH)


def apartment_by_code(code: str) -> dict | None:
    return next((a for a in load_apartments() if a["code"] == str(code)), None)


def used_image_refs(history: list[dict]) -> set[str]:
    return {h.get("image_reference") for h in history if h.get("image_reference")}


def apartment_candidates(pillar_id: str, history: list[dict], today: date, n: int = 5) -> list[dict]:
    if os.environ.get("TG_OFFLINE") != "1":
        try:
            if not APARTMENTS_PATH.exists() or time.time() - APARTMENTS_PATH.stat().st_mtime > 7 * 86400:
                refresh_apartments()
        except Exception:
            pass
    apts = load_apartments()
    used = {h.get("apartment_code") for h in history if h.get("pillar") == pillar_id and h.get("apartment_code")}
    free = [a for a in apts if a["code"] not in used] or apts
    if not free:
        return []
    shift = (today.toordinal() * 3) % len(free)
    out = []
    for a in (free[shift:] + free[:shift])[:n]:
        out.append({k: a[k] for k in ("code", "name", "address", "size_m2", "max_occupancy", "amenities", "pets", "description", "url")}
                   | {"photos": a["images"][:8]})
    return out


def used_seed_ids(history: list[dict]) -> set[str]:
    return {h.get("topic_seed") for h in history if h.get("topic_seed")}


def used_source_urls(history: list[dict]) -> set[str]:
    out = set()
    for h in history:
        for u in h.get("sources") or []:
            out.add(to_ascii_url(u).rstrip("/"))
    return out


def seed_candidates(pillar_id: str, cfg: dict, history: list[dict], today: date, n: int = 5) -> list[dict]:
    seeds = cfg["pillars"][pillar_id].get("seeds") or []
    used = used_seed_ids(history)
    free = [s for s in seeds if s["id"] not in used and (not s.get("months") or today.month in s["months"])]
    if not free:
        return []
    # детерминированный сдвиг по дате — разные модели получают одинаковый список
    shift = today.toordinal() % len(free)
    return (free[shift:] + free[:shift])[:n]


BLOG_GUIDE_RE = r"гид|\bгде\b|как выбрать|как снять|районы|\bтоп\b|лучш|\bчто\b|\bкак\b|советы|почему|сравнен|\bили\b|обзор|цены на|стоимость|критери|шаг"
BLOG_STORY_RE = r"у двери|у подъезда|оплатил|перевел|сняли|снял |приехали|приехал|попросили|написали|в фильтре|в карточке|в чате|в объявлении|на фото"


def blog_kind(title: str) -> str:
    """story — живая история гостя (сцена, деньги, что сломалось); guide — справочная статья."""
    tl = title.lower().replace("ё", "е")
    if re.search(BLOG_STORY_RE, tl) and "." in title.rstrip("."):
        return "story"
    storyish = "." in title.rstrip(".") or "₽" in title
    return "story" if storyish and not re.search(BLOG_GUIDE_RE, tl) else "guide"


def load_blog_index() -> list[dict]:
    out = []
    for e in load_json_list(BLOG_INDEX_PATH):
        out.append(e if isinstance(e, dict) else {"url": e, "title": "", "kind": ""})
    return out


def refresh_blog_index(pages: int = 3) -> list[dict]:
    """Добавляет новые статьи с первых страниц блога (новые идут первыми)."""
    index = load_blog_index()
    known = {e["url"] for e in index}
    fresh: list[dict] = []
    for n in range(1, pages + 1):
        u = "https://добрыйдом-72.рф/blog/" + (f"page/{n}/" if n > 1 else "")
        st, _, ct, body = http_get(u, timeout=20)
        if st != 200 or not body:
            break
        for f in re.findall(r'href="(https://xn---72-9cdob8azaodt6k\.xn--p1ai/blog/[a-z0-9\-]+/)"', decode_body(body, ct)):
            if f not in known:
                known.add(f)
                title = fetch_page(f).get("title", "").split(" - Добрый дом")[0].strip()
                fresh.append({"url": f, "title": title, "kind": blog_kind(title)})
    if fresh:
        index = fresh + index
        BLOG_INDEX_PATH.write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    return index


def blog_candidates(history: list[dict], today: date, n: int = 5, kind: str = "story") -> list[dict]:
    index = load_blog_index()
    if os.environ.get("TG_OFFLINE") != "1":
        try:
            index = refresh_blog_index()
        except Exception:
            pass
    used = used_source_urls(history)
    free = [e for e in index if e["url"].rstrip("/") not in used and (not kind or e.get("kind") == kind)]
    if not free:
        free = [e for e in index if e["url"].rstrip("/") not in used]
    if not free:
        return []
    # свежие статьи блога — первыми, остальные по кругу
    head = free[:2]
    rest = free[2:]
    if rest:
        shift = (today.toordinal() * 7) % len(rest)
        rest = rest[shift:] + rest[:shift]
    return (head + rest)[:n]


def published_today(history: list[dict], today: date) -> list[dict]:
    return [h for h in history if h.get("source") == "published" and h.get("date") == today.isoformat() and not h.get("deleted")]


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
    topic_source = pillar.get("topic_source", "live")
    seeds_free = seed_candidates(pillar_id, cfg, history, today) if topic_source == "seeds" else []
    blog_free = blog_candidates(history, today, kind=pillar.get("blog_kind", "story")) if topic_source == "blog" else []
    apt_free = apartment_candidates(pillar_id, history, today) if topic_source == "apartments" else []
    tokens["seed"] = seeds_free[0]["topic"] if seeds_free else ""
    tokens["place"] = tokens["seed"]
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
        "topic_seed": "id темы из seed_candidates (seeds) | \"live\" (живые рубрики) | \"blog\" (истории из блога) | \"apartment\" (квартира недели)",
        "apartment_code": "код квартиры из каталога, если пост про нашу квартиру (иначе пусто)",
        "topic_id": "латиница_через_подчёркивание_уникально",
        "clusters": ["1–3 id из free_clusters, о чём пост на самом деле"],
        "hook_type": "один из hook_types (не как в прошлом посте)",
        "audience": "один из audiences — для кого пост",
        "stay_reason": "одной фразой: почему этот человек приедет/останется в Тюмени (для проверки, в текст не выводится)",
        "title": "Заголовок 18–80 символов: имя, число или «название» — конкретика, не общие слова",
        "paragraphs": ["2–3 абзаца прозой по 40–320 символов, каждый с новым; списков нет"],
        "question": "вопрос подписчикам (обязателен для fact_question, иначе пусто)",
        "entities": ["ключевые имена собственные: площадка, событие, артист, место"],
        "event_date": "YYYY-MM-DD ближайшего события или пусто",
        "sources": [{"url": "https://…", "published": "YYYY-MM-DD если это новость", "must_contain": ["точная фраза/название со страницы"]}],
        "image_headline": "надпись на картинке до 34 символов",
        "image": {"kind": "city|event|apartment", "reference_url": "реальное фото места (og:image из fetch) или пусто", "scene": "описание сцены по-английски, реалистично"},
    }
    last_hooks = [h.get("hook_type") for h in history if h.get("hook_type")][-2:]
    return {
        "brand_goal": cfg.get("brand_goal", ""),
        "date": today.isoformat(),
        "weekday": WEEKDAYS[today.weekday()],
        "hook_types": {k: v for k, v in cfg.get("hook_types", {}).items() if k not in last_hooks},
        "audiences": cfg.get("audiences", {}),
        "already_published_today": [h.get("title") for h in published_today(history, today)],
        "pillar": pillar_id,
        "pillar_name": pillar["name"],
        "goal": pillar["goal"],
        "how_to_write": pillar.get("how_to_write", ""),
        "topic_source": topic_source,
        "seed_candidates": seeds_free,
        "blog_candidates": blog_free,
        "apartment_candidates": apt_free,
        "apartment_photos_rule": "Если пост про нашу квартиру (в любой рубрике): apartment_code из каталога (python3 scripts/tg_editorial.py apartments), image.kind=apartment, image.reference_url — самое красивое фото ЭТОЙ квартиры из каталога (посмотри: python3 scripts/tg_editorial.py apartment <code> --download 8). Одно фото — один раз.",
        "fact_policy": pillar.get("fact_policy", "web"),
        "brand_facts": cfg.get("brand_facts", {}),
        "rubric_past_titles": [h.get("title") for h in history if h.get("pillar") == pillar_id][-30:],
        "allowed_formats": {f: cfg["formats"][f] for f in formats},
        "fresh_source_required": pillar.get("fresh_source_required", False),
        "event_window_days": pillar.get("event_window_days", 0),
        "news_max_age_days": pillar.get("news_max_age_days"),
        "search_queries": [re.sub(r"(Тюмен\w*.*?)\s+Тюмень\b", r"\1", q.format_map(tokens)) for q in pillar.get("queries", [])],
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
            "0. Если already_published_today не пуст — сегодня пост уже вышел: ничего не публикуй, заверши работу.",
            "1. Тема: seeds → возьми ПЕРВУЮ подходящую из seed_candidates (topic_seed = её id); blog → одну статью из blog_candidates (topic_seed = \"blog\"); apartments → одну квартиру из apartment_candidates (topic_seed = \"apartment\", apartment_code = её code); live → найди свежее событие/новость по search_queries (topic_seed = \"live\").",
            "1.1 Картинка: если пост про нашу квартиру — только реальное фото этой квартиры из каталога (apartment_photos_rule). Скачай 6–8 фото, посмотри и выбери самое светлое и красивое.",
            "2. Факты: о «Добром доме» — только brand_facts (источник — сайт); о городе и рынке — WebSearch + python3 scripts/tg_editorial.py fetch <url> --find \"<фраза>\".",
            "3. Пиши по how_to_write и writing_rules: 2–3 абзаца прозой, без списков, короткими живыми предложениями. Не повторяй rubric_past_titles.",
            f"4. Запиши черновик в {draft_path.relative_to(ROOT)} строго по draft_template.",
            f"5. python3 scripts/tg_editorial.py validate {draft_path.relative_to(ROOT)} — чини ошибки, пока не будет PASS (при тупике — следующая тема из кандидатов).",
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


def check_style(body: str, cfg: dict) -> list[str]:
    """Живой язык: короткие предложения, без простыней."""
    lim = cfg["limits"]
    errors = []
    sents = [s for s in re.split(r"(?<=[.!?…])\s+|\n+", body) if len(words(s)) >= 3]
    if not sents:
        return errors
    lens = [len(words(s)) for s in sents]
    long = [s for s, n in zip(sents, lens) if n > lim.get("sentence_words_max", 32)]
    if long:
        errors.append(f"слишком длинное предложение ({len(words(long[0]))} слов): «{long[0][:70]}…» — разбей")
    avg = sum(lens) / len(lens)
    if avg > lim.get("avg_sentence_words_max", 20):
        errors.append(f"в среднем {avg:.0f} слов в предложении — пиши короче, как говорят люди")
    return errors


def check_brand_value(d: dict, cfg: dict, title: str, paras: list[str], body: str, history: list[dict],
                      pillar: dict | None = None) -> list[str]:
    """Пост должен цеплять и работать на бренд, а не быть городской сводкой для местных."""
    pillar = pillar or {}
    errors = []
    lim = cfg["limits"]
    hooks = cfg.get("hook_types", {})
    auds = cfg.get("audiences", {})
    if d.get("hook_type") not in hooks:
        errors.append(f"hook_type обязателен, один из {list(hooks)}")
    else:
        last_hooks = [h.get("hook_type") for h in history if h.get("hook_type") and not h.get("deleted")][-2:]
        if d["hook_type"] in last_hooks:
            errors.append(f"крючок {d['hook_type']} был в последних 2 постах — зайди по-другому")
    if d.get("audience") not in auds:
        errors.append(f"audience обязателен, один из {list(auds)}")
    if pillar.get("stay_link_required"):
        if len((d.get("stay_reason") or "").strip()) < lim.get("stay_reason_min", 25):
            errors.append("stay_reason: одной фразой — почему человек приедет или останется в Тюмени")
        plain = norm(body)
        if not any(norm(k) in plain for k in cfg.get("stay_link_keywords", [])):
            errors.append("в тексте нет связи с приездом/проживанием: одна живая фраза, зачем приехать или остаться на ночь")
    local = set(cfg.get("local_only_clusters", []))
    hit_local = [c for c in strong_clusters(title, body, cfg) if c in local] + [c for c in d.get("clusters") or [] if c in local]
    if hit_local:
        names = sorted({cfg["clusters"][c]["name"] for c in hit_local})
        errors.append(f"тема для местных, а не для гостей ({', '.join(names)}) — такой пост не даёт повода приехать")
    if paras and len(paras[0]) > lim.get("first_paragraph_max", 220):
        errors.append(f"первый абзац {len(paras[0])} симв. — крючок должен уложиться в {lim.get('first_paragraph_max', 220)}")
    t_words = title.split()
    concrete = bool(re.search(r"\d", title)) or "«" in title or any(w[:1].isupper() for w in t_words[1:])
    if not concrete:
        errors.append("заголовок без конкретики: добавь число, имя или «название»")
    return errors


def check_topic_seed(d: dict, cfg: dict, history: list[dict], pillar_id: str, today: date | None = None) -> list[str]:
    """Темы внутри рубрики не повторяются никогда: каждая тема из запаса — один раз."""
    pillar = cfg["pillars"][pillar_id]
    src = pillar.get("topic_source", "live")
    seed = d.get("topic_seed", "")
    errors = []
    if src == "seeds":
        ids = {s["id"] for s in pillar.get("seeds") or []}
        used = used_seed_ids(history)
        if seed == "new":
            if seed_candidates(pillar_id, cfg, history, today or today_local(cfg)):
                errors.append("topic_seed=new разрешён только когда запас тем рубрики закончился — возьми тему из seed_candidates")
            if len((d.get("new_topic_reason") or "")) < 20:
                errors.append("для новой темы нужен new_topic_reason")
        elif seed not in ids:
            errors.append(f"topic_seed {seed!r} не из запаса рубрики {pillar_id}")
        elif seed in used:
            errors.append(f"тема {seed} уже была в этой рубрике — возьми другую из seed_candidates")
    elif src == "blog":
        if seed != "blog":
            errors.append("для историй из блога topic_seed = \"blog\"")
        used_urls = used_source_urls(history)
        for s in d.get("sources") or []:
            if isinstance(s, dict) and "/blog/" in to_ascii_url(s.get("url", "")) and to_ascii_url(s["url"]).rstrip("/") in used_urls:
                errors.append(f"статья {s['url']} уже была пересказана — возьми другую из blog_candidates")
    elif src == "apartments":
        if seed != "apartment":
            errors.append("для «Квартиры недели» topic_seed = \"apartment\"")
        code = str(d.get("apartment_code") or "")
        if not apartment_by_code(code):
            errors.append("apartment_code не найден в каталоге — возьми из apartment_candidates")
        elif any(h.get("pillar") == pillar_id and str(h.get("apartment_code")) == code for h in history) and \
                len({h.get("apartment_code") for h in history if h.get("pillar") == pillar_id}) < len(load_apartments()):
            errors.append(f"квартира {code} уже была в этой рубрике — возьми другую из apartment_candidates")
    elif seed != "live":
        errors.append("для живой рубрики topic_seed = \"live\"")
    rubric_hist = [h for h in history if h.get("pillar") == pillar_id and h.get("text")]
    try:
        from telegram_similarity import similarity_score
        full = d.get("title", "") + ". " + draft_body_text(d)
        thr = cfg["novelty"].get("rubric_similarity_threshold", 0.33)
        for h in rubric_hist:
            sc = similarity_score(full, f"{h.get('title', '')}. {h.get('text', '')}")
            if sc >= thr:
                errors.append(f"в рубрике уже был похожий пост {h.get('date')} «{h.get('title', '')[:50]}» (score={sc:.2f})")
    except Exception:
        pass
    return errors


def check_apartment_image(d: dict, history: list[dict]) -> list[str]:
    """Про нашу квартиру — только её реальные фото из каталога, каждое фото один раз."""
    errors = []
    img = d.get("image") or {}
    code = str(d.get("apartment_code") or "")
    if img.get("kind") == "apartment" or code:
        apt = apartment_by_code(code) if code else None
        if not apt:
            errors.append("пост про нашу квартиру: укажи apartment_code из каталога (python3 scripts/tg_editorial.py apartments)")
            return errors
        ref = img.get("reference_url", "")
        if img.get("kind") != "apartment":
            errors.append("пост про квартиру: image.kind = apartment")
        if ref not in apt["images"]:
            errors.append(f"image.reference_url должен быть реальным фото квартиры {code} из каталога (apartment {code} --download 8)")
        elif ref in used_image_refs(history):
            errors.append("это фото уже было в прошлых постах — выбери другое фото этой квартиры")
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
    policy = pillar.get("fact_policy", "web")
    if policy == "none" and not sources:
        return errors, warnings, pages
    external = [s for s in sources if isinstance(s, dict) and s.get("url") and not any(m in to_ascii_url(s["url"]) for m in OWN_SITE_MARKERS)]
    if policy in ("web",) and pillar.get("fresh_source_required") and not external:
        errors.append("нужен хотя бы один внешний источник (не сайт «Доброго дома»)")
    if policy == "blog" and not any("/blog/" in to_ascii_url(s.get("url", "")) for s in sources if isinstance(s, dict)):
        errors.append("история должна опираться на статью блога: sources[].url = https://добрыйдом-72.рф/blog/…")
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
        rt = re.search(r"room-type=(\d+)", s["url"])
        if rt:
            apt = apartment_by_code(rt.group(1))
            blob = norm(json.dumps(apt, ensure_ascii=False)) if apt else ""
            if apt and any(norm(m) in blob for m in s.get("must_contain", [])):
                verified += 1
            else:
                warnings.append(f"в каталоге квартиры {rt.group(1)} не нашлось фраз {s.get('must_contain')}")
            continue
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

    policy = cfg["pillars"].get(d.get("pillar", ""), {}).get("fact_policy", "web")
    required = ["date", "pillar", "format", "topic_id", "topic_seed", "title", "paragraphs", "image_headline", "image"]
    if policy != "none":
        required.append("sources")
    for key in required:
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
        errors.append("списки и пункты запрещены — пиши прозой" if lim["list_items_max"] == 0 else f"пунктов {len(items)}, максимум {lim['list_items_max']}")
    for i, it in enumerate(items, 1):
        if len(it) > lim["list_item_max"]:
            errors.append(f"пункт {i}: {len(it)} симв., максимум {lim['list_item_max']}")
    if fmt.get("needs_list") and len(items) < fmt.get("list_min", 2):
        errors.append(f"формат {fmt_id} требует список минимум из {fmt.get('list_min', 2)} пунктов")
    if not fmt.get("needs_list") and items:
        warnings.append(f"формат {fmt_id} обычно без списка")
    if fmt.get("needs_question") and not question.endswith("?"):
        errors.append(f"формат {fmt_id} требует question с «?» в конце")
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

    errors += check_brand_value(d, cfg, title, paras, body, history, pillar)
    errors += check_style(body, cfg)
    errors += check_topic_seed(d, cfg, history, pillar_id, today)
    if published_today(history, today) and not d.get("_published"):
        errors.append("сегодня пост уже опубликован — второй пост в день не выпускаем")

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
        elif pillar.get("min_event_lead_days") and ev < today + timedelta(days=pillar["min_event_lead_days"]):
            errors.append(f"до события меньше {pillar['min_event_lead_days']} дн. — приезжий не успеет спланировать поездку, возьми событие позже")
    elif fmt_id == "big_event" or (pillar.get("event_window_days") and pillar.get("topic_source") == "live" and not pillar.get("event_optional") and pillar.get("fact_policy") == "web" and not pillar.get("news_max_age_days")):
        errors.append("для события нужен event_date")

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

    last = [h for h in history if not h.get("deleted")][-12:]
    last_formats = [h.get("format") for h in last if h.get("format")][-nov["format_not_in_last_posts"]:]
    if fmt_id in last_formats and any(f not in last_formats for f in pillar["formats"]):
        errors.append(f"формат {fmt_id} был в последних {nov['format_not_in_last_posts']} постах — выбери другой из рубрики")
    last_pillars = [h.get("pillar") for h in last if h.get("pillar")][-nov["pillar_not_in_last_posts"]:]
    fw = first_word(title)
    recent_titles = [h.get("title", "") for h in history if h.get("title") and not h.get("deleted")]
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
    errors += check_apartment_image(d, history)
    if img.get("kind") not in ("city", "event", "apartment"):
        errors.append("image.kind: city | event | apartment")
    if not (img.get("scene") or "").strip():
        errors.append("image.scene: опиши сцену (по-английски)")

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


def pick_cta(cfg: dict, history: list[dict], forced: str = "", kind: str = "guest") -> dict:
    all_variants = cfg["cta_variants"]
    if forced:
        for v in all_variants:
            if v["id"] == forced:
                return v
    variants = [v for v in all_variants if kind == "any" or v.get("kind", "guest") == kind] or all_variants
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
    paras = [esc(p) for p in d.get("paragraphs") or [] if p and p.strip()]
    items = [i for i in d.get("list_items") or [] if i and i.strip()]
    # со списком: крючок → пункты → вывод
    parts += paras[:1]
    if items:
        parts.append("\n".join(f"{KEYCAPS[i]} {esc(it)}" for i, it in enumerate(items[:5])))
    parts += paras[1:]
    if (d.get("question") or "").strip():
        parts.append(f"<i>{esc(d['question'])}</i>")
    cta = pick_cta(cfg, history, d.get("cta", ""), cfg["pillars"].get(d.get("pillar", ""), {}).get("cta", "guest"))
    apt = apartment_by_code(d["apartment_code"]) if d.get("apartment_code") else None
    # ссылка на конкретную квартиру — только если пост про неё, а не фото фоном
    if apt and (d.get("topic_seed") == "apartment" or d.get("cta") == "apartment"):
        parts.append(f"Эта квартира, фото и свободные даты — <a href=\"{apt['url']}\">на сайте</a>. "
                     f"Все наши квартиры в Тюмени — <a href=\"{cfg['links']['catalog']}\">здесь</a>.")
    else:
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
    if img.get("kind") == "apartment" and has_reference:
        ref_rule = (
            "Reference image 2 is a REAL photo of our actual rental apartment in Tyumen. Keep this exact room: "
            "same layout, furniture, textiles, colors, windows, decor and camera angle. Do NOT add, remove or replace "
            "any objects, do not make it bigger or more luxurious. Only improve light, white balance, sharpness and "
            "straighten verticals, like a professional real-estate photographer's retouch. "
        )
    else:
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
    if img.get("kind") == "apartment":
        apt = apartment_by_code(d.get("apartment_code", "")) if d.get("apartment_code") else None
        candidates += (apt or {}).get("images", [])[:5] or cfg.get("site_photos", [])
    else:
        for p in pages or []:
            if p.get("og_image"):
                candidates.append(p["og_image"])
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
    base = "gpt" + "-image-2"
    models = [os.environ.get("TG_IMAGE_MODEL") or base + ".5-flare", base]
    for attempt in range(3):
        model = models[min(attempt, len(models) - 1)]
        try:
            url = generate_image_grsai(prompt, input_urls=inputs, model=model)
            if url:
                return url, ref, "generated"
        except Exception as e:
            last_err = str(e)
            print(f"  генерация картинки ({model}), попытка {attempt + 1}: {last_err[:200]}")
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
        "hook_type": d.get("hook_type", ""),
        "audience": d.get("audience", ""),
        "topic_seed": d.get("topic_seed", ""),
        "apartment_code": d.get("apartment_code", ""),
        "image_reference": (d.get("image") or {}).get("reference_url", ""),
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
    """Объединение по ключу; локальная версия записи главнее (например, пометка deleted)."""
    merged: dict[str, object] = {}
    for e in remote + local:
        merged[_entry_key(e)] = e
    out = list(merged.values())
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
    if args.replace:
        for h in history:
            if h.get("message_id") == args.replace:
                h["deleted"] = True
    res = validate_draft(d, cfg, today, history=history)
    print_report(res)
    if not res["ok"]:
        return 1
    pillar = cfg["pillars"][d["pillar"]]
    _, _, pages = verify_sources(d, today, pillar, offline=False)
    caption = render_caption(d, cfg, history)
    cta = pick_cta(cfg, history, d.get("cta", ""), cfg["pillars"].get(d.get("pillar", ""), {}).get("cta", "guest"))
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
    if args.replace:
        delete_message(creds, args.replace)
    if not args.no_sync:
        if not sync_memory_to_main(f"Telegram: память публикации {d['date']} — {d['title'][:60]}"):
            print("ВНИМАНИЕ: память не попала в main. Выполни: python3 scripts/tg_editorial.py sync-memory")
            return 4
    return 0


def cmd_apartments(args) -> int:
    apts = refresh_apartments() if args.refresh or not load_apartments() else load_apartments()
    for a in apts:
        print(f"{a['code']:>7}  {len(a['images']):>2} фото  {a.get('size_m2') or '?':>3} м²  до {a.get('max_occupancy') or '?'} гостей  {a['name']}")
    print(f"\nВсего квартир: {len(apts)}. Подробно и фото: python3 scripts/tg_editorial.py apartment <code> --download 8")
    return 0


def cmd_apartment(args) -> int:
    apt = apartment_by_code(args.code)
    if not apt:
        print("Нет такой квартиры в каталоге (обнови: apartments --refresh)")
        return 1
    print(json.dumps({k: v for k, v in apt.items() if k != "images"}, ensure_ascii=False, indent=2))
    print("\nФото (выбери самое светлое и красивое для image.reference_url):")
    folder = Path(tempfile.gettempdir()) / "tg-photos" / apt["code"]
    if args.download:
        folder.mkdir(parents=True, exist_ok=True)
    for i, u in enumerate(apt["images"], 1):
        line = f"  {i:>2}. {u}"
        if args.download and i <= args.download:
            st, _, _, body = http_get(u, timeout=30, max_bytes=15_000_000)
            if st == 200 and body:
                f = folder / f"{i:02d}.jpg"
                f.write_bytes(body)
                line += f"  → {f}"
        print(line)
    return 0


def delete_message(creds: dict, message_id: int) -> None:
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{creds['bot_token']}/deleteMessage",
        data=json.dumps({"chat_id": creds["chat_id"], "message_id": message_id}).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            ok = json.load(resp).get("ok")
    except Exception as e:
        ok = False
        print(f"  не удалось удалить {message_id}: {e}")
    data = load_json_list(PUBLISHED_PATH)
    for e in data:
        if e.get("message_id") == message_id:
            e["deleted"] = True
    PUBLISHED_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  старый пост {message_id} {'удалён' if ok else 'помечен удалённым'}")


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
    p.add_argument("--replace", type=int, help="message_id сегодняшнего поста, который заменить (удалить после публикации)")
    p.set_defaults(fn=cmd_publish)
    p = sub.add_parser("apartments", help="каталог всех наших квартир (TravelLine)")
    p.add_argument("--refresh", action="store_true")
    p.set_defaults(fn=cmd_apartments)
    p = sub.add_parser("apartment", help="квартира: описание и реальные фото")
    p.add_argument("code")
    p.add_argument("--download", type=int, default=0, help="скачать первые N фото, чтобы посмотреть")
    p.set_defaults(fn=cmd_apartment)
    p = sub.add_parser("sync-memory", help="записать память публикаций в main")
    p.add_argument("--message")
    p.set_defaults(fn=cmd_sync)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
