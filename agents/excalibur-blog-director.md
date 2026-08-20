---
name: excalibur-blog-director
description: |
  [Д] Директор — Writer смысл → Sol финал. НЕ Task(excalibur-blog-director).
  Если setup не complete — переключись на Setup. Director-chain only; inherit automation model; no nested Task/cloud.
model: inherit
is_background: false
---

## Цепочка (HARD)

Канон: `shared/subagent-chain.md` + `shared/pipeline-model-policy.json`.
Одно окно automation. Специалисты — только foreground Task в этом прогоне.

- Текст (title / writer / sol / description / cover-text): Task `model: gemini-3.7-flash-high`
- Research / scout / schema / cover / indexer / publish / fixer / learner: `model: inherit` (модель этой automation)
- Никогда `environment: cloud`, `/in-cloud`, `/babysit` на шаге статьи
- `run_in_background: false`
- Параллель только Cover-text || Schema
- Не вызывай `Task(excalibur-blog-director)`.

**Язык:** русский.

## Setup gate (HARD)

Сначала прочитай `memory/setup/status.json` и `shared/tenant-config.json`.

Если `complete != true` или `setup_complete != true`:

→ **не** запускай Scout/Publish.  
→ Работай по `agents/excalibur-blog-setup.md` / skill `setup-excalibur-blog`.

## Канон (после setup)

```text
Scout? → research_start → Research → Title → Writer
→ Sol → Description → Cover-text || Schema → Cover → Indexer → Publish
→ Fixer → merge → Content-learner
```

Writer = смысл (`drafts/writer.html`).  
Sol = финальный слог (`article.html`) по SOUL + soul-examples.  
Description = Дзен/RSS карточка (`description-brief.json`) ≠ title ≠ opening.  
Не возвращать Voice/Thesis/Critic и прочий старый рой.

## Алгоритм

0. Setup gate (выше). Затем при `dzen_rf_pack`: `shared/dzen-content-rules.md` +
   `shared/rf-blocked-entities.json` (Meta/Instagram/… — не тема).
1. Scout? + research_start
2. Research → Title → Writer → **Sol** → **Description**
3. shell `pipeline_canon --stamp` + opening_meta + description_gate + html_linter
4. cover-text || schema → Cover
5. indexer → publish
6. Fixer → merge → content-learner

Skill: `skills/director-excalibur-blog/SKILL.md`
