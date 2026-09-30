#!/usr/bin/env python3
"""Исследование публичных Telegram-каналов по веб-ленте t.me/s: посты, просмотры, реакции.

Личный аккаунт не нужен: веб-лента публичного канала показывает просмотры и реакции
под каждым постом. Результат — JSON для анализа «что заходит, что нет».

    python3 scripts/tg_channel_research.py collect sutkii lite_aparts_ekb --posts 120 --out /tmp/tg_research.json
    python3 scripts/tg_channel_research.py report /tmp/tg_research.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import statistics
import sys
import time
import urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"


def get(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ru"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def parse_count(s: str) -> int:
    s = s.strip().replace(" ", "").replace(",", ".")
    m = re.match(r"([\d.]+)([KM]?)", s)
    if not m:
        return 0
    n = float(m.group(1))
    return int(n * {"": 1, "K": 1_000, "M": 1_000_000}[m.group(2)])


def clean(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment)
    return html.unescape(re.sub(r"<[^>]+>", "", fragment)).strip()


def parse_page(raw: str, channel: str) -> list[dict]:
    posts = []
    blocks = re.split(r'(?=<div class="tgme_widget_message_wrap)', raw)
    for b in blocks:
        m = re.search(r'data-post="([^"/]+)/(\d+)"', b)
        if not m:
            continue
        text_m = re.search(r'<div class="tgme_widget_message_text[^"]*"[^>]*>(.*?)</div>', b, re.S)
        views_m = re.search(r'<span class="tgme_widget_message_views">([^<]+)</span>', b)
        date_m = re.search(r'<time[^>]+datetime="([^"]+)"', b)
        reactions = sum(parse_count(x) for x in re.findall(
            r'class="tgme_reaction[^"]*"[^>]*>.*?</i>\s*([\d.,KM ]+)</span>', b, re.S))
        if not reactions:
            reactions = sum(parse_count(x) for x in re.findall(r'</(?:i|tg-emoji)>([\d.,KM]+)</span>', b))
        media = ("video" if "tgme_widget_message_video" in b or "roundvideo" in b else
                 "album" if "tgme_widget_message_grouped" in b else
                 "photo" if "tgme_widget_message_photo" in b else
                 "poll" if "tgme_widget_message_poll" in b else "text")
        posts.append({
            "channel": channel,
            "id": int(m.group(2)),
            "url": f"https://t.me/{m.group(1)}/{m.group(2)}",
            "date": date_m.group(1)[:10] if date_m else "",
            "views": parse_count(views_m.group(1)) if views_m else 0,
            "reactions": reactions,
            "media": media,
            "forwarded": "tgme_widget_message_forwarded_from" in b,
            "text": clean(text_m.group(1)) if text_m else "",
        })
    return posts


def channel_info(raw: str) -> dict:
    title = re.search(r'<div class="tgme_channel_info_header_title[^"]*"><span[^>]*>(.*?)</span>', raw, re.S)
    subs = re.search(r'<span class="counter_value">([^<]+)</span>\s*<span class="counter_type">(?:subscribers|подписчик)', raw)
    desc = re.search(r'<div class="tgme_channel_info_description">(.*?)</div>', raw, re.S)
    return {
        "title": clean(title.group(1)) if title else "",
        "subscribers": parse_count(subs.group(1)) if subs else 0,
        "description": clean(desc.group(1))[:300] if desc else "",
    }


def collect(channel: str, limit: int) -> dict:
    raw = get(f"https://t.me/s/{channel}")
    info = channel_info(raw)
    posts = parse_page(raw, channel)
    while posts and len(posts) < limit:
        before = min(p["id"] for p in posts)
        if before <= 1:
            break
        time.sleep(0.6)
        more = parse_page(get(f"https://t.me/s/{channel}?before={before}"), channel)
        more = [p for p in more if p["id"] < before]
        if not more:
            break
        posts += more
    posts = sorted({p["id"]: p for p in posts}.values(), key=lambda p: p["id"], reverse=True)[:limit]
    return {"channel": channel, **info, "posts": posts}


def score_posts(ch: dict) -> None:
    """Индекс поста = просмотры / медиана канала; вовлечённость = реакции на 1000 просмотров."""
    views = [p["views"] for p in ch["posts"] if p["views"] and not p["forwarded"]]
    med = statistics.median(views) if views else 0
    ch["median_views"] = med
    for p in ch["posts"]:
        p["view_index"] = round(p["views"] / med, 2) if med else 0
        p["er"] = round(1000 * p["reactions"] / p["views"], 1) if p["views"] else 0


def cmd_collect(args) -> int:
    out = []
    for name in args.channels:
        try:
            ch = collect(name, args.posts)
        except Exception as e:
            print(f"{name}: не открылся ({e})", file=sys.stderr)
            continue
        if not ch["posts"]:
            print(f"{name}: нет публичной ленты", file=sys.stderr)
            continue
        score_posts(ch)
        out.append(ch)
        print(f"{name}: «{ch['title'][:40]}» подписчиков {ch['subscribers']}, постов {len(ch['posts'])}, "
              f"медиана просмотров {ch['median_views']}", file=sys.stderr)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return 0


def cmd_report(args) -> int:
    data = json.load(open(args.file, encoding="utf-8"))
    for ch in data:
        posts = [p for p in ch["posts"] if p["views"] and not p["forwarded"]]
        if not posts:
            continue
        print(f"\n=== @{ch['channel']} «{ch['title']}» — {ch['subscribers']} подписчиков, медиана {ch['median_views']}")
        for p in sorted(posts, key=lambda p: p["view_index"], reverse=True)[: args.top]:
            print(f"  ▲ x{p['view_index']:<5} {p['views']:>6} просм. {p['reactions']:>4} реакц. {p['media']:<6} "
                  f"{p['date']} {p['text'][:110].replace(chr(10), ' ')}")
        for p in sorted(posts, key=lambda p: p["view_index"])[: args.bottom]:
            print(f"  ▼ x{p['view_index']:<5} {p['views']:>6} просм. {p['reactions']:>4} реакц. {p['media']:<6} "
                  f"{p['date']} {p['text'][:110].replace(chr(10), ' ')}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("collect")
    p.add_argument("channels", nargs="+")
    p.add_argument("--posts", type=int, default=120)
    p.add_argument("--out", default="/tmp/tg_research.json")
    p.set_defaults(fn=cmd_collect)
    p = sub.add_parser("report")
    p.add_argument("file")
    p.add_argument("--top", type=int, default=8)
    p.add_argument("--bottom", type=int, default=4)
    p.set_defaults(fn=cmd_report)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    sys.exit(main())
