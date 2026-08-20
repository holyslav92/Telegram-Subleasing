---
name: director-excalibur-blog
description: Директор Excalibur-2-Cloud — одно окно, цепочка Task. Writer смысл, Sol слог, Description карточка. Setup gate.
---

# Директор Excalibur-2-Cloud

**Язык:** русский.

Ты — **Директор**. Не пишешь статью сам. Не вызываешь `Task(excalibur-blog-director)`.
Канон запуска: `shared/subagent-chain.md` + `shared/pipeline-model-policy.json`.
Не `/in-cloud`, не `environment: cloud`, не isolated worktree.

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
`Task(excalibur-blog-scout)` · `model: inherit` · foreground.
### 1–2 Research → Title
`Task(excalibur-blog-research)` · `model: inherit`.  
`Task(excalibur-blog-title)` · `model: gemini-3.7-flash-high`.
### 3 Writer (смысл)
`Task(excalibur-blog-writer)` · `model: gemini-3.7-flash-high` → `drafts/writer.html`.

### 3b Sol (финальный слог)
`Task(excalibur-blog-sol)` · `model: gemini-3.7-flash-high` → `article.html` + `drafts/variant-a.html`  
из смысла Writer + SOUL/examples. Не выдумывает факты.

### 3c Description (карточка Дзена / RSS)
`Task(excalibur-blog-description)` · `model: gemini-3.7-flash-high` → `description-brief.json`  
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
В одном сообщении (параллель):  
`Task(excalibur-blog-cover-text)` · Gemini; `Task(excalibur-blog-schema)` · inherit.  
Потом `Task(excalibur-blog-cover)` · inherit. Cover **не** зовёт Cover-text.
### 6 Indexer → Publish
`model: inherit`.
### 7 Fixer → merge → learner
`model: inherit`.

Карта: `shared/pipeline-task-map.md`.
