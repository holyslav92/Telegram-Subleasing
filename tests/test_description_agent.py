#!/usr/bin/env python3
"""Tests for Dzen Description agent path (teaser ≠ title ≠ opening)."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from excalibur_blog_description_gate import check_article, near_duplicate  # noqa: E402
from excalibur_blog_pipeline_canon import (  # noqa: E402
    description_clones_opening,
    description_near_title,
    stamp_article,
)
from excalibur_blog_wp_publish import rss_safe_excerpt  # noqa: E402


class DescriptionAgentContracts(unittest.TestCase):
    def test_rules_and_agent_files_exist(self) -> None:
        self.assertTrue((ROOT / "shared/dzen-description-rules.md").is_file())
        self.assertTrue((ROOT / "agents/excalibur-blog-description.md").is_file())
        self.assertTrue((ROOT / "skills/description-excalibur-blog/SKILL.md").is_file())
        rules = (ROOT / "shared/dzen-description-rules.md").read_text(encoding="utf-8")
        self.assertIn("rss-modify.html", rules)
        self.assertIn("карточк", rules.lower())
        self.assertIn("80–180", rules)

    def test_canon_wires_description(self) -> None:
        canon = json.loads((ROOT / "shared/pipeline-canon.json").read_text(encoding="utf-8"))
        self.assertEqual(canon.get("description_agent"), "excalibur-blog-description")
        self.assertIn("Description", canon.get("description", ""))
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("Description", agents)
        self.assertIn("description-brief.json", agents)

    def test_near_title_detection(self) -> None:
        title = "Langflow без пароля запускает чужой код на сервере агентов"
        self.assertTrue(description_near_title(title, title))
        self.assertTrue(near_duplicate(title, title))
        teaser = (
            "В открытом Langflow без пароля чужой может запустить свой код "
            "на вашем сервере агентов — и это уже чинят."
        )
        self.assertFalse(description_near_title(teaser, title))

    def test_stamp_requires_distinct_teaser(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            article_dir = Path(tmp)
            (article_dir / "article.html").write_text(
                "<p>Многие люди уверены: поднял конструктор — и всё само.</p>\n"
                "<p>Точнее, снаружи другая картина.</p>\n",
                encoding="utf-8",
            )
            title = "Langflow без пароля запускает чужой код на сервере агентов"
            (article_dir / "title-brief.json").write_text(
                json.dumps({"topic_id": "B999", "h1": title, "title": title}, ensure_ascii=False),
                encoding="utf-8",
            )
            # Missing brief → fail
            with self.assertRaises(ValueError):
                stamp_article(article_dir, ROOT)
            # Title-as-description → fail
            (article_dir / "description-brief.json").write_text(
                json.dumps(
                    {
                        "topic_id": "B999",
                        "title": title,
                        "description": title,
                        "char_count": len(title),
                        "verdict": "PASS",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                stamp_article(article_dir, ROOT)
            # Opening clone → fail
            opening_clone = (
                "Многие люди уверены: поднял конструктор — и всё само, "
                "пока снаружи не придёт беда для сервера."
            )
            (article_dir / "description-brief.json").write_text(
                json.dumps(
                    {
                        "topic_id": "B999",
                        "title": title,
                        "description": opening_clone,
                        "char_count": len(opening_clone),
                        "verdict": "PASS",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            self.assertTrue(
                description_clones_opening(opening_clone, (article_dir / "article.html").read_text())
            )
            with self.assertRaises(ValueError):
                stamp_article(article_dir, ROOT)
            # Good teaser → ok
            teaser = (
                "В открытом Langflow без пароля чужой может запустить свой код "
                "на вашем сервере агентов — уже есть патч."
            )
            (article_dir / "description-brief.json").write_text(
                json.dumps(
                    {
                        "topic_id": "B999",
                        "title": title,
                        "description": teaser,
                        "char_count": len(teaser),
                        "verdict": "PASS",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            stamp_article(article_dir, ROOT)
            meta = json.loads((article_dir / "article.meta.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["description"], teaser)
            self.assertNotEqual(meta["description"], meta["h1"])

    def test_rss_safe_excerpt_rejects_title_fallback(self) -> None:
        title = "Cloudflare дал агентам кошелёк с лимитом трат"
        html = "<p>Многие люди уверены: агенту можно дать карту без потолка.</p>"
        with self.assertRaises(ValueError):
            rss_safe_excerpt(description=title, content_html=html, title=title)
        with self.assertRaises(ValueError):
            rss_safe_excerpt(description="", content_html=html, title=title)
        teaser = (
            "Cloudflare ограничил траты ИИ-агента отдельным кошельком, "
            "чтобы бот не сжёг бюджет за ночь."
        )
        self.assertEqual(
            rss_safe_excerpt(description=teaser, content_html=html, title=title),
            teaser,
        )

    def test_description_gate_pass_fail(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            article_dir = Path(tmp)
            title = "Make ставит агенту потолок циклов, чтобы не жечь операции"
            (article_dir / "article.html").write_text(
                "<p>Многие люди уверены: повесил агента — и он сам разберётся.</p>",
                encoding="utf-8",
            )
            (article_dir / "title-brief.json").write_text(
                json.dumps({"h1": title, "title": title, "topic_id": "B139"}),
                encoding="utf-8",
            )
            (article_dir / "article.meta.json").write_text(
                json.dumps({"h1": title, "title": title, "description": title}),
                encoding="utf-8",
            )
            report = check_article(article_dir)
            self.assertEqual(report["status"], "BLOCK")
            teaser = (
                "Make ограничил число кругов агента в сценарии, "
                "чтобы автоматизация не сожгла пакет операций."
            )
            (article_dir / "description-brief.json").write_text(
                json.dumps(
                    {
                        "topic_id": "B139",
                        "title": title,
                        "description": teaser,
                        "char_count": len(teaser),
                        "verdict": "PASS",
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (article_dir / "article.meta.json").write_text(
                json.dumps({"h1": title, "title": title, "description": teaser}),
                encoding="utf-8",
            )
            report2 = check_article(article_dir)
            self.assertEqual(report2["status"], "PASS", report2)


if __name__ == "__main__":
    unittest.main()
