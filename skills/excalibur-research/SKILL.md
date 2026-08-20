---
name: excalibur-research
description: Current-date facts from live sources; no invented series continuation. Director-chain specialist.
disable-model-invocation: true
---

# Research — факты сейчас, не выдумка

Задача: дать Writer достоверные факты и боль читателя по теме, которую Scout
взял из **живого** сигнала. Не придумывать каркас и не дописывать соседнюю статью.

## Выход

- `research-notes.md`
- `research-agent-report.json` PASS

## Обязательная свежесть

- `research_date` = сегодня (`today_iso` из research-context)
- В `source_table` у каждого источника `accessed_at: YYYY-MM-DD` (сегодня)
- Минимум один источник — **канал/community/новость этой недели**
  (не только вечные docs). Если Scout дал `signal_urls` в handoff — проверь
  и расширь, не игнорь.
- Wordstat / SERP / GitHub/docs — по теме, с датой доступа.
  `wordstat_get_top_requests` — **несколько вызовов** (solo turn, один вызов
  за turn) по 2–4 смежным фразам: родитель + синоним + угол. Смотришь
  частотности и топ-фразы, чтобы понять, что интереснее. `totalCount`-only =
  WORDSTAT PARTIAL, не blocker. Не собирай один ключ ради title.

Без свежего community/news сигнала → `research-agent-report.json` **BLOCK**
с причиной `STALE_OR_INVENTED_SIGNAL`.

## Содержание notes

- `reader_problem` / `reader_outcome` — **одна** бытовая боль, не список
  требований к архитектуре продукта. Это **внутренняя** справка для
  Lead/Writer, **не** готовый абзац и не инструкция («понять по фактам
  запуска / оговорки прессы»). Пиши outcome как результат для читателя
  («поймёт, что агент кликает сам, а доступ пока в очереди»), не как
  бриф редактору.
- `practical_facts`, `constraints`, versions, типичные ошибки — факты, не
  готовый абзац для лида.
- `voice_angle`, `surprising_fact` — только если есть в источниках.
- `source_table` + `writer_safe_urls` (CTA: каналы из tenant-config.cta_links / scout_signal_urls, канал в
  **MAX** — автоматизация с нейросетями, Make, Cursor AI — и обучение
  Cursor + Make + AI, без «клуб»)

**Не пиши готовые H2, готовый лид и готовый каркас терминов.** Research
— факты. Writer сам решает форму и не обязан открывать статью
определением продукта.


## Overlap

Только `published-titles-only.md`. Не открывай чужие `article.html`,
не читай **уже опубликованные статьи сайта** — они все плохие как образец.
Не строй тему «как продолжение B10x» и не переписывай старый текст.

## Запрещено

- Выдуманные факты / новости «как будто сегодня»
- `h2_outline`, `pain_solution_map`, `action_outline`, FAQ-скелет, готовый lead
- Копировать соседний research-notes как образец прозы
