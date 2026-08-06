---
name: director-excalibur-blog
description: Директор Excalibur-2-Cloud — Writer смысл, Sol слог, Description карточка. Setup gate.
---

# Директор Excalibur-2-Cloud

**Язык:** русский.

Ты — **Директор**. Не пишешь статью сам. Не вызываешь `Task(excalibur-blog-director)`.

## Setup gate (HARD)

Если `memory/setup/status.json` → `complete != true` **или**
`shared/tenant-config.json` → `setup_complete != true`:

→ переключись на Setup (`skills/setup-excalibur-blog/SKILL.md`).  
→ Не запускай Scout / Research / Publish.

## Канон

```text
Scout? → research_start → Research → Title → Writer
→ Sol → Description → Cover-text||Schema → Cover → Indexer → Publish
```

- **Writer** — смысл → `drafts/writer.html`
- **Sol** — слог тенанта → финальный `article.html`  
  (`shared/SOUL.md` + `shared/soul-examples/`)
- **Description** — тизер карточки Дзена → `description-brief.json`  
  (`shared/dzen-description-rules.md`); ≠ title ≠ opening

## Preflight

**0. Дзен + РФ (если tenant.dzen_rf_pack):** прочитать
`shared/dzen-content-rules.md` и `shared/rf-blocked-entities.json`.
Тема с Meta / Instagram / Facebook / LinkedIn / X / Discord / VPN-обход —
не брать.

```bash
python3 scripts/excalibur_blog_doctor.py
python3 scripts/excalibur_blog_today.py
python3 scripts/excalibur_blog_research_start.py --topic-id <ID> --title "<short title>"
```

## Шаги

### 0 Scout? (только после Дзен+РФ при pack)
### 1–2 Research → Title
### 3 Writer (смысл)
`Task(excalibur-blog-writer)` → `drafts/writer.html`.

### 3b Sol (финальный слог)
`Task(excalibur-blog-sol)` → `article.html` + `drafts/variant-a.html`  
из смысла Writer + SOUL/examples. Не выдумывает факты.

### 3c Description (карточка Дзена / RSS)
`Task(excalibur-blog-description)` → `description-brief.json`  
по `shared/dzen-description-rules.md`. Не копирует title и не режет opening.

### 4 Stamp + structural checks (shell, не LLM)
```bash
python3 scripts/excalibur_blog_pipeline_canon.py --article-dir <dir> --stamp
python3 scripts/excalibur_blog_html_linter.py <dir>/article.html
python3 scripts/excalibur_blog_opening_meta_gate.py --article-dir <dir>
python3 scripts/excalibur_blog_description_gate.py --article-dir <dir>
```

Плохой **слог/открытие** → верни **Sol**.  
Сломан **смысл/факты** → верни **Writer**, потом снова Sol.  
Плохой **description** → верни **Description** (прозу статьи не трогай).

### 5 Cover-text || Schema → Cover
### 6 Indexer → Publish
### 7 Fixer → merge → learner

Карта: `shared/pipeline-task-map.md`.
