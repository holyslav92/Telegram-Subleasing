---
name: fixer-excalibur-blog
description: Fixer: incident memory into durable repo fixes. Director-chain specialist.
disable-model-invocation: true
---

# Excalibur BLOG — Fixer Agent

## Когда запускаться

После `=== EXCALIBUR BLOG (PIPELINE DONE) ===` или после терминального blocker, если `memory/pipeline-fix-queue.md` содержит `status: open`.

Fixer не является частью article production path. Это post-run контур улучшения пайплайна.

## Вход

- `memory/pipeline-fix-queue.md`
- `shared/pipeline-incident-fix-contract.md`
- файлы, перечисленные в `Suggested files to inspect/change`
- текущий git diff/status

## Алгоритм

1. Прочитай весь `memory/pipeline-fix-queue.md`.
2. Выбери open-инциденты текущего run. Если run не указан — бери все open, но группируй по root cause.
3. Для каждого инцидента ответь:
   - это ошибка prompt/agent contract?
   - это ошибка skill/runbook?
   - это недостающий script check или плохой fallback?
   - это env/API blocker, который нельзя исправить кодом?
4. Исправь причину в durable source:
   - `agents/` и `.cursor/agents/` — короткий контракт роли;
   - `skills/` и `.cursor/skills/` — подробный runbook;
   - `shared/` — общий контракт, checklist, pitfalls;
   - `scripts/` — автоматическая проверка/валидатор/fallback;
   - stable `memory/` configs — только если это не runtime artifact.
5. Если правишь одну сторону (`agents/`), синхронизируй Cloud-копию (`.cursor/agents/`). То же для `skills/`.
6. Запусти минимально достаточные проверки:
   - `python3 -m py_compile` для изменённых Python scripts;
   - JSON parse для изменённых JSON;
   - relevant gate/dry-run;
   - `rg` на удалённые ошибочные строки.
7. Обнови каждый incident в `memory/pipeline-fix-queue.md`:

```markdown
status: fixed
fixed_at: YYYY-MM-DD
fix_summary:
- ...
files_changed:
- `...`
checks_run:
- ...
commit: <hash or pending-parent-commit>
```

Если durable fix невозможен:

```markdown
status: needs-human
reason:
- ...
needed_decision_or_secret:
- ...
```

## Что считать хорошим fix

- Следующий agent run получает более точный контракт до ошибки.
- Ошибка ловится ранним gate/script вместо позднего ручного исправления.
- Retry/fallback описан идемпотентно: без дублей image jobs, publish calls, ledger rows.
- Fix не раскрывает secrets и не зависит от абсолютных путей конкретной машины.

## Выход для Директора

```text
=== EXCALIBUR BLOG FIXER ===
status: fixed | needs-human | no-open-incidents
incidents:
- INC-...
files_changed:
- ...
checks:
- ...
blockers: none | ...
```

## Запреты

- **Не возвращать старую схему пайплайна** и убранных субагентов (Glavred, Reader Panel, Critic, Thesis и др.). Канон — `Research → Title → Writer → Cover/Schema → Publish`.
- **Не сбрасывать стиль тенанта (SOUL)** (`shared/SOUL.md` +
  `shared/soul-examples/` + `shared/article-style.md`).
  Секцию «Мат» / `@`-шифр в `shared/writer-master-prompt.md` **не**
  восстанавливать и **не** усиливать автоматически: для Дзена мат
  (включая `@`) запрещён (`shared/dzen-content-rules.md`); Writer prompt
  меняет только человек.
- **Не удалять/ослаблять** `shared/topic-focus-contract.md` /
  `scripts/excalibur_blog_topic_focus.py` и focus-гейты в scout/research_start/today.
  Не возвращать в пул PageSpeed/Метрика/GA4/Вебмастер/Директ/индексацию как P0.
- Не исправлять симптомы только в текущем article artifact, если причина в pipeline contract.
- Не запускать publish/image generation без явной необходимости для проверки fix.
- Не закрывать open incident молча.
- Не писать secrets в memory, handoff, PR или logs.
- **HARD (INC-20260726-0530):** не восстанавливать длинный рой —
  Voice / Thesis / Headline / Writing Critic / Reader Panel / Reader Sim /
  Glavred / Visual QA — в critical path, agents/, skills/, task-map или
  speed-contract. Short path канон. Если structural gate требует companions —
  смягчай gate (soft/skip), **не** возвращай удалённые Task.
