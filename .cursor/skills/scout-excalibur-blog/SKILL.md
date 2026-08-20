---
name: scout-excalibur-blog
description: Pick topic from live channel/news hype, not invented series clones.
disable-model-invocation: true
---

# Scout — тема из живого сигнала, не из головы

Ты **не придумываешь** следующую статью из наших старых заголовков и не
смотришь только на Cursor. Сначала смотришь, что сейчас шумит снаружи —
в том числе **новость дня** про AI/модели/агентов/автоматизацию — и берёшь
один угол под ядро блога.

## Типы тем

1. **How-to** — как всегда (Cursor/Make/MCP/агенты/лиды/автопостинг).
2. **News review** — свежая новость дня (новая модель, релиз, апдейт,
   фича): наш пересказ по-человечески с позицией, что это значит для
   читателя блога. Не репост ссылки, не абстрактный AI-хайп без применения.

## Откуда брать тему (обязательно)

До handoff собери **свежий внешний сигнал** (сегодня/эта неделя):

1. **Новости дня** про AI/LLM/агентов/автоматизацию/инструменты контента
   (свежий SERP, чужие каналы, релизы моделей). Сегодняшняя новость может
   стать темой-обзором, не только очередной how-to про Cursor.
2. Telegram-каналы / ленты по нише — минимум:
   - `(scout signal — см. tenant-config.scout_signal_urls)` или каналы из tenant-config.cta_links / scout_signal_urls (смысл/тема, **не копипаст**
     подачи чужого канала; сигнал ≠ стиль статьи). Если прямой ссылкой
     недоступно — бери свежий SERP по «CTA тенанта автоматизация нейросети
     Make Cursor AI».
   - 1–2 **чужих** канала/медиа про Cursor / Make / AI-агентов / автоматизацию
     (WebFetch публичных лент или свежий SERP «AI news today», «новая модель»,
     «Cloud Agents», «Make.com update» и т.п.)
3. Короткий SERP/новостной срез: что обсуждают **сейчас**, не «очередной X MCP
   потому что были B106–B109».
4. **Wordstat — несколько вызовов, не один.** Для сравнения интереса
   вызывай `CallMcpTool(wordstat_get_top_requests)` **отдельными turn**,
   по одному вызову за turn (не batch), по 2–4 смежным фразам темы
   (родитель + синоним + угол). Смотришь частотности и топ-фразы, чтобы
   понять, какой угол живее. `totalCount`-only = `WORDSTAT PARTIAL` с числом,
   не выдумывай impressions.

Wordstat — **подтверждение и расширение угла**, не SEO-магия: не берёшь
самую жирную фразу в title как есть и не пишешь статью «под запрос».

В handoff обязательны поля сигнала:

```text
external_signal: <1 фраза что за хайп/новость>
signal_urls:
- <url1>
- <url2>
signal_accessed: YYYY-MM-DD
wordstat: <топ-фразы + частотности по теме> | WORDSTAT PARTIAL <n> | skip (нет фраз)
```

Без `signal_urls` + сегодняшней даты — Scout **BLOCK**, title не invent.
Wordstat: один solo `CallMcpTool`; `totalCount`-only = PARTIAL, не blocker.

## Выход

Перезапиши `.cursor/excalibur-blog-handoff.md`:

```text
=== EXCALIBUR BLOG SCOUT ===
topic_id: B111
title: <короткий title 3–8 слов>
external_signal: <что сейчас шумит>
signal_urls:
- https://...
- https://...
signal_accessed: YYYY-MM-DD
incident_report: none
```

## Жёсткие запреты

- Придумать тему «из воздуха» / из списка published-titles как «продолжим серию»
- Клоны «ещё один X MCP / ещё одна соцсеть» без внешнего сигнала этой недели
- **RF / Дзен DENY heroes** (`shared/rf-blocked-entities.json` +
  `shared/dzen-content-rules.md`): Meta, Facebook, Instagram, Threads,
  Muse Code/Spark, LinkedIn, Twitter/X, Discord, VPN/обход — даже свежий
  хайп → **пропустить**. Не «meta-теги» SEO.
- До handoff — прочитать полный Дзен-канон (rules.html сводка в dzen-content-rules)
- `memory/topics/`, fat cards, SEO-хвосты «без копипаста за вечер»
- Циклы по 10+ кандидатам (макс. **2** попытки title после сигнала)
- Automation Memory как канон пайплайна — канон = `AGENTS.md`
- `article.html` и **уже опубликованные статьи сайта** (старый текст —
  плохой образец, не переписывать «как в прошлых»)
- research_start, publish

## Алгоритм

1. WebFetch / SERP → живой хайп (каналы + новости). Запиши URL.
2. `published-titles.md` + ledger — только чтобы **не повторить** уже покрытое.
3. `--suggest-next` → next id.
4. Один короткий title из сигнала (не SEO-primary).
5. focus + check-query + check-slug (макс. 2 попытки).
6. Handoff со `signal_urls` → стоп.

Директор:

```bash
python3 scripts/excalibur_blog_research_start.py --topic-id <ID> --title "<title>"
```
