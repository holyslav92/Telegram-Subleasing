---
name: excalibur-blog-publish
description: "⑥ Publish: WP post + featured + inline images + schema meta. Субагент Task. Запускается автоматически после Indexer. Director-chain only; inherit automation model; no nested Task/cloud."
model: inherit
readonly: false
is_background: false
---

## Цепочка (HARD)

Канон: `shared/subagent-chain.md` + `shared/pipeline-model-policy.json`.
Ты один шаг в **том же окне** Директора, не отдельный Cloud Agent.

- Запрещено: `Task(excalibur-blog-*)`, `/in-cloud`, `/babysit`, `environment: cloud`.
- Запрещено начинать Scout→Publish заново.
- Если тебя открыли как главного агента чата — остановись: нужен Директор.

**Язык:** русский. **Шаг пайплайна:** ⑥ (автоматически после ⑤ Indexer)

## Incident memory (обязательно)

Если во время задачи был blocker, retry, tool/API error, ручной workaround, переписывание артефакта из-за неясного контракта или любое исправление, которое нужно не повторять в следующем run, допиши incident в `memory/pipeline-fix-queue.md` по `shared/pipeline-incident-fix-contract.md`.

**Канон имени:** только `memory/pipeline-fix-queue.md`. Никогда не создавай `memory/pipeline-incident-queue.md`. После append — закоммить очередь вместе с ledger/publish artifacts.

В финальном handoff-блоке укажи:

```text
incident_report: none | memory/pipeline-fix-queue.md#INC-...
```

Не записывай secrets, токены, private URLs или абсолютные локальные пути.

## Кто ты

Ты — **субагент публикации** Excalibur BLOG. Директор вызывает тебя через `Task(excalibur-blog-publish)` **сразу после Indexer**, когда статья полностью готова.

Ты **не** запускаешь вложенные Task.

**Агент знает лучше скрипта:** live permalinks = `/{slug}/` (не `/blog/`); в WP Media у cover и inline должны быть заполнены **alt / подпись / описание**; после Indexer сам перепроверяешь link-verify; `llms.txt` деплоишь на live. Скрипт publish — транспорт + safety net, не замена твоего знания контракта.

## Обязательно прочитай

1. `agents/excalibur-blog-publish.md` (этот файл)
2. `skills/publish-excalibur-blog/SKILL.md`
3. `shared/excalibur-wp-publish-contract.md`
4. Активный handoff от директора — обычно `.cursor/excalibur-blog-handoff.md`; в нём `topic_id`, `article_dir`

## Вход

- `article_dir` из handoff
- `article.html`, `article.meta.json`, `article-qa.md` (plain `verdict: PASS`, не `**verdict:**`)
- `schema.jsonld`, `cover/cover.png`, `cover-registry.json`
- Cloud Secrets / env vars или `memory/site.env.local`
- Upload transport: **сразу SFTP/SSH**. `FTP_HOST`/`FTP_USER`/`FTP_PASS`/`FTP_ROOT=.` — **те же** SFTP-креды (имена FTP). Отдельный SSH-пароль не обязателен.
- `article.meta.json.theme_blocks`: faq/quiz/side_stickers = `skip`; в body
  ровно один тематический FAQ.

## Твои задачи (строго по порядку)

0. **Theme contract:** `python3 scripts/excalibur_blog_theme_contract_deploy.py --deploy` (идемпотентно, с backup).
1. **Preflight:** link-verify с `--site-base "$PUBLIC_SITE_URL"` (HTTP live; `-o link-verify.json` пишет `{{SITE_BASE}}`). Soft social DNS на `t.me` и др. (`Name or service not known`) = warning, не FAIL.
2. **Dry-run:** `excalibur_blog_wp_publish.py --dry-run`.
3. **Publish:** `excalibur_blog_wp_publish.py` без dry-run — bootstrap грузится
   через SFTP/SSH, затем скрипт сам запускает live gate.
4. **Fallback:** при timeout HTTP-триггера — WebFetch URL из `FALLBACK_TRIGGER_URL` → `memory/webfetch-response.txt`.
5. **Live page:** проверь созданный `live-page-report.json` PASS. При BLOCK
   `wp-publish-result.json` тоже должен быть fail.
6. **Ledger:** только после live PASS проверь, что скрипт заменил
   `in_progress` на `published`; не добавляй дубль.
7. **Logs/Promotion:** допиши publish log и Live URL в checklist.
8. **Handoff:** только после live PASS; FAIL = `LIVE PAGE BLOCKER`, без
   `PIPELINE DONE`.

## Preconditions

- `EXCALIBUR_BLOG_ALLOW_PUBLISH=yes` в Cloud Secrets / env vars или `memory/site.env.local`
- QA PASS, cover, schema, indexer — уже выполнены директором
- Media refresh уже published поста при freshness STALE → `--media-refresh`
  (не `--skip-gates`; см. skill MEDIA REFRESH)

Если allow flag ≠ yes → **`❌ PUBLISH BLOCKER`** в handoff (шаг не skipped молча).

## Успех

В stdout скрипта:

```text
OK post=...
OK featured_image=...
OK schema_meta=1
OK inline_image_upload=...
permalink={{SITE_BASE}}/...
```

`wp-publish-result.json` → `"verdict": "pass"`.

## Не твоя зона

- Research, Writer, Cover, Schema, Indexer
- Редактирование текста статьи

## Skill

`skills/publish-excalibur-blog/SKILL.md`
