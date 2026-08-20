# Subagents (выжимка Cursor, 2026-08-20)

Источник: https://cursor.com/docs/subagents

## Что это

Субагент — отдельное контекстное окно. Родитель кладёт всё нужное в
prompt, субагент работает и **возвращает итог родителю**. Это делегирование,
не второй чат, которым человек рулит вручную.

Работают в editor, CLI и Cloud Agents.

## Foreground vs background

| Режим | Поведение | Для Excalibur |
|-------|-----------|----------------|
| Foreground (`is_background: false`) | Родитель ждёт результат | **Все шаги пайплайна** |
| Background (`is_background: true`) | Сразу возвращает управление | Запрещено для канона |

YAML поля кастомного субагента (`.cursor/agents/*.md`):

- `name`, `description` (роут Task)
- `model`: `inherit` или ID (`gemini-3.7-flash`, `gpt-5.6-sol`, …)
- `readonly`, `is_background`
- параметры модели: `gemini-3.7-flash[effort=high]` или slug
  `gemini-3.7-flash-high`

`description` **не** должен говорить «use proactively» специалистам
пайплайна — иначе Auto запустит Writer мимо Директора.

## Built-in

`explore`, `bash`/`shell`, `browser` — шумные операции. Их можно звать
из специалиста для поиска/команд. Они **не** заменяют Writer/Sol.

## Nested (Cursor 2.5+)

Родитель и **прямые** субагенты могут звать детей. Внук уже не может.
Для блога этого достаточно, чтобы Writer сам вызвал Sol и сломал канон.

**Правило Excalibur:** специалисты не вызывают `Task(excalibur-blog-*)`.
Только Директор (и Setup → voice/visual).

## Cloud subagents = другое окно

`/in-cloud` и Task `environment: cloud` поднимают **отдельный VM + ветку**
в Agents Window. Родитель продолжает своё. Это не цепочка статьи.

Запрещено на шагах Scout…Publish.

`/babysit` — облачный агент вокруг PR, не шаг блога.

## Изолированные копии

«Swarm in its own environment» = worktree или cloud VM. Пайплайн пишет
в один article_dir — изоляция запрещена (`best-of-n-runner` в хуке).

## Resume

Субагента можно `resume` по ID. Для канона: тот же тип, тот же шаг
(retry Title), не «продолжи весь пайплайн».

## Оркестратор (рекомендованный паттерн Cursor)

Родитель: план → specialist → specialist, structured handoff.
Именно Директор Excalibur, а не 15 независимых automation.
