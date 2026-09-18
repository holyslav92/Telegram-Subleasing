"""Проверки защиты Telegram-пайплайна от выдуманных локаций и повторов."""

from __future__ import annotations

import unittest
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from image_prompt_builder import build_image_prompt
from telegram_content_bank import get_next_topic
from telegram_visual_reference import validate_reference_policy


class TelegramVisualReferenceTest(unittest.TestCase):
    def test_generation_requires_logo_and_source_photo(self) -> None:
        self.assertTrue(validate_reference_policy(["logo.png"]))
        self.assertEqual(validate_reference_policy(["logo.png", "photo.jpg"]), [])

    def test_prompt_forbids_inventing_location_details(self) -> None:
        prompt = build_image_prompt(
            "weekend_thermal",
            text_on_image="Тест",
            visual_idea="Use the supplied source photograph as the exact scene reference.",
            scene_override="Use the supplied source photograph as the exact scene reference.",
        )["prompt"]
        self.assertIn("Do not invent, add or replace bridges", prompt)
        self.assertNotIn("may inspire mood", prompt)

    def test_friday_topic_does_not_return_blocked_embankment(self) -> None:
        topic = get_next_topic("weekend_thermal", history=[])
        self.assertNotEqual(topic.get("id"), "weekend_embankment_walk")
        self.assertNotEqual(topic.get("id"), "weekend_letoleto_spa")


if __name__ == "__main__":
    unittest.main()
