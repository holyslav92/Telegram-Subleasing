---
description: Excalibur-2-Cloud — живой прогон статьи через оркестратор и субагентов.
---

# Excalibur-2-Cloud — запуск пайплайна

Сначала: `memory/setup/status.json` → `complete: true`. Иначе — Setup.

«Запусти Excalibur для темы **B01**»

Это **одно окно Директора**. Не `/in-cloud`. Специалисты — foreground Task.
Текст: Gemini 3.7 Flash. Research/картинки: модель automation.

## Параметры

- `topic_id`: B01 | all | P0-only
- `publish`: yes | no (default yes)

## Пайплайн

```text
Scout? → Research → Title → Writer → Sol → Description → Cover||Schema
→ Indexer → Publish
```

Writer / Sol / Title / Description / Cover-text — Gemini 3.7 Flash.
Research / Cover / Publish — модель automation. Не читать тела старых статей.
Publish BLOCK без setup / без pipeline_canon stamp.

Оркестратор: `skills/director-excalibur-blog/SKILL.md`.
