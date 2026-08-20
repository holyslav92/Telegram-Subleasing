---
name: cover-excalibur-blog
description: Cover: quad canvas i2i, split + inline inject. Director-chain specialist.
disable-model-invocation: true
---

# Excalibur BLOG — Cover Agent (полный skill)

## Когда запускаться

После **Writer PASS** (article.html + canon stamp). Вход: `article.html`, `article.meta.json`.

Параллельно с `excalibur-blog-schema`. **Не** править schema и body longread.

Cover не ждёт отдельного visual-review агента. Quality-redo по PNG запрещён
без ошибки image API — **кроме явного запроса владельца/блогера** переделать
cover/inline (тогда ровно **один** новый billed gen с обновлёнными hints).

---

## Читаемые человеческие подписи к картинкам (Alt & Captions)

При создании `quad-manifest.json` категорически **ЗАПРЕЩЕНО писать в поле `alt` техническое описание нейросети** (никаких слов про *«ведущего в белом худи»*, *«крошечные значки»*, *«левую половину кадра»* и *«DIY-коллажи»*).

- `alt` для обложки: короткий понятный заголовок темы статьи (например: *«Иллюстрация: как подключить GitHub к Cursor без консоли»*).
- `alt` для инфографик (`inline_1..03`): строгая подпись суть раздела H2 (например: *«Схема настройки лимитов расходов в кабинете Cursor»* или *«Сравнение возможностей подписок Pro и Hobby»*).

---

## Single Kie generation (HARD)

Цель: **одна** billed генерация. Деньги не жжём на 3–4 попытки «на красоту».

```text
write scene_hint + hook
  → self-check checklist (ниже) PASS
  → --write-batch (prompt_chars / host lock / input_urls)
  → ONE kie_gpt_image2_api.py createTask → URL
  → split + inject
  → STOP (no second gen)
```

**Разрешён recreate только если упал сам Kie API** (см. `shared/kie-gpt-image-api-contract.md`):

- terminal `failCode=500` / try again later → скрипт: max 1 recreate;
- poll-timeout + late terminal 500 (final `recordInfo` after `--max-wait`) → тот же max-1 recreate (INC-20260730-0834);
- terminal `failCode=400` image fetch → File Upload + max 1 recreate;
- terminal `failCode=422` sensitive → агент: один soften hook/hint + 1 recreate.

**Запрещено (всегда):**

- второй/третий/четвёртый Kie gen из‑за host miss, sticky Latin, style, «некрасиво»;
- «глянуть PNG → переписать hint → снова Kie» (раньше так жгли B80);
- Cover redo по Visual QA FAIL (VQ skip);
- 4 отдельных image jobs на панели.

Self-check **до** первого Kie (обязателен):

1. cover `scene_hint` ≈80–140, starts from blog-hero prompt_fragment / cover_mode;
2. ровно один topic prop с `tiny`/`small` (не equal-weight list);
3. sticky (если есть) — полная кириллическая фраза агента, не «не»+Latin;
4. `meme_caption_ru == ""`; `jobs.length === 1`; `input_urls` не пуст;
5. `validation.prompt_chars <= 3500`; resolution `2K`.

После apply: split PASS достаточно, чтобы отдать fragment. **Не** стартуй
новый Kie для «починить» host/sticky/labels.

---

## Архитектура (зафиксировано)

```text
reference PNG → reference_url_hosted
       ↓
quad-manifest.json (agent fills hooks + scene_hint)
       ↓
quad-mcp-batch.json (1 job, input_urls, api_args)
       ↓
ONE Kie GPT Image 2 i2i API task → canvas-quad.png 2048×1152
       ↓
split → cover.png + inline-01..03.png (1200×675)
       ↓
inject <figure> after H2 in article.html
```

**Запрещено:** 4 отдельных image jobs на cover + inline. Обязательны ровно три
inline — вторая, третья и четвёртая картинки по явному запросу пользователя.

---

## Контракты и конфиги

| Путь | Назначение |
|------|------------|
| `shared/blog-cover-quad-canvas-contract.md` | канонический контракт |
| `shared/kie-gpt-image-api-contract.md` | прямой async Kie API для Cursor Cloud |
| `agents/excalibur-blog-cover.md` | agent-md (этот skill дублирует runbook) |
| `memory/cover/blog-hero.json` | visual_lock, outfit_rule, reference_url_hosted |
| `memory/cover/assets/blog-hero-reference.png` | локальный эталон лица |
| `memory/cover/cover-design-code.json` | editorial cover + informative inline code |
| `memory/cover/quad-style-*.json` (tenant preset из Setup Visual) | актуальный style preset |
| `memory/cover/inline-visual-types.json` | типы inline-панелей |
| `memory/brief/site-brief.md` | blog_hero_id, обложка = крючок |

