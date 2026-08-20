---
name: setup-visual-excalibur-blog
description: Синтез cover prompt-системы из референсов тенанта.
disable-model-invocation: true
---

# Setup Visual

См. `agents/excalibur-blog-setup-visual.md`.

Кратко:

1. Прочитай visual-inbox + cover_mode.
2. Скопируй assets в `memory/cover/assets/`.
3. Заполни blog-hero.json, cover-design-code.json, quad-style-*.json.
4. Обнови tenant-config cover fields.
5. Никаких чужих дефолтных лиц/брендовых коллажей.
6. Handoff PASS или NEED_MORE_REFS.
