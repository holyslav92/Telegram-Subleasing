# Excalibur-2-Cloud — карта задач

Директор и Setup **не** Task. Цепочка в **одном окне**:
`shared/subagent-chain.md`, модели `shared/pipeline-model-policy.json`.

```text
[S] Setup (чат, inherit) — если !setup_complete
  ├─ блоки 0–7
  ├─ Task: setup-voice   (Gemini 3.7 Flash)
  └─ Task: setup-visual  (inherit)

[Д] Директор (чат, inherit) — только если setup_complete
  ├─ Scout (needs_scout)          inherit
  ├─ shell: today + research_start (+ titles-only)
  ├─ Research (inherit) → Title (Gemini) → Writer (Gemini)
  │    → Sol (Gemini) → Description (Gemini)
  ├─ shell: pipeline_canon --stamp + opening_meta + description_gate + html_linter
  ├─ Cover-text (Gemini) || Schema (inherit) → Cover (inherit)
  ├─ Indexer (llms only) → Publish                 inherit
  └─ Fixer(open) → merge_to_main → Content-learner inherit
```

## Кто трогает текст

| Роль | Проза |
|------|-------|
| **Writer** | Смысл → `drafts/writer.html` (Gemini) |
| **Sol** | Слог → финальный `article.html` (+ `drafts/variant-a.html`, Gemini) |
| **Title** | Только H1 в brief (Gemini) |
| **Description** | Только тизер карточки → `description-brief.json` (не body, Gemini) |
| **Cover-text** | Только русские надписи (Gemini) |
| `pipeline_canon --stamp` | meta only, **0** переписки |
| Cover | Только `<figure>` |

## Правила

1. Title → `title-brief.json`
2. Writer → `drafts/writer.html`
3. Sol → `article.html` (SOUL + soul-examples; факты из Writer)
4. Description → `description-brief.json` (`shared/dzen-description-rules.md`)
5. `python3 scripts/excalibur_blog_pipeline_canon.py --article-dir … --stamp`
6. Cover-text → Cover; Indexer; Publish