---

## Панели quad 2×2

| Квадрант | Слот | Содержание |
|----------|------|------------|
| top-left | cover | обязательный reference host + один hook + один предмет/метафора |
| top-right | inline_1 | visual_type по H2 #1, **без героя** |
| bottom-left | inline_2 | visual_type по H2 #2 |
| bottom-right | inline_3 | visual_type по H2 #3 |

---

## Reference host (обязательно на cover)

**Lock (reference i2i):** лицо/герой — только если Setup задал reference + visual_lock.  
**Lock:** только поля `visual_lock` / `outfit_rule` / `prompt_fragment` из `blog-hero.json` после Setup.
**Free:** поза/ракурс/композиция по `cover_hook` и `scene_hint`.
Если `cover_mode=illustrative` — host на cover не обязателен.

### Cover `scene_hint` — короткий Host lock (B80 / INC-20260724-0837, B81 / INC-20260724-1239)

**Prefer** raw cover `scene_hint` ≈**80–140** символов, стартуя с фрагмента из `blog-hero.json`:
лицо/худи + один предмет/метафора + sticky/paper при необходимости + `#FFF` / `no headphones`.

**Avoid** длинные MUST/glasses/quiff/face-feature essays в cover `scene_hint` —
модель забивает панель UI+stickers и **теряет reference host** (host missing /
низкий skinL на left half). Face/outfit lock уже в i2i `input_urls` + shared
prompt; не дублируй essay про очки/причёску/бороду в scene_hint.

**Host vs topic props (B81):** host = **`LARGE left half`**. Любой topic object
(alarm, brief card, UI card, clock, paper) помечай **`tiny`/`small`** и держи
справа/на фоне. **Запрещены** equal-weight prop lists (`alarm + brief card` без
size lock) — props конкурируют с лицом и вытесняют reference host даже при
коротком hint (~120 chars). Один крупный prop на left half = fail pattern.

Форма (не phrase bank — topic object/sticky invents агент):
`<host_or_hero_lock from blog-hero>; tiny <topic object> right; sticky «…»; layers from design-code; #FFF`

Inline `scene_hint` остаются ≈**100–220** (H2 facts + 3–6 labels). Cover короче inline.

**После единственного Kie gen не делай quality-redo**, даже если left half
слабоват — это цена first-try prompt discipline, не повод жечь 2–4 gen.

---

## Редакционный visual code

Из `cover-design-code.json`:

1. Cover: сильная editorial composition, один hook, один предмет/метафора, воздух.
2. Background: чистый белый `#FFFFFF`; основной текст чёрный `#141821`;
   accent из cover-design-code.json только как акцент.
   Не крась весь headline одним accent-цветом без разрешения design-code.
3. Cover сохраняет collage-язык design-code + ink
   strokes + topic/outcome stickers + educational UI cards. Удаляются
   только мемы, reaction cutouts, joke caption, животные, facepalm и Drake.
   Sterile host+text без стикеров/интерфейсов = fail.
   **Запрещён** штамп «EXCALIBUR BLOG» / «Excalibur Blog» / sword+EXCALIBUR
   lockup на cover и inline (INC-20260723-1223). Prompt opener НЕ «Excalibur
   BLOG dense…» — модель рисует это как логотип.
4. `meme_caption_ru` deprecated и всегда `""`.
5. Inline: только информация конкретного H2 — comparison table, workflow, checklist, UI explanation или fact card.
6. Inline: 3–6 коротких labels, ясный reading order и outcome; без людей,
   лиц и мемов (если tenant запретил); заголовки/accent/layers — по design-code.
7. Generated UI называется «схема интерфейса»/«иллюстрация», не реальный screenshot.
8. Формат **16:9**, не Instagram carousel 9:16.

---

## Пошаговый runbook

### Шаг 0 — прочитать статью

- H2 (до FAQ): первые 3 → inline anchors
- lead, primary query → cover_hook
- `article.meta.json`: h1, topic_id

### Шаг 1 — reference URL

