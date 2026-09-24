#!/usr/bin/env python3
"""
Telegram Content Director — оркестратор с отчётом.
Запуск: подготовка поста → gate → learner report.
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))

from telegram_content_learner import build_director_report, print_report, save_report


def run_prepare(category: str, topic: str = "", use_scout: bool = False, auto_publish: bool = False) -> int:
    cmd = [sys.executable, str(SCRIPT_DIR / "daily_telegram_pipeline.py"), "--category", category]
    if topic:
        cmd.extend(["--topic", topic])
    if use_scout:
        cmd.append("--use-scout")
    if auto_publish:
        cmd.append("--auto-publish")
    return subprocess.call(cmd)


def run_publish(bundle: str, variant: int) -> int:
    cmd = [
        sys.executable,
        str(SCRIPT_DIR / "publish_telegram_bundle.py"),
        "--bundle",
        bundle,
        "--variant",
        str(variant),
    ]
    return subprocess.call(cmd)


def main():
    parser = argparse.ArgumentParser(description="Telegram Content Director")
    parser.add_argument("--category", default="")
    parser.add_argument("--topic", default="")
    parser.add_argument("--use-scout", action="store_true")
    parser.add_argument("--prepare", action="store_true", help="Сгенерировать bundle (1 фото + 3 текста)")
    parser.add_argument("--auto-publish", action="store_true", help="После успешной подготовки сразу опубликовать вариант 1")
    parser.add_argument("--publish", default="", help="Путь к bundle для публикации")
    parser.add_argument("--variant", type=int, default=1, choices=[1, 2, 3])
    parser.add_argument("--report-only", action="store_true", help="Только отчёт learner")
    args = parser.parse_args()

    if args.report_only:
        report = build_director_report()
        path = save_report(report)
        print_report(report)
        print(f"\nreport_file: {path}")
        return

    if not args.prepare and not args.publish:
        report = build_director_report()
        path = save_report(report)
        print_report(report)
        print(f"\nreport_file: {path}")
        return

    if args.prepare or args.publish:
        from tg_legacy_guard import refuse_legacy
        refuse_legacy()

    if args.prepare:
        cat = args.category
        if not cat:
            from daily_telegram_pipeline import get_today_category
            cat = get_today_category()
        print(f"=== DIRECTOR: подготовка [{cat}] ===")
        code = run_prepare(cat, args.topic, args.use_scout, args.auto_publish)
        report = build_director_report()
        save_report(report)
        print_report(report)
        sys.exit(code)

    if args.publish:
        print(f"=== DIRECTOR: публикация variant {args.variant} ===")
        code = run_publish(args.publish, args.variant)
        if code == 0:
            subprocess.call([
                sys.executable,
                str(SCRIPT_DIR / "telegram_content_learner.py"),
                "--record",
                args.publish,
                "--variant",
                str(args.variant),
            ])
        report = build_director_report()
        save_report(report)
        print_report(report)
        sys.exit(code)


if __name__ == "__main__":
    main()
