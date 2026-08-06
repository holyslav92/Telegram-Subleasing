# Excalibur-2-Cloud — карта задач

Директор и Setup **не** Task.

```text
[S] Setup (чат) — если !setup_complete
  ├─ блоки 0–7
  ├─ Task: setup-voice
  └─ Task: setup-visual

[Д] Директор (чат) — только если setup_complete
  ├─ Scout (needs_scout)
  ├─ shell: today + research_start (+ titles-only)
  ├─ Research → Title → Writer → Sol → Description
  ├─ shell: pipeline_canon --stamp + opening_meta + description_gate + html_linter
  ├─ Cover-text || Schema → Cover
  ├─ Indexer (llms only) → Publish
  └─ Fixer(open) → merge_to_main → Content-learner
```

## Кто трогает текст

| Роль | Проза |
|------|-------|
| **Writer** | Смысл → `drafts/writer.html` |
| **Sol** | Слог → финальный `article.html` (+ `drafts/variant-a.html`) |
| **Title** | Только H1 в brief |
| **Description** | Только тизер карточки → `description-brief.json` (не body) |
| `pipeline_canon --stamp` | meta only, **0** переписки |
| Cover | Только `<figure>` |

## Правила

1. Title → `title-brief.json`
2. Writer → `drafts/writer.html`
3. Sol → `article.html` (SOUL + soul-examples; факты из Writer)
4. Description → `description-brief.json` (`shared/dzen-description-rules.md`)
5. `python3 scripts/excalibur_blog_pipeline_canon.py --article-dir … --stamp`
6. Cover-text → Cover; Indexer; Publish