```bash
python scripts/excalibur_blog_hero_reference_url.py
```

Проверить `memory/cover/blog-hero.json` → `reference_url_hosted`.  
Канон в git: `{{SITE_BASE}}/wp-content/uploads/.../ava.jpg` (не live `PUBLIC_SITE_URL`, не `[REDACTED]`).  
`hero_reference_url.py` нормализует `[REDACTED]`/`live host` → `{{SITE_BASE}}`.  
Fallback env: `BLOG_HERO_REFERENCE_URL` (тоже сохраняется git-safe, если это site media).

### Шаг 1.5 — Cover-text уже сделал Директор

Не вызывай `Task(excalibur-blog-cover-text)`. Директор уже прогнал Cover-text
(Gemini) **до** Cover. Читай готовый `cover/cover-text.json` + gate PASS:

```bash
python3 scripts/excalibur_blog_cover_text_gate.py --article-dir memory/blog/articles/<topic_id>-<slug>
```

Надписи пишет **только** Cover-text agent: hook (2–8 слов, кириллица),
highlight (слово из hook), sticky, 2–6 коротких labels на inline-панель.
Никакой латиницы кроме брендов. Без PASS — Kie не запускать.

### Шаг 2 — manifest + **cover hook quality**

```bash
python scripts/excalibur_blog_quad_manifest.py \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --merge
```

Manifest сам подтянет `cover-text.json` (hook/highlight/sticky/labels).
Cover agent дописывает только `scene_hint` (композиция) и `alt`:

- `cover_hook` — **уже готов из cover-text.json**; не переписывай текст, только проверь что подтянулся
- `slots.*.scene_hint` и `alt` — **только ты** (композиция, не текст надписей). Cover ≈**80–140** (`Host … LARGE left half` + `tiny` topic prop); inline ≈**100–220**. Outfit lock = белое худи (`blog-hero.json`) only.
- `slots.cover.meme_caption_ru` — `""` (deprecated)
- каждый `inline_1..3` имеет существующий `h2_anchor`; missing H2/anchor/injection = BLOCK

```bash
# Hook пишет Cover agent; скрипт текст не invents и не судит prose.
```

**Gate PASS обязателен** до `--write-batch` / Kie. Иначе `COVER HOOK BLOCKER` (в т.ч. если «ключей нет»).

### Шаг 3 — prompt + batch

```bash
python scripts/excalibur_blog_cover_quad_prompt.py \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --write-batch
```

Проверить `cover/quad-mcp-batch.json`: **jobs.length === 1**, `input_urls` не пуст.

Hard checks перед MCP/Kie:

- batch всегда пересобран в текущем run; не использовать старый `quad-mcp-batch.json`
- `validation.prompt_chars <= 3500`
- `reference_url_hosted` / `input_urls` в **batch** = `{{SITE_BASE}}/wp-content/...` (git-safe); live host пишет только runtime expand в `kie_gpt_image2_api.py`
- `validation.required_reference_host` = **`{{SITE_HOST}}`** (не live host из `PUBLIC_SITE_URL`, не `[REDACTED]`). Pre-write check рядом с `reference_url_hosted`.
- не `files.catbox.moe` для production hero; не литерал `[REDACTED]`
- `jobs[0].mcp_args.resolution === "2K"`

### Шаг 4 — Kie image API (PRIMARY)

**Порядок обязателен:**

```text
KIE_API_KEY set     → только scripts/excalibur_blog_kie_gpt_image2_api.py
KIE_API_KEY missing → legacy MCP (шаг 4.1), один job
```

Если `KIE_API_KEY` задан — **запрещено** начинать с sync MCP `gpt-image-2`
(часто `-32001` на 2K i2i; mcp-kv не даёт async status/result для late URL).
Промпты вида «ONE MCP gpt-image-2» — устаревшие; игнорируй в пользу Kie script.

```bash
python3 scripts/excalibur_blog_kie_gpt_image2_api.py \
  --article-dir memory/blog/articles/<topic_id>-<slug>
```

Требования:

