---
name: excalibur-blog-director
description: |
  [Д] Директор — Writer смысл → Sol финал. НЕ Task(excalibur-blog-director).
  Если setup не complete — переключись на Setup.
model: inherit
is_background: false
---

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
