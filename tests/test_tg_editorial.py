"""Тесты редакционной системы Telegram: проверка черновика, новизна, рендер, память."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tg_editorial as ed  # noqa: E402

TODAY = date(2026, 9, 24)  # четверг → city_news


def good_draft(**over) -> dict:
    d = {
        "date": TODAY.isoformat(),
        "pillar": "city_news",
        "format": "news_useful",
        "topic_id": "roshchino_new_winter_flights_2026",
        "clusters": ["transport"],
        "title": "Из Рощино зимой полетят в Минеральные Воды и Сочи чаще",
        "paragraphs": [
            "Аэропорт Рощино опубликовал зимнее расписание: с конца октября в Сочи будет три рейса в неделю вместо двух.",
            "Для тех, кто прилетает в Тюмень по делам, это значит больше удобных стыковок по вечерам в пятницу.",
            "Билеты на ноябрь уже продаются, цены пока держатся на уровне сентября.",
        ],
        "entities": ["Рощино"],
        "event_date": "",
        "sources": [{"url": "https://www.tjm.aero/news/1", "published": "2026-09-23", "must_contain": ["зимнее расписание"]}],
        "image_headline": "Зимнее расписание Рощино",
        "image": {"kind": "city", "reference_url": "", "scene": "Roshchino airport terminal in Tyumen at dusk"},
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
        history = [{"date": "2026-09-20", "title": "Новые рейсы из аэропорта Рощино", "text": "рейсы аэропорт",
                    "clusters": ["transport"], "format": "news_useful", "pillar": "city_news"}]
        res = self.run_v(good_draft(), history)
        self.assertFalse(res["ok"])
        self.assertTrue(any("на паузе" in e for e in res["errors"]))

    def test_same_format_as_last_posts_blocks(self):
        history = [{"date": "2026-09-23", "title": "Другое", "text": "про другое", "clusters": [],
                    "format": "news_useful", "pillar": "trip"}]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("формат news_useful" in e for e in res["errors"]))

    def test_entity_cooldown_blocks(self):
        history = [{"date": "2026-09-10", "title": "Что нового", "text": "текст", "clusters": [],
                    "entities": ["Рощино"], "format": "route"}]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("Рощино" in e for e in res["errors"]))

    def test_old_news_fails(self):
        d = good_draft(sources=[{"url": "https://www.tjm.aero/news/1", "published": "2026-09-01", "must_contain": ["зимнее расписание"]}])
        res = self.run_v(d)
        self.assertTrue(any("не старше" in e for e in res["errors"]))

    def test_wrong_pillar_without_reason_fails(self):
        res = self.run_v(good_draft(pillar="weekend", format="event_list"))
        self.assertTrue(any("сегодня рубрика city_news" in e for e in res["errors"]))

    def test_links_and_emoji_in_text_fail(self):
        d = good_draft(paragraphs=["Смотрите расписание на https://tjm.aero и пишите нам ✅ если есть вопросы по рейсам."])
        res = self.run_v(d)
        self.assertTrue(any("ссылки" in e for e in res["errors"]))
        self.assertTrue(any("эмодзи" in e for e in res["errors"]))

    def test_title_first_word_rotation(self):
        history = [{"date": "2026-09-2%d" % i, "title": "Из дома в театр", "text": "x %d" % i, "clusters": []} for i in range(1, 3)]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("начинается с «из»" in e for e in res["errors"]))

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
        self.assertEqual(plan["pillar"], "city_news")
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