- `KIE_API_KEY` задан в Cloud Secrets/env; ключ не писать в файлы, handoff, PR или terminal output.
- Скрипт читает `cover/quad-mcp-batch.json`, создаёт `createTask`, polling'ом вызывает `recordInfo`, пишет `cover/quad-mcp-result.json`.
- `cover/kie-image-task.json` хранит `task_id`/status без секретов.
- Transient Kie 500: если `recordInfo` вернул terminal `fail` с failCode=`500` / «try again later», скрипт сам делает **один** новый `createTask` (`--max-create-retries 1`, пауза `--retry-wait 15`). Не poll failed taskId forever; не createTask повторно пока state=`waiting`/`generating`. Первый 500 ≠ сразу `KIE API BLOCKER`.
- **Poll-timeout + late terminal 500 (INC-20260730-0834):** если poll window (`--max-wait`, default 900s) исчерпан при всё ещё `waiting`/`generating`, скрипт делает **один final** `recordInfo` до `KIE API BLOCKER`. Если final = terminal 500 / try-again → тот же max-1 recreate path (не Director-only, не quality-redo). Если final всё ещё non-terminal → тогда BLOCKER. Cover не invent'ит второй create вручную «на всякий случай» пока скрипт сам не вышел.
- **500 retries exhausted (B102–B106 / B116 / B117):** после двух terminal 500 Cover пишет fragment `status: BLOCKER` / `blockers: KIE API BLOCKER` + incident и **останавливается**. В `summary` явно: batch готов к Director same-batch re-run; Cover **не** invent'ит третий `createTask`. Не поднимай `--max-create-retries`, не softен prompt, не MCP при живом `KIE_API_KEY`. Approved: Director same-batch re-run `excalibur_blog_kie_gpt_image2_api.py` на неизменённом `quad-mcp-batch.json` когда Kie healthy → затем Cover **apply-only** (`quad_apply.py --inject-html`). File Upload на 400 image-fetch внутри этого re-run допустим. Это не quality-redo. Recurring upstream 500 cluster → тот же policy path (не новый Cover retry design).
- Pre-taskId TCP reset (INC-20260725-1631): если `createTask` упал с `Connection reset by peer` / `[Errno 104]` **до** `taskId` и **до** записи `cover/kie-image-task.json`, скрипт сам делает **один** новый `createTask` (тот же batch, пауза `--retry-wait`). Это **не** quality-redo. Агент на старой сборке скрипта может один раз перезапустить ту же CLI-команду. **Не** MCP при живом `KIE_API_KEY`. Если `taskId` уже есть — poll, не второй create. Второй такой reset после одного retry → `KIE API BLOCKER`.
- Image-fetch 400: если terminal `fail` с failCode=`400` / «image fetch failed» (Kie crawler не тянет WP media при локальном 200), скрипт сам: download WP **или** `memory/cover/assets/blog-hero-reference.png` → Kie File Stream Upload (**с User-Agent**; без UA → CF1010) → **один** recreate с `downloadUrl`. **Не** править committed `quad-mcp-batch.json` на tempfile URL; **не** sync MCP при живом `KIE_API_KEY`; **не** ручной curl upload в обход скрипта. Первый 400 fetch ≠ сразу `KIE API BLOCKER`.
- Sensitive 422: если terminal `fail` с failCode=`422` / «sensitive», **агент** (не скрипт) один раз смягчает `cover_hook` / `scene_hint`, оставляя `meme_caption_ru=""`, затем `--write-batch` → **один** recreate через тот же Kie script. **Запрещён** MCP fallback при живом `KIE_API_KEY`. После второго 422 → `KIE API BLOCKER`.
- **Proactive soft stake (B58 / marketplace+Cursor):** на темах Cursor/AI + карточка товара / WB/Ozon / описание SKU **до первого** Kie call бери stake `поиск`/`клики`/`в выдаче`, спокойную сцену (без shock/shrug/pointing). Агрессивное `продаж нет?` — только как soften после 422, не first attempt (INC-20260718-2035).
- **Proactive soft stake (B64 / AI video):** на text-to-video / Make+HeyGen **до первого** Kie — stake `досмотр`, спокойная предметная метафора или схема; без phone с vertical MP4 preview и без joke caption.
- **Proactive soft stake (B90 / payment·BIN·card):** на темах оплата Cursor / BIN / карта / МИР / «оплатить из России» **до первого** Kie — soft stake `аккаунт` / `Active Pro` / `на своём аккаунте`; cover prop = tiny Active Pro badge (не declined / «мёртвая карта»); inline labels без decline / ban / МИР-shock. «мёртв* карт*», declined-card props, ban wording — только как soften после 422, не first attempt (INC-20260726-0814).
- **Cursor SDK / local agent (B72):** до первого Kie — scene_hint lock «SDK needs internet»; cover без keyword checklist / «Ключевые темы»; comparison Chat YES / Ollama NO / SDK YES (INC-20260721-2050).

