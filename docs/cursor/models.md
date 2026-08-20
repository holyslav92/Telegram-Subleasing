# Модели для субагентов (выжимка, 2026-08-20)

Источники:

- https://cursor.com/docs/subagents.md#model-configuration
- https://cursor.com/docs/models-and-pricing
- https://cursor.com/docs/models/gemini-3-7-flash

## Pin vs inherit

| YAML / Task `model` | Поведение |
|---------------------|-----------|
| `inherit` | Модель родителя = модель automation / чата |
| конкретный ID | Всегда эта модель (если план/админ не блокирует) |

Если Task **опускает** `model`, в Cloud Agent runtime субагент часто
берёт модель **родителя**, даже если YAML другой. Поэтому Директор
**явно** передаёт `gemini-3.7-flash-high` на текстовые шаги.

## Latest Gemini (каталог 2026-08-20)

В публичном каталоге Cursor не hidden: **Gemini 3.7 Flash**
(`gemini-3.7-flash`). Task slug с effort high:
`gemini-3.7-flash-high`.

Это модель для:

- Title (H1 / title)
- Writer (смысл, заголовки H2, черновик)
- Sol (финальная проза)
- Description (тизер карточки)
- Cover-text (русские надписи)
- Setup Voice (SOUL, article-style, examples)

Gemini 3 Pro Image / image preview — **не** текстовые роли.
Картинки Cover идут через Kie/MCP на inherit-агенте `excalibur-blog-cover`.

## Что остаётся на модели automation

Scout, Research, Schema, Cover (генерация), Indexer, Publish, Fixer,
Content-learner, Setup, Setup Visual, сам Директор.

Владелец ставит Grok / Composer / Opus в automation — research и картинки
идут на неё. Текст статьи всё равно Gemini.

## Fallback

Админ команды / план / legacy Max Mode могут подменить модель.
Если текст внезапно не Gemini — смотри план и
https://cursor.com/docs/subagents.md#why-is-my-subagent-using-a-different-model
