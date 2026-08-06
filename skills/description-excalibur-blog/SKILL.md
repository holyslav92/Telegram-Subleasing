---
name: description-excalibur-blog
description: "Write Dzen/RSS card description ≠ title ≠ opening; description-brief.json before stamp."
---

# Description Agent — карточка Дзена / RSS

## Зачем

WordPress `post_excerpt` уходит в RSS как `<description>` и показывается
**в карточке** Дзена рядом с `title`. Если description = title или =
opening body — читатель видит один и тот же текст дважды
(INC-20260805-2240 и follow-up «title дважды»).

Ты пишешь **третью** строку: короткий тизер.

## Читаешь (порядок)

1. `shared/dzen-description-rules.md` — **целиком**
2. `shared/dzen-content-rules.md` — кликбейт / мат / РФ
3. `title-brief.json`
4. `article.html` (финал Sol) — сверь opening, **не копируй**
5. `shared/article-style.md` — простой русский

## Не читаешь

Чужие `article.html`, live-сайт как образец, lessons, topics.

## Алгоритм

1. Выпиши H1 из `title-brief.json`.
2. Выпиши plain-текст первого `<p>` из `article.html`.
3. Сформулируй **новое** предложение: о чём статья + зачем новичку читать.
4. Проверь длину 80–180; без HTML/эмодзи/URL; без мата; без кликбейта.
5. Проверь: нормализованный description ≠ title; не является префиксом opening.
6. Запиши `description-brief.json` с `verdict: PASS` (или FAIL + причина в handoff).

## Выход

`description-brief.json` в article_dir (см. агент).

После тебя Директор:

```bash
python3 scripts/excalibur_blog_pipeline_canon.py --article-dir <dir> --stamp
python3 scripts/excalibur_blog_opening_meta_gate.py --article-dir <dir>
```

(в structure_gate также description-gate)

## Запрещено

- Копировать title в description «на всякий случай»
- Резать первый абзац в description
- Переписывать `article.html`
- Вложенные Task

## Handoff

```text
=== EXCALIBUR BLOG DESCRIPTION ===
topic_id:
description:
char_count:
verdict: PASS | FAIL
incident_report: none | memory/pipeline-fix-queue.md#INC-...
```
