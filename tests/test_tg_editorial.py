"""Тесты редакционной системы Telegram: проверка черновика, новизна, рендер, память."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tg_editorial as ed  # noqa: E402

TODAY = date(2026, 9, 24)  # четверг → reason_to_come


def good_draft(**over) -> dict:
    d = {
        "date": TODAY.isoformat(),
        "pillar": "reason_to_come",
        "format": "big_event",
        "hook_type": "countdown",
        "audience": "fans",
        "stay_reason": "концерт заканчивается поздно, ехать ночью в Сургут или Тобольск неудобно",
        "topic_id": "concert_orchestra_tyumen_20261010",
        "clusters": ["concert"],
        "title": "Через 16 дней в Тюмени сыграет оркестр «Русская филармония»",
        "paragraphs": [
            "10 октября в концертном зале на Республики большой вечер оркестра: Чайковский и Рахманинов, билеты от 1500 рублей.",
            "Концерт начинается в 19:00 и идёт почти три часа, поэтому гостям из Тобольска и Ялуторовска проще приехать днём.",
            "После концерта не нужно гнать ночью по трассе: можно остаться в Тюмени, а утром спокойно позавтракать у реки.",
        ],
        "entities": ["Русская филармония"],
        "event_date": "2026-10-10",
        "sources": [{"url": "https://example.org/concert", "must_contain": ["Русская филармония"]}],
        "image_headline": "10 октября — оркестр",
        "image": {"kind": "event", "reference_url": "", "scene": "symphony orchestra on stage in a concert hall"},
    }
    d.update(over)
    return d


class ValidateTests(unittest.TestCase):
    def setUp(self):
        self.cfg = ed.load_config()

    def run_v(self, d, history=None):
        return ed.validate_draft(d, self.cfg, TODAY, history=history or [], offline=True)

    def test_good_draft_passes(self):
        res = self.run_v(good_draft())
        self.assertTrue(res["ok"], res["errors"])

    def test_banned_phrases_fail(self):
        d = good_draft(paragraphs=good_draft()["paragraphs"][:2] + ["В квартире идеальная чистота и белое постельное бельё для каждого гостя."])
        res = self.run_v(d)
        self.assertFalse(res["ok"])
        joined = " ".join(res["errors"])
        self.assertIn("идеальн", joined)
        self.assertIn("бел", joined)

    def test_repeated_phrase_fails(self):
        p = "Вы только открыли дверь квартиры и сразу видите окно на реку Туру."
        d = good_draft(paragraphs=[p, "Кстати: " + p])
        res = self.run_v(d)
        self.assertFalse(res["ok"])
        self.assertTrue(any("повтор" in e for e in res["errors"]))

    def test_cluster_cooldown_blocks(self):
        history = [{"date": "2026-09-20", "title": "Большой концерт", "text": "концерт гастроли",
                    "clusters": ["concert"], "format": "route", "pillar": "trip"}]
        res = self.run_v(good_draft(), history)
        self.assertFalse(res["ok"])
        self.assertTrue(any("на паузе" in e for e in res["errors"]))

    def test_same_format_as_last_posts_blocks(self):
        history = [{"date": "2026-09-23", "title": "Другое", "text": "про другое", "clusters": [],
                    "format": "big_event", "pillar": "trip"}]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("формат big_event" in e for e in res["errors"]))

    def test_entity_cooldown_blocks(self):
        history = [{"date": "2026-09-10", "title": "Что нового", "text": "текст", "clusters": [],
                    "entities": ["Русская филармония"], "format": "route"}]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("Русская филармония" in e for e in res["errors"]))

    def test_event_too_soon_fails(self):
        res = self.run_v(good_draft(event_date="2026-09-25"))
        self.assertTrue(any("меньше 3 дн" in e for e in res["errors"]))

    def test_weather_post_rejected_as_local(self):
        d = good_draft(title="Ночью до −5, днём до +17 в Тюмени", clusters=["weather"],
                       paragraphs=["Синоптики обещают заморозки ночью и солнечную погоду днём, дождей не будет до конца месяца.",
                                   "Погода отличная для прогулок, если приехать в Тюмень на выходные и взять тёплую куртку."])
        res = self.run_v(d)
        self.assertTrue(any("тема для местных" in e for e in res["errors"]))

    def test_no_stay_link_fails(self):
        d = good_draft(paragraphs=["10 октября в концертном зале большой вечер оркестра: Чайковский и Рахманинов, билеты от 1500 рублей.",
                                   "Концерт начинается в 19:00 и идёт почти три часа с антрактом, программа классическая и понятная."])
        res = self.run_v(d)
        self.assertTrue(any("связи с приездом" in e for e in res["errors"]))

    def test_hook_and_audience_required(self):
        d = good_draft()
        d.pop("hook_type"); d.pop("audience")
        res = self.run_v(d)
        self.assertTrue(any("hook_type" in e for e in res["errors"]))
        self.assertTrue(any("audience" in e for e in res["errors"]))

    def test_hook_rotation(self):
        history = [{"date": "2026-09-23", "title": "Иное", "text": "иное", "clusters": [], "hook_type": "countdown"}]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("крючок countdown" in e for e in res["errors"]))

    def test_vague_title_fails(self):
        res = self.run_v(good_draft(title="чем заняться осенью и куда сходить вечером"))
        self.assertTrue(any("без конкретики" in e for e in res["errors"]))

    def test_wrong_pillar_without_reason_fails(self):
        res = self.run_v(good_draft(pillar="weekend", format="event_list"))
        self.assertTrue(any("сегодня рубрика reason_to_come" in e for e in res["errors"]))

    def test_links_and_emoji_in_text_fail(self):
        d = good_draft(paragraphs=["Смотрите расписание на https://tjm.aero и пишите нам ✅ если есть вопросы по приезду в Тюмень."])
        res = self.run_v(d)
        self.assertTrue(any("ссылки" in e for e in res["errors"]))
        self.assertTrue(any("эмодзи" in e for e in res["errors"]))

    def test_title_first_word_rotation(self):
        history = [{"date": "2026-09-2%d" % i, "title": "Через год в театр", "text": "x %d" % i, "clusters": []} for i in range(1, 3)]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("начинается с «через»" in e for e in res["errors"]))

    def test_similarity_to_old_post_fails(self):
        d = good_draft()
        history = [{"date": "2026-08-01", "title": d["title"] + "!", "text": " ".join(d["paragraphs"]), "clusters": []}]
        res = self.run_v(d, history)
        self.assertTrue(any("похож" in e for e in res["errors"]))


class RenderTests(unittest.TestCase):
    def setUp(self):
        self.cfg = ed.load_config()

    def test_caption_structure(self):
        d = good_draft(format="event_list", list_items=["25 сентября — концерт", "26 сентября — выставка"])
        cap = ed.render_caption(d, self.cfg, [])
        self.assertTrue(cap.startswith("<b>"))
        self.assertIn("1️⃣ 25 сентября", cap)
        self.assertIn("добрыйдом-72.рф/booking", cap)
        self.assertLess(len(ed.html_to_text(cap)), 1000)

    def test_cta_rotates(self):
        first = ed.pick_cta(self.cfg, [])["id"]
        second = ed.pick_cta(self.cfg, [{"cta_id": first}])["id"]
        self.assertNotEqual(first, second)

    def test_buttons_have_booking_and_max(self):
        urls = [b["url"] for row in ed.render_buttons(self.cfg)["inline_keyboard"] for b in row]
        self.assertTrue(any("booking" in u for u in urls))
        self.assertTrue(any("max.ru" in u for u in urls))


class PlanAndMemoryTests(unittest.TestCase):
    def setUp(self):
        self.cfg = ed.load_config()

    def test_plan_uses_weekday_pillar_and_blocks(self):
        history = [{"date": "2026-09-22", "title": "Термы Верхнего Бора", "text": "термы термальные", "clusters": ["thermal"], "format": "route"}]
        plan = ed.build_plan(self.cfg, TODAY, history)
        self.assertEqual(plan["pillar"], "reason_to_come")
        self.assertIn("thermal", plan["blocked_clusters"])
        self.assertTrue(all("{" not in q for q in plan["search_queries"]))

    def test_every_weekday_has_pillar(self):
        for i in range(7):
            self.assertIn(self.cfg["weekday_pillars"][str(i)], self.cfg["pillars"])

    def test_merge_lists_dedupes(self):
        a = [{"message_id": 1, "date": "2026-09-01"}]
        b = [{"message_id": 1, "date": "2026-09-01"}, {"message_id": 2, "date": "2026-09-02"}]
        self.assertEqual(len(ed.merge_lists(a, b)), 2)

    def test_cluster_detection(self):
        self.assertIn("thermal", ed.strong_clusters("Термы под Тюменью", "", self.cfg))
        self.assertNotIn("family", ed.strong_clusters("Семь причин", "семь дней", self.cfg))


if __name__ == "__main__":
    unittest.main()
