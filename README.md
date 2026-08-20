# Excalibur-2-Cloud

Чистый агентный пайплайн блога для **Cursor Cloud**: Scout → Research →
Title → Writer → Sol → Cover/Schema → Indexer → Publish.

В репозитории **нет** чужого слога, лица, CTA и статей. При первом запуске
агент **Setup** спрашивает вас и заполняет настройки.

## Быстрый старт

1. Склонируйте **private** репозиторий в Cursor / подключите Cloud Environment.
2. Прочитайте [`CLOUD-FIRST-RUN.md`](CLOUD-FIRST-RUN.md) — Secrets, MCP,
   **Memories OFF**.
3. Запустите First-run automation / чат с промптом Setup.
4. Ответьте на вопросы (стиль, примеры, обложки, ссылки, сайт, автор).
5. Когда `memory/setup/status.json` → `complete: true`, включайте Daily
   automation из [`CLOUD-AUTOMATION.md`](CLOUD-AUTOMATION.md).

Карта анкеты: [`SETUP.md`](SETUP.md). Канон агентов: [`AGENTS.md`](AGENTS.md).
Цепочка субагентов: [`shared/subagent-chain.md`](shared/subagent-chain.md).
Выжимка Cursor Docs: [`docs/cursor/README.md`](docs/cursor/README.md).

## Что внутри

| Путь | Роль |
|------|------|
| `agents/` + `.cursor/agents/` | Director, Setup, Sol, Cover, Publish… |
| `docs/cursor/` | Выжимка Cursor Docs (subagents, automations, модели) |
| `skills/` | Runbook'и субагентов |
| `shared/` | Контракты, SOUL (после setup), tenant-config |
| `memory/setup/` | Статус онбординга, inbox примеров |
| `scripts/` | Гейты, publish, cover split (инфраструктура) |

## Чего здесь нет

- Личных промптов и корпуса слога другого автора
- Референс-фото чужого ведущего
- Готовых статей и published ledger с чужими URL
- GUI-приложения — только агенты и Markdown

## Лицензия / доступ

Репозиторий **закрытый**. Владелец открывает доступ сам.
