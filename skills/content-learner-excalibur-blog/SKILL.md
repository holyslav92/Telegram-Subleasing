---
name: content-learner-excalibur-blog
description: Evidence + Metrika → named lessons and durable improvements.
disable-model-invocation: true
---

# Excalibur BLOG — Content Learner v2

После publish/skip, до fixer. Evidence report optional under human-first-v2.

## Вход

- `content-evidence-report.json` schema v2 — **optional**;
- active `memory/content-lessons.md`;
- `shared/content-learning-contract.md`;
- `shared/content-evidence-contract.md`;
- `shared/pipeline-canon.json`.

## Порядок

1. Запусти content evidence gate:

   ```bash
   python3 scripts/excalibur_blog_content_evidence_gate.py \
     --article-dir <article_dir>
   ```

   - `status: SKIP` (нет файла) → **не BLOCK**. Продолжай.
   - `status: PASS` → используй named findings.
   - `status: BLOCK` (файл есть, но invalid) → `CONTENT EVIDENCE BLOCKER`
     + incident. Не invent'ить report/scorecards.
2. Сам выполни `excalibur_blog_metrika_fetch.py --days 30 --ingest`, затем
   прочитай свежий `memory/analytics/metrika-latest.json`.
   Metrika **обязательна** даже при evidence SKIP.
3. Credentials/API error = `METRIKA FEEDBACK BLOCKER` + incident.
4. Сопоставь named evidence findings с actionable Metrika signals. Low sample,
   слабая confidence или evidence SKIP → named note / low-confidence lesson,
   не причинный вывод и не CONTENT EVIDENCE BLOCKER.
5. Запиши lesson по v2 contract: evidence refs (или `none (skipped)`),
   named blockers, keep/change/never_again, proposed apply.
   При SKIP — optional/low-confidence lesson допустим.
6. Durable apply только при повторе evidence в ≥2 запусках или causal
   high-severity blocker. Запиши rollback.

## Запреты

- Не запускать LLM judge/ensemble.
- Не создавать/обновлять content-scorecard, automatic rating, overall,
  child/parent, weighted quality или score delta.
- Не выдумывать `content-evidence-report.json`, чтобы «закрыть» SKIP.
- Historical score files read-only.
- Не переписывать текущий `article.html`.
- Не добавлять новые правила в `shared/writer-master-prompt.md` или
  Writer agent/skill автоматически. Writer prompt защищён от разрастания;
  изменения только после явного решения человека.
- Learning proposals — в `memory/content-lessons.md` (review-only), не в Writer.

```text
=== EXCALIBUR BLOG CONTENT LEARNER ===
status:
topic_id:
article_dir:
evidence_gate: PASS | SKIP | BLOCK
metrika_feedback: PASS | BLOCKER
named_blockers:
lessons_recorded:
durable_applied:
rollback_check:
incident_report:
```
