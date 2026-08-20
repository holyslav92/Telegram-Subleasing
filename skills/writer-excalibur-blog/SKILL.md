---
name: writer-excalibur-blog
description: Write meaning draft drafts/writer.html; Sol applies tenant SOUL style. Director-chain specialist.
disable-model-invocation: true
---

# Writer Skill — смысл статьи (черновик)

Ты пишешь **смысл**: факты, тезисы, ограничения, CTA.  
Финал слога делает **Sol** (`excalibur-blog-sol`) по SOUL + examples.
Ты Sol **не** запускаешь — Директор вызовет его следующим Task.

Выход: **`drafts/writer.html`** (чистый HTML-фрагмент без `<h1>`).  
Можно положить ту же копию во временный `article.html`, но канон —
`drafts/writer.html`. Sol перепишет `article.html`.

## Читаешь

1. `shared/writer-master-prompt.md` (секция Writer / смысл)
2. `research-notes.md`
3. `title-brief.json`
4. `published-titles-only.md`
5. `shared/dzen-content-rules.md` + RF (не герой Meta/…) — кратко

## Не обязан читать (это зона Sol)

`shared/SOUL.md`, `shared/soul-examples/*` — Sol применит слог сам.
Можешь писать ясно по-русски без SEO; не трать ход на косплей тенанта.

## Правила смысла

- Все факты только из research; не выдумывай.
- Структура: открытие → несколько H2 с мыслями → практика/ограничения → CTA.
- Без research-даты / Wordstat в открытии (Sol всё равно вычистит, но не засоряй).
- CTA: только tenant-config.cta_links.
- Не читай чужие article.html / live-сайт / уже опубликованные статьи сайта / topics.

## Handoff

```text
drafts/writer.html
=== EXCALIBUR BLOG WRITER ===
draft: meaning
next: Sol
incident_report: none | memory/pipeline-fix-queue.md#INC-...
```