Ожидание: Image to Image, 1 входное фото, aspect 16:9, resolution 2K.

Prompt budget: короткий compact prompt (`validation.prompt_chars <= 3500`). Не дублировать полный brand-lock, suffix и negative на каждую панель; скрипт пишет **один** shared `Inline all:` lock на все три inline (не ×3) + короткое описание 4 квадрантов (INC-20260723-1626 / B79). **До** `--write-batch`: cover `scene_hint` ≈**80–140** (`Host … LARGE left half` + `tiny` topic prop, без MUST/face essay / equal-weight props); inline ≈**100–220**. Bilingual essays → 3670+ chars FAIL (INC-20260721-0837); длинный cover face-essay или equal-weight props → host missing (INC-20260724-0837 / INC-20260724-1239). Скрипт compact caps: cover≤200, inline≤180; при BLOCKER сначала укороти hints. Если hints уже короткие, а budget всё равно FAIL — это рост shared ban/style text: reclaim в `cover_quad_prompt.py`, **не** опустошай `scene_hint`.

### Шаг 4.1 — legacy MCP fallback (только без KIE_API_KEY)

Вызывай MCP **только** если `KIE_API_KEY` отсутствует. Иначе пропусти этот шаг.

Backend sync `gpt-image-2` может ждать Kie.ai до **15 минут**. В Cloud HTTP-клиент MCP может оборвать sync call раньше с:

```text
HTTP MCP tool execution failed: MCP error -32001: Request timed out
```

Это означает, что Cursor MCP client оборвал длинный sync call раньше, чем backend вернул URL. Делай так:

1. Убедись, что ошибка именно `-32001 Request timed out`, а не schema/auth/input.
2. Не ищи URL в `cover/*` или других article files: при timeout `quad-mcp-result.json` ещё не существует, пока агент сам не запишет URL.
3. Проверь expanded MCP tool response / Cursor MCP Logs: если там уже появился generated image URL, это **успех**.
4. Если в логе есть `task_id`, но нет URL — используй status/result MCP tool, если он доступен.
5. Если нет URL, нет `task_id` и нет status/result tool — `COVER MCP ASYNC BLOCKER` (не blind retry sync create).

Запрещено: начинать Cover с MCP при наличии `KIE_API_KEY`; останавливать cover после первого timeout без диагностики; запускать повторную sync-генерацию после client timeout; делать 4 отдельных генерации; идти дальше без URL.

### Шаг 5 — apply

```bash
python scripts/excalibur_blog_quad_apply.py \
  --article-dir memory/blog/articles/<topic_id>-<slug> \
  --inject-html
```

Требует Pillow. Выход: cover, inline PNG, registry, inject в article.html.

### Шаг 6 — fragment

`.cursor/excalibur-blog-fragments/cover.md` — шаблон в `agents/excalibur-blog-cover.md`.

### Шаг 6.5 — после apply (без quality Kie)

Split/inject PASS → fragment. **Не** открывай PNG чтобы запустить второй Kie.
Visual QA skip; style/host/sticky чинятся **только** улучшением first-try
prompt в следующем run (incident), не ретраем в текущем.

### Sticky Cyrillic lock (INC-20260723-0858 / INC-20260723-1237)

1. В `scene_hint` cover: если sticky отрицает Latin brand/token — **сам**
   invent полную кириллическую фразу (не голое «не» рядом с Latin). **Не**
   копируй canned примеры из style/prompt/skill — phrase bank запрещён
   (INC-20260722-1715).
2. Inline `scene_hint`: явный `NO people/faces/emoji/silhouettes` (не только
   «no people»). Все UI labels invents агент; без canned English chat prompts.
3. **Запрещён** Kie redo из‑за Latin-bias sticky (INC-20260724-2120). Если
   после единственного gen sticky кривой — зафиксируй incident; optional
   surgical Pillow overlay **только** sticky blob текстом из scene_hint
   (без нового Kie). Никогда не flood-fill левый half.

### Comparison + product-folder lock (INC-20260723-1243)

1. `comparison_table_ui` scene_hint: **явно** пометь колонку GOOD vs BAD
   (green checks **только** под правильным продуктом; BAD = red X / «не
   сегодня»). Не полагайся на порядок колонок «слева/справа» без labels —
   модель часто инвертирует.
