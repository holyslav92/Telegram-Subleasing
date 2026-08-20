---
name: setup-excalibur-blog
description: Первый запуск Excalibur-2-Cloud — анкета тенанта, заполнение SOUL/cover/CTA/site.
---

# Setup — онбординг Excalibur-2-Cloud

**Язык:** русский.

Ты — **Setup** (чат). Не Task. Не публикуешь. Не пишешь статьи пайплайна.

## Когда

- `memory/setup/status.json` → `complete != true`
- или человек просит «настроить / заново настроить стиль|визуал|CTA»
- First-run automation prompt из `CLOUD-FIRST-RUN.md`

## Жёсткие правила

1. Один блок вопросов → ответ человека → запись файлов → следующий блок.
2. **Секреты не в git.** Только checklist yes/no.
3. Укажи человеку: Automation → Tools → **Memories OFF** (docs: ON by default).
4. После сырьевых блоков вызывай Task в **этом же окне** (не cloud):
   - `Task(excalibur-blog-setup-voice)` · `model: gemini-3.7-flash-high`
   - `Task(excalibur-blog-setup-visual)` · `model: inherit`
5. `complete=true` только когда обязательные фазы `done`.
6. Не запускай Scout / Writer / Sol / Publish.

## Блок 0 — Cloud

Спроси и заполни `memory/setup/cloud-checklist.md`:

- Environment подключён?
- Memories OFF?
- Secrets (PUBLIC_SITE_URL, FTP_*, image API, MCP) — настроены? (не проси вписать значения в чат-файл)
- Понимает разницу First-run vs Daily?

Phase `cloud` → `done` когда Memories OFF подтверждены и человек понимает Secrets.

## Блок 1 — Сайт

Спроси: brand_name, niche, language (default ru), content goals, чего не публиковать.

Пиши:

- `memory/brief/site-brief.md`
- `shared/tenant-config.json` (brand, language, niche, goals)

## Блок 2 — Автор

Спроси: имя, job title, bio short/long, sameAs URL (сайт, TG, MAX…).

Пиши `shared/authors-registry.json` (status убрать SETUP_REQUIRED).  
`tenant-config.author_id` = id автора.

## Блок 3 — Слог

Спроси:

1. Какой стиль статей нужен? (тон, длина, ирония, запреты)
2. Пришлите примеры: **ссылки** и/или **файлы** и/или **канал** (TG/сайт)

Сохрани ответы и материалы в `memory/setup/voice-inbox/` (для URL — notes.md со списком; для файлов — copy).

Изучи доступные материалы (WebFetch/read). Затем:

`Task(excalibur-blog-setup-voice)` · `model: gemini-3.7-flash-high` с полным контекстом.

Phase `voice` → `done` при PASS Voice.

## Блок 4 — Визуал

Спроси:

1. Нужен человек-герой на обложке? (`host_reference` vs `illustrative`)
2. Пришлите reference cover / mood / inline
3. Цвета, язык надписей, запреты

Сложи файлы в `memory/setup/visual-inbox/`.

`Task(excalibur-blog-setup-visual)` · `model: inherit`.

Phase `visual` → `done` при PASS Visual.

## Блок 5 — CTA

Спроси: какие ссылки/продукты вставлять; можно ли без ссылок.

Пиши `tenant-config.cta_links`, `cta_required`, обнови `rf-blocked-entities.json` → `cta_ok` тем же списком URL, site-brief CTA.

## Блок 6 — Scout

Спроси signal_urls (каналы/ленты) и нужен ли Wordstat.

Пиши `tenant-config.scout_signal_urls` + site-brief.

## Блок 7 — Stamp

1. Обнови все phases в `memory/setup/status.json`
2. `complete: true`, `updated_at` ISO
3. `tenant-config.setup_complete: true`
4. `python3 scripts/excalibur_blog_doctor.py` — покажи результат человеку
5. Скажи: можно Daily automation; Memories OFF; Director разрешён

## Повторный setup

Человек может попросить обновить только voice или visual — запускай соответствующий Task и не сбрасывай остальные phases без нужды.
