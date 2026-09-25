"""Тесты редакционной системы Telegram: проверка черновика, новизна, рендер, память."""

import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import tg_editorial as ed  # noqa: E402

APT = ed.load_apartments()[0]
TODAY = date(2026, 9, 24)  # четверг → reason_to_come


def good_draft(**over) -> dict:
    d = {
        "date": TODAY.isoformat(),
        "pillar": "reason_to_come",
        "format": "big_event",
        "hook_type": "countdown",
        "audience": "fans",
        "topic_seed": "live",
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


def seed_draft(**over) -> dict:
    d = {
        "date": "2026-09-21", "pillar": "how_we_work", "format": "story", "hook_type": "insider", "audience": "guests",
        "topic_seed": "hww_02", "topic_id": "how_we_answer_in_5_minutes", "clusters": [],
        "title": "23:40, гость пишет «не могу найти подъезд» — что дальше",
        "paragraphs": [
            "Такие сообщения приходят чаще, чем кажется. Поздний рейс, новый район, одинаковые дома во дворе.",
            "Поэтому мы отвечаем в мессенджере до 5 минут, в любое время. В инструкции есть фото подъезда и этаж.",
            "Заселение у нас без встреч. Но живой человек на связи всё равно важнее любой инструкции.",
        ],
        "entities": [], "event_date": "",
        "sources": [{"url": "https://добрыйдом-72.рф/", "must_contain": ["ответ до 5 минут"]}],
        "image_headline": "Ответим за 5 минут",
        "apartment_code": APT["code"],
        "image": {"kind": "apartment", "reference_url": APT["images"][1], "scene": "apartment entrance at night"},
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
        history = [{"date": "2026-09-20", "title": "Другое", "text": "про другое", "clusters": [],
                    "format": "story", "pillar": "community"}]
        res = ed.validate_draft(seed_draft(), self.cfg, date(2026, 9, 21), history=history, offline=True)
        self.assertTrue(any("формат story" in e for e in res["errors"]))
        # у рубрики с единственным форматом ротация не блокирует
        history = [{"date": "2026-09-23", "title": "Другое", "text": "про другое", "clusters": [], "format": "big_event"}]
        res = self.run_v(good_draft(), history)
        self.assertFalse(any("формат big_event" in e for e in res["errors"]))

    def test_entity_cooldown_blocks(self):
        history = [{"date": "2026-09-10", "title": "Что нового", "text": "текст", "clusters": [],
                    "entities": ["Русская филармония"], "format": "route"}]
        res = self.run_v(good_draft(), history)
        self.assertTrue(any("Русская филармония" in e for e in res["errors"]))

    def test_event_too_soon_fails(self):
        res = self.run_v(good_draft(event_date="2026-09-25"))
        self.assertTrue(any("меньше 5 дн" in e for e in res["errors"]))

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
        res = self.run_v(good_draft(pillar="weekend_idea", format="story"))
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
        cap = ed.render_caption(good_draft(), self.cfg, [])
        self.assertTrue(cap.startswith("<b>"))
        self.assertNotIn("1️⃣", cap)
        self.assertIn("добрыйдом-72.рф/booking", cap)
        self.assertLess(len(ed.html_to_text(cap)), 1000)

    def test_lists_forbidden(self):
        res = ed.validate_draft(good_draft(list_items=["10 октября — концерт", "11 октября — выставка"]), self.cfg, TODAY, history=[], offline=True)
        self.assertTrue(any("списки" in e for e in res["errors"]))

    def test_owner_cta_for_owner_rubric(self):
        self.assertEqual(ed.pick_cta(self.cfg, [], kind="owner")["kind"], "owner")

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
        self.assertEqual(plan["topic_source"], "live")
        self.assertIn("thermal", plan["blocked_clusters"])
        self.assertTrue(all("{" not in q for q in plan["search_queries"]))

    def test_cycle_has_14_unique_rubrics(self):
        days = self.cfg["cycle"]["days"]
        self.assertEqual(len(days), 14)
        self.assertEqual(len(set(days)), 14)
        for p in days:
            self.assertIn(p, self.cfg["pillars"])

    def test_seed_rubrics_have_year_of_topics(self):
        for pid, p in self.cfg["pillars"].items():
            if p.get("topic_source") == "seeds":
                self.assertGreaterEqual(len(p["seeds"]), 26, pid)
                self.assertEqual(len({s["topic"] for s in p["seeds"]}), len(p["seeds"]), pid)

    def test_schedule_two_weeks(self):
        self.assertEqual(ed.pillar_for(date(2026, 9, 21), self.cfg), "how_we_work")
        self.assertEqual(ed.pillar_for(date(2026, 9, 28), self.cfg), "market_news")
        self.assertEqual(ed.pillar_for(date(2026, 10, 5), self.cfg), "how_we_work")

    def test_seed_used_once(self):
        d = seed_draft()
        res = ed.validate_draft(d, self.cfg, date(2026, 9, 21), history=[], offline=True)
        self.assertTrue(res["ok"], res["errors"])
        history = [{"date": "2026-09-07", "title": "Иное", "text": "иное", "pillar": "how_we_work", "topic_seed": d["topic_seed"], "clusters": []}]
        res = ed.validate_draft(d, self.cfg, date(2026, 9, 21), history=history, offline=True)
        self.assertTrue(any("уже была в этой рубрике" in e for e in res["errors"]))

    def test_blog_story_used_once(self):
        d = seed_draft(pillar="guest_stories", format="story", topic_seed="blog", date="2026-09-25",
                       topic_id="blog_one_night_min_two", sources=[{"url": "https://добрыйдом-72.рф/blog/oplachena-odna-noch-minimum-dvoe-sutok/", "must_contain": ["4 800"]}])
        history = [{"date": "2026-09-11", "title": "Иное", "text": "иное", "pillar": "guest_stories", "clusters": [],
                    "sources": ["https://xn---72-9cdob8azaodt6k.xn--p1ai/blog/oplachena-odna-noch-minimum-dvoe-sutok/"]}]
        res = ed.validate_draft(d, self.cfg, date(2026, 9, 25), history=history, offline=True)
        self.assertTrue(any("уже была пересказана" in e for e in res["errors"]))

    def test_long_sentence_fails(self):
        long = "Мы " + " ".join(["очень"] * 40) + " стараемся."
        d = seed_draft(paragraphs=[long, seed_draft()["paragraphs"][1]])
        res = ed.validate_draft(d, self.cfg, date(2026, 9, 21), history=[], offline=True)
        self.assertTrue(any("длинное предложение" in e for e in res["errors"]))

    def test_second_post_same_day_blocked(self):
        history = [{"source": "published", "date": "2026-09-21", "title": "Уже вышло", "text": "x", "clusters": []}]
        res = ed.validate_draft(seed_draft(), self.cfg, date(2026, 9, 21), history=history, offline=True)
        self.assertTrue(any("уже опубликован" in e for e in res["errors"]))

    def test_merge_lists_dedupes(self):
        a = [{"message_id": 1, "date": "2026-09-01"}]
        b = [{"message_id": 1, "date": "2026-09-01"}, {"message_id": 2, "date": "2026-09-02"}]
        self.assertEqual(len(ed.merge_lists(a, b)), 2)

    def test_year_without_repeats(self):
        from datetime import timedelta
        import os
        os.environ["TG_OFFLINE"] = "1"
        hist, start = [], date(2026, 9, 21)
        for i in range(365):
            x = start + timedelta(days=i)
            pid = ed.pillar_for(x, self.cfg)
            src = self.cfg["pillars"][pid].get("topic_source")
            if src == "seeds":
                c = ed.seed_candidates(pid, self.cfg, hist, x)
                self.assertTrue(c, f"нет темы {pid} на {x}")
                hist.append({"date": x.isoformat(), "pillar": pid, "topic_seed": c[0]["id"]})
            elif src == "blog":
                c = ed.blog_candidates(hist, x)
                self.assertTrue(c, f"нет истории на {x}")
                hist.append({"date": x.isoformat(), "pillar": pid, "sources": [c[0]["url"]]})
            elif src == "apartments":
                c = ed.apartment_candidates(pid, hist, x)
                self.assertTrue(c, f"нет квартиры на {x}")
                hist.append({"date": x.isoformat(), "pillar": pid, "apartment_code": c[0]["code"]})
        apts = [h["apartment_code"] for h in hist if h.get("apartment_code")]
        self.assertEqual(len(apts), len(set(apts)))
        seeds = [h["topic_seed"] for h in hist if h.get("topic_seed")]
        self.assertEqual(len(seeds), len(set(seeds)))
        blog = [h["sources"][0] for h in hist if h.get("sources")]
        self.assertEqual(len(blog), len(set(blog)))

    def test_apartment_post_requires_real_photo(self):
        apt = ed.load_apartments()[0]
        d = seed_draft(pillar="apartment_week", format="portrait", topic_seed="apartment", date="2026-09-22",
                       apartment_code=apt["code"], topic_id="apt_week_first",
                       image={"kind": "apartment", "reference_url": "https://images.pexels.com/x.jpg", "scene": "room"})
        res = ed.validate_draft(d, self.cfg, date(2026, 9, 22), history=[], offline=True)
        self.assertTrue(any("реальным фото квартиры" in e for e in res["errors"]))
        d["image"]["reference_url"] = apt["images"][0]
        hist = [{"date": "2026-09-01", "title": "x", "text": "x", "clusters": [], "image_reference": apt["images"][0]}]
        res = ed.validate_draft(d, self.cfg, date(2026, 9, 22), history=hist, offline=True)
        self.assertTrue(any("фото уже было" in e for e in res["errors"]))

    def test_apartment_cta_links_to_that_apartment(self):
        apt = ed.load_apartments()[0]
        cap = ed.render_caption(seed_draft(apartment_code=apt["code"], topic_seed="apartment"), self.cfg, [])
        self.assertNotIn("room-type", ed.render_caption(seed_draft(), self.cfg, []))
        self.assertIn(f"room-type={apt['code']}", cap)

    def test_merge_lists_local_wins(self):
        remote = [{"message_id": 5, "date": "2026-09-01", "title": "a"}]
        local = [{"message_id": 5, "date": "2026-09-01", "title": "a", "deleted": True}]
        self.assertTrue(ed.merge_lists(remote, local)[0].get("deleted"))

    def test_cluster_detection(self):
        self.assertIn("thermal", ed.strong_clusters("Термы под Тюменью", "", self.cfg))
        self.assertNotIn("family", ed.strong_clusters("Семь причин", "семь дней", self.cfg))


if __name__ == "__main__":
    unittest.main()