2. Install/checklist/workflow для sibling Cursor plugins: **hard-lock**
   имя папки продукта в scene_hint (`nero-network-office-page`,
   `excalibur-blog`, …). Запрещено подставлять соседний plugin folder
   (office-pages ≠ excalibur-blog).
3. Sticky Cyrillic — first-try в `scene_hint`; без quality Kie redo.

---

## visual_type (inline)

| type | Когда |
|------|-------|
| `comparison_table_ui` | SEO vs GEO, сравнение |
| `workflow_diagram` | структура, шаги, longread |
| `checklist_board` | чеклист, публикация |
| `schema_faq_ui` | FAQ, schema, JSON-LD |
| `tool_screenshot` | схема интерфейса/иллюстрация инструмента, не реальный screenshot |
| `infographic_card` | цифры, факты |

Keywords + автовыбор: `inline-visual-types.json` + `quad_manifest.py`.

---

## Visual verdict

Не создавай scorecard, numeric rating или script-generated evaluation.
Visual QA **skip по умолчанию**. Cover подтверждается split/inject артефактами
+ one successful Kie result; не PNG beauty loop.

---

## QA перед ✅

- [ ] 1 image job, не 4
- [ ] input_urls в image API/MCP
- [ ] cover.png + 3 inline существуют
- [ ] alt в registry для всех 4
- [ ] ровно три inline привязаны к существующим H2 (`h2_anchor`) и injected после них
- [ ] cover: один hook виден на PNG; `meme_caption_ru == ""`
- [ ] inline: без лица героя
- [ ] cover и inline: чистый белый фон `#FFFFFF`, без бежевого/серого/grunge-фона
- [ ] cover: hook + accent по design-code; dense collage по tenant rules;
  без штампа EXCALIBUR BLOG;
  без sterile host+text, без meme/reaction
- [ ] inline: конкретный H2, 3–6 labels, reading order/outcome, чёрные headings +
  accents + stickers/UI card layers по design-code; без людей/мемов если запрещено,
  silhouette icons; **тот же finish что cover**; **нет empty gray boxes /
  unfinished placeholders**
- [ ] cover sticky Cyrillic unambiguous (не Latin He/ne для «не»)
- [ ] comparison_table_ui: GOOD/BAD columns explicit; green only under correct product
- [ ] product folder in install/checklist inline matches topic (no sibling plugin swap)
- [ ] generated UI честно обозначен как схема/иллюстрация
- [ ] `cover-scorecard.json`: keep/change/never_again без live host и без tool-display mask; validate PASS
- [ ] fragment cover.md записан

---

## Blockers → verdict ❌

- нет reference_url_hosted
- image call text-only (без input_urls)
- `KIE API BLOCKER`: нет `KIE_API_KEY`, non-retryable createTask/recordInfo fail, retryable 500 exhausted (`--max-create-retries`), pre-taskId Connection reset exhausted (один retry), image-fetch File Upload fallback exhausted/`--no-file-upload-fallback`, sensitive 422 после одного soften+recreate, polling timeout после final `recordInfo` (всё ещё non-terminal) или нет resultUrls
- async status/result tool подтвердил failed/no result или повторный timeout уже в status/result flow
- `COVER MCP RECOVERY NEEDED`: после timeout агент не имеет доступа к MCP/Cursor log, где виден generated URL; нужен URL из лога, повторять генерацию вслепую нельзя
- `COVER MCP ASYNC BLOCKER`: sync `gpt-image-2` обрывается по client timeout, а MCP server не даёт `task_id` и отдельный status/result tool для получения позднего URL
- 4 отдельные генерации
- QUAD SPLIT fail
- отсутствует одна из трёх inline, её H2/anchor или injection
- cover содержит meme/reaction/joke caption, больше одного hook или keyword spam
- `meme_caption_ru` не пуст
- inline не объясняет H2, содержит людей/мемы, нечитаемые labels или выдает generated UI за screenshot

---

## Deprecated scripts

Не вызывать (удалены): `excalibur_blog_visual_prompts.py`,
`excalibur_blog_visual_apply.py`, `excalibur_blog_visual_manifest.py`,
interlinker / visual-qa gates.

---

## Эталон (B01)

`memory/blog/articles/B01-primer-seo-stati/cover/` — reference implementation после design code v1.
