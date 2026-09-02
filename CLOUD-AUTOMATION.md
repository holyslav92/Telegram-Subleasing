# Excalibur-2-Cloud — Cloud Automation (Daily)

**Только после** `memory/setup/status.json` → `complete: true`.

Одно окно: эта automation = **Директор**. Не поднимай второй Cloud Agent
на Writer/Sol/Cover (`/in-cloud`, `environment: cloud` запрещены).
Цепочка: `shared/subagent-chain.md`. Модели: `shared/pipeline-model-policy.json`.
Cursor: `docs/cursor/README.md`.

Модель, выбранная в UI automation, идёт на Директора, Research, Scout,
Cover (картинки), Publish. Текст статьи всё равно пишет **Gemini 3.7 Flash**.

## Канон

```text
Scout? → research_start → Research → Title → Writer → Sol
→ Description → Cover-text||Schema → Cover → Indexer → Publish
→ Fixer → merge → Content-learner
```

Writer = смысл (`drafts/writer.html`). Sol = финальный слог тенанта.
Description = тизер карточки ≠ title ≠ opening.

## Automation prompt

```text
Прочитай AGENTS.md + shared/subagent-chain.md + shared/pipeline-model-policy.json
+ shared/pipeline-canon.json + shared/tenant-config.json.
Ты Директор в ЭТОМ окне. Не /in-cloud, не environment:cloud, не isolated worktree.
Специалисты только foreground Task; они не запускают свой пайплайн.
Текст (title/writer/sol/description/cover-text): Task model gemini-3.7-flash-high.
Research/scout/schema/cover/indexer/publish/fixer: model inherit.
Если setup_complete != true — остановись и запусти Setup (см. CLOUD-FIRST-RUN.md).
Игнорируй Automation Memory. Memories в Tools = OFF.

doctor + today.
Если dzen_rf_pack: прочитай shared/dzen-content-rules.md + rf-blocked-entities.json.
needs_scout → Scout (signal_urls из tenant + Wordstat; не RF-DENY heroes).
research_start --topic-id … --title "…".
Research (inherit) → Title (Gemini) → Writer (Gemini) → Sol (Gemini) → Description (Gemini).
shell после Description:
  python3 scripts/excalibur_blog_pipeline_canon.py --article-dir … --stamp
  + opening_meta / description_gate / html_linter.
Cover-text (Gemini) || Schema (inherit) → Cover (inherit); Indexer; Publish; merge; content-learner.
```

## Telegram Daily Automation Prompt

```text
Ты Директор ежедневного SMM-пайплайна сети апартаментов «Добрый дом Тюмень».
Запусти:
python3 scripts/daily_telegram_pipeline.py

Если возникла ошибка выполнения или генерации:
1. Запусти субагента-Фиксика (excalibur-blog-fixer), чтобы он локализовал причину ошибки (промпт, параметры API, конфигурация), устранил баг в файлах проекта и перезапустил генерацию.
2. Фиксик обязан решить проблему и довести публикацию до выхода полноценного качественного поста.
3. Категорически запрещено отправлять в канал 'сухой' пост без фото или с одиночным логотипом. Если после всех попыток изображение не готово — пост отменяется.
```

Секреты только из Cloud Secrets.
