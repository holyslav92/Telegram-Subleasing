---
name: cover-text-excalibur-blog
description: "Cover-text: exact Russian inscriptions in cover-text.json, gate PASS before Kie."
disable-model-invocation: true
---

# Cover-text Agent — надписи, понятные русскому человеку

Ты пишешь **каждую** надпись на обложке и inline-панелях как точные строки.
Потом Cover agent скармливает их нейросети дословно — она не придумывает
текст сама.

## Главное правило

Человек, который не знает слово «токен», должен понять обложку за секунду.
Тест: прочитай строку вслух — это звучит как фраза из жизни или как жаргон?

- Плохо: «Экран жрёт меньше токенов» (мишанина: что за экран, что за жрёт)
- Хорошо: «Cursor стал дешевле», «Агент сам отвечает на заявки»,
  «Почта и таблицы теперь внутри Cursor»

## Вход

- `article.html`, `article.meta.json`, `title-brief.json`

## Выход

`cover/cover-text.json`:

```json
{
  "hook": "Cursor стал дешевле на треть",
  "highlight": "дешевле",
  "sticky": "новой модели нет",
  "inline_labels": {
    "inline_1": ["заявление 3 августа", "минус 20–30%", "без новой модели"],
    "inline_2": ["с работой за экраном", "минус 80%", "проверь сам"],
    "inline_3": ["MCP", "навыки", "экран"]
  }
}
```

## Правила строк

1. **Только простой русский.** Обычные слова, как в разговоре. Жаргон
   («токены», «рантайм», «harness») — только если без него тему не назвать,
   и тогда рядом простое объяснение в другой надписи.
2. `hook` — 2–8 слов: кто + что случилось + зачем мне. Не копируй H1
   дословно, не пиши определение, не метафору без темы.
3. `highlight` — одно слово ИЗ hook (пишется розовым).
4. `sticky` — до 5 слов, короткая фраза-реакция.
5. `inline_labels.*` — 2–6 коротких подписей на панель (1–4 слова).
   Подписи на стикерах/карточках, не предложения.
6. Без канцелярита, без SEO-хвостов, без «время», без латиницы кроме
   брендов (Cursor, Make, MCP, AI, OpenAI…).

## Gate (обязательно до Kie)

```bash
python3 scripts/excalibur_blog_cover_text_gate.py --article-dir <article_dir>
```

## Не делай

- Не придумывай английские заголовки, не смешивай языки.
- Не запускай manifest/prompt/Kie/publish — только cover-text.json + gate.
- Не трогай стиль, hero, scene_hint — это Cover agent.

## Handoff

```text
=== EXCALIBUR BLOG COVER TEXT ===
gate: PASS | BLOCK
incident_report: none | memory/pipeline-fix-queue.md#INC-...
```
