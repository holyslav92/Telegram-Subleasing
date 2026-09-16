#!/usr/bin/env python3
"""
Content Learner для Telegram: учится на опубликованных постах,
фиксирует уроки, блокирует повторы, формирует отчёт для директора.
"""

import argparse
import json
import re
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent
LESSONS_FILE = WORKSPACE_ROOT / "memory" / "telegram_posts" / "lessons.json"
REPORTS_DIR = WORKSPACE_ROOT / "memory" / "telegram_posts" / "reports"

sys.path.insert(0, str(SCRIPT_DIR))

from telegram_post_history import load_ledger, strip_html, text_fingerprint
from telegram_similarity import opening_hook, similarity_score, BANNED_OPENING_HOOKS


def load_lessons() -> dict:
    if LESSONS_FILE.exists():
        try:
            with open(LESSONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "version": 1,
        "lessons": [],
        "used_opening_hooks": [],
        "used_angles_by_category": {},
        "banned_hooks": list(BANNED_OPENING_HOOKS),
    }


def save_lessons(data: dict) -> None:
    LESSONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LESSONS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def iso_week() -> str:
    return datetime.now().strftime("%G-W%V")


def record_publication_lesson(
    topic_id: str,
    category_id: str,
    title: str,
    text_html: str,
    variant_number: int = 1,
    craft_meta: dict | None = None,
) -> dict:
    """Записывает урок после публикации; обновляет lessons.json и craft-память."""
    lessons = load_lessons()
    hook = opening_hook(text_html)
    fp = text_fingerprint(text_html)
    week = iso_week()
    craft_meta = craft_meta or {}

    entry = {
        "id": f"pub_{topic_id}_{datetime.now().strftime('%Y%m%d')}",
        "topic_id": topic_id,
        "category_id": category_id,
        "title": title,
        "opening_hook": hook,
        "text_fingerprint": fp,
        "variant_number": variant_number,
        "week": week,
        "craft_meta": craft_meta,
        "recorded_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "lesson": f"Опубликовано: {title}. Не повторять hook и topic_id 60+ дней.",
    }

    # Дедуп по fingerprint
    existing_fps = {l.get("text_fingerprint") for l in lessons.get("lessons", [])}
    if fp not in existing_fps:
        lessons.setdefault("lessons", []).append(entry)

    hooks = lessons.setdefault("used_opening_hooks", [])
    if hook and hook not in hooks:
        hooks.append(hook)

    by_cat = lessons.setdefault("used_angles_by_category", {})
    by_cat.setdefault(category_id, [])
    if topic_id not in by_cat[category_id]:
        by_cat[category_id].append(topic_id)

    _record_craft_memory(lessons, craft_meta, week)

    lessons["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    save_lessons(lessons)
    return entry


def _append_unique(lst: list, value) -> None:
    if value and value not in lst:
        lst.append(value)


def _record_craft_memory(lessons: dict, craft_meta: dict, week: str) -> None:
    """Запоминает использованные craft-элементы для ротации."""
    if not craft_meta:
        return
    _append_unique(lessons.setdefault("used_cta_ids", []), craft_meta.get("cta_id"))
    _append_unique(lessons.setdefault("used_scene_ids", []), craft_meta.get("scene_id"))
    _append_unique(lessons.setdefault("used_audience_lines", []), craft_meta.get("audience_id"))
    _append_unique(lessons.setdefault("used_contrast_ids", []), craft_meta.get("contrast_id"))
    _append_unique(lessons.setdefault("used_micro_proof_ids", []), craft_meta.get("micro_proof_id"))
    _append_unique(lessons.setdefault("used_urgency_ids", []), craft_meta.get("urgency_id"))
    if craft_meta.get("save_worthy_id"):
        _append_unique(lessons.setdefault("used_save_worthy_ids", []), craft_meta.get("save_worthy_id"))
        _append_unique(lessons.setdefault("save_worthy_weeks", []), week)


def analyze_repetition_risks() -> dict:
    """Анализ ledger + lessons на риски повторов."""
    ledger = load_ledger()
    lessons = load_lessons()
    risks = []

    hooks_seen: dict[str, int] = {}
    for entry in ledger:
        text = entry.get("text_html") or entry.get("title") or ""
        if not text:
            continue
        hook = entry.get("opening_hook") or opening_hook(text)
        hooks_seen[hook] = hooks_seen.get(hook, 0) + 1

    for hook, count in hooks_seen.items():
        if count > 1 and hook:
            risks.append(f"Opening hook повторялся {count}×: «{hook[:80]}…»")

    # Похожие пары в ledger
    for i, a in enumerate(ledger):
        for b in ledger[i + 1 :]:
            ta = a.get("text_html") or a.get("title") or ""
            tb = b.get("text_html") or b.get("title") or ""
            if not ta or not tb:
                continue
            score = similarity_score(ta, tb)
            if score >= 0.45:
                risks.append(
                    f"Похожие посты {a.get('id')} ↔ {b.get('id')} (score={score:.2f})"
                )

    return {
        "ledger_count": len(ledger),
        "lessons_count": len(lessons.get("lessons", [])),
        "unique_hooks": len(hooks_seen),
        "week": iso_week(),
        "risks": risks,
        "categories_published": lessons.get("used_angles_by_category", {}),
    }


def build_director_report() -> dict:
    analysis = analyze_repetition_risks()
    ledger = load_ledger()
    lessons = load_lessons()

    recent = sorted(ledger, key=lambda x: x.get("published_at", ""), reverse=True)[:7]
    report = {
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "week": iso_week(),
        "status": "OK" if not analysis["risks"] else "NEEDS_ATTENTION",
        "published_total": len(ledger),
        "recent_publications": [
            {
                "id": e.get("id"),
                "category_id": e.get("category_id"),
                "title": e.get("title"),
                "published_at": e.get("published_at"),
            }
            for e in recent
        ],
        "lessons_recorded": len(lessons.get("lessons", [])),
        "repetition_risks": analysis["risks"],
        "recommendations": [
            "Не использовать один opening hook дважды за 8 недель.",
            "3 варианта: История / Чек-лист / Диалог — craft-композитор.",
            "CTA, сцены и proof ротируются — см. used_* в lessons.json.",
            "Конtrast и save-worthy — только в тему, не в каждом посте.",
        ],
        "next_checks": [
            "python3 scripts/telegram_content_learner.py --report",
            "python3 scripts/telegram_history_backfill.py",
        ],
    }
    return report


def save_report(report: dict) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = REPORTS_DIR / f"director_report_{ts}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return path


def print_report(report: dict) -> None:
    print("=== TELEGRAM CONTENT DIRECTOR REPORT ===")
    print(f"status: {report['status']}")
    print(f"week: {report['week']}")
    print(f"published_total: {report['published_total']}")
    print(f"lessons_recorded: {report['lessons_recorded']}")
    print("\nrecent_publications:")
    for r in report.get("recent_publications", []):
        print(f"  - [{r.get('published_at')}] {r.get('id')} · {r.get('title', '')[:50]}")
    risks = report.get("repetition_risks") or []
    print(f"\nrepetition_risks: {len(risks)}")
    for risk in risks[:10]:
        print(f"  ⚠ {risk}")
    print("\nrecommendations:")
    for rec in report.get("recommendations", []):
        print(f"  • {rec}")


def main():
    parser = argparse.ArgumentParser(description="Telegram Content Learner")
    parser.add_argument("--report", action="store_true", help="Отчёт директора")
    parser.add_argument("--record", default="", help="JSON-файл опубликованного поста/bundle")
    parser.add_argument("--variant", type=int, default=1)
    args = parser.parse_args()

    if args.record:
        with open(args.record, "r", encoding="utf-8") as f:
            data = json.load(f)
        variants = data.get("variants") or []
        chosen = variants[args.variant - 1] if variants else data
        text = chosen.get("text_html") if isinstance(chosen, dict) else data.get("text_html", "")
        craft_meta = (
            chosen.get("craft_meta")
            if isinstance(chosen, dict)
            else data.get("craft_meta", {})
        ) or {}
        entry = record_publication_lesson(
            data.get("id", ""),
            data.get("category_id", ""),
            data.get("title", ""),
            text,
            variant_number=args.variant,
            craft_meta=craft_meta,
        )
        print(json.dumps({"recorded": entry}, ensure_ascii=False, indent=2))
        return

    report = build_director_report()
    path = save_report(report)
    print_report(report)
    print(f"\nreport_file: {path}")


if __name__ == "__main__":
    main()
