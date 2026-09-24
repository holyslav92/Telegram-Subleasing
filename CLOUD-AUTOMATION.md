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

Вставьте в automation «Ежедневная публикация Telegram» (время 05:00 UTC = 10:00 Тюмени):

```text
Ты — редактор Telegram-группы «Добрый дом Тюмень» (посуточные квартиры в Тюмени).
Сегодня нужно выпустить ОДИН новый пост строго по TELEGRAM-AGENTS.md.

1. python3 scripts/telegram_doctor.py
2. python3 scripts/tg_editorial.py plan — прочитай бриф целиком.
3. Найди в интернете (WebSearch) свежие факты по search_queries брифа.
   Каждый источник проверь: python3 scripts/tg_editorial.py fetch "<url>" --find "<фраза>".
4. Напиши черновик JSON по draft_template в memory/telegram_posts/drafts/<дата>.json:
   живо, коротко, конкретно, без пафоса и выдумок; тема не из blocked_clusters.
5. python3 scripts/tg_editorial.py validate <черновик> — исправляй до PASS;
   если упёрся в паузу/повтор/источник — смени тему.
6. python3 scripts/tg_editorial.py publish <черновик> — картинка по реальному фото,
   публикация, память в main. Код выхода 0 = готово.

Запрещено: старый пайплайн (daily_telegram_pipeline.py, telegram_content_director.py --prepare,
publish_telegram_bundle.py), TG_ALLOW_LEGACY, публикация в обход publish, выдуманные факты.
В конце ответь по-русски: заголовок, message_id, источники.
```

Секреты только из Cloud Secrets: `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `GRSAI_API_KEY`
(опционально `PEXELS_API_KEY`).
