# Excalibur-2-Cloud Instructions

Язык: русский (тенант может сменить в `shared/tenant-config.json`).

## Первый запуск

Если `memory/setup/status.json` → `complete != true` **или**
`shared/tenant-config.json` → `setup_complete != true`:

→ работай как **`excalibur-blog-setup`** (skill `setup-excalibur-blog`).  
→ **Не** запускай Scout / Research / Publish.

См. `CLOUD-FIRST-RUN.md`, `SETUP.md`.

## Канон (после setup)

```text
Scout? → research_start → Research → Title → Writer(смысл)
→ Sol(слог) → Description(Дзен-карточка) → Cover-text || Schema → Cover
→ Indexer(llms) → Publish → Fixer → merge → Content-learner
```

**Writer** → `drafts/writer.html` (факты и смысл).  
**Sol** (`excalibur-blog-sol`) → финальный `article.html` слогом тенанта
(`shared/SOUL.md` + `shared/soul-examples/`).  
**Description** (`excalibur-blog-description`) → `description-brief.json`
(тизер карточки Дзена / RSS; `shared/dzen-description-rules.md`).  
≠ title, ≠ opening. После Description — stamp `pipeline_canon` + structural
checks. Прозу после Sol не переписывают (кроме возврата Sol при FAIL гейтов
слога; FAIL description → снова Description).

**Title** → `title-brief.json`.

Никто не читает уже опубликованные статьи сайта — только
`published-titles-only.md` / `shared/published-titles.md` для anti-dup.

`memory/topics/` запрещена. Scout → handoff + `signal_urls` + Wordstat
(из tenant / site-brief).

```bash
python3 scripts/excalibur_blog_research_start.py --topic-id B111 --title "…"
```

## Ошибка

- Второй автор / rewrite-loop **поверх Sol** (Sol — единственный стилевой рерайт)
- Термин-дамп / research-брифинг в открытии финала
- Description = title или обрезка лида (двойная карточка в Дзене)
- topics / SEO-хвосты
- Writer/Sol читают старые article.html / live-сайт как образец
- Publish без pipeline_canon stamp
- Scout/тема про RF-blocked heroes без Дзен-канона (если `dzen_rf_pack`)
- Sol выдумывает факты, которых нет в `drafts/writer.html` / research
- Запуск пайплайна до завершения Setup

## Preflight

**До Scout (если dzen_rf_pack):** прочитать `shared/dzen-content-rules.md` +
`shared/rf-blocked-entities.json`.

```bash
python3 scripts/excalibur_blog_doctor.py
python3 scripts/excalibur_blog_today.py
python3 scripts/excalibur_blog_research_start.py --topic-id <id> --title "<short>"
```

Директор: `.cursor/agents/excalibur-blog-director.md` (не Task).  
Setup: `.cursor/agents/excalibur-blog-setup.md` (не Task).
