# Hooks и Skills vs Subagents (выжимка, 2026-08-20)

Источники:

- https://cursor.com/docs/hooks
- https://cursor.com/docs/skills
- https://cursor.com/docs/reference/plugins

## Зачем хук

Cursor 2.5 разрешает прямым субагентам звать детей. Промпта мало.
Хук `preToolUse` (matcher `Task`) + `subagentStart`:

- режет `environment: cloud`;
- режет `Task(director|setup)`;
- режет `best-of-n-runner`;
- режет `run_in_background` на ролях пайплайна;
- режет nested `excalibur-blog-*`, если transcript уже специалист.

Реализация: `scripts/excalibur_blog_subagent_hook.py`,
конфиг: `.cursor/hooks.json` (Cloud Agents подхватывают project hooks).

`subagentStart` / `subagentStop` в cloud поддерживаются.
`failClosed` не ставим: падение хука не должно убить весь run
(fail-open). Запреты срабатывают, когда JSON разобран.

## Skills ≠ субагенты

| | Skill | Subagent |
|--|-------|----------|
| Контекст | Тот же чат | Новое окно, возврат итога |
| Зачем | Короткий runbook | Длинный изолированный шаг |
| Auto | Может прилипнуть ко всем | По `description` / явный Task |

Специалист-skills в этом репо: `disable-model-invocation: true`.
Их открывает субагент по пути из `agents/*.md`, а не Auto Директора.

Директор и Setup — обычные skills оркестратора (без disable).

Не дублировать slash command и субагента на одно и то же.
Команда `commands/excalibur-blog-run.md` только будит Директора.

## Plugins

`.cursor-plugin/plugin.json` пакует `agents/`, `skills/`, `rules/`.
Рабочая копия Cursor Cloud также читает `.cursor/agents|skills|rules`.
Деревья должны совпадать (`scripts/excalibur_blog_sync_cursor_trees.py`).
