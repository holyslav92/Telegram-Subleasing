# Agents Window и «окна» (выжимка, 2026-08-20)

Источники:

- https://cursor.com/docs/agent/agents-window
- https://cursor.com/docs/cloud-agent
- https://cursor.com/docs/agent/overview

## Одно окно vs много агентов

Agents Window заточен под **параллельные** cloud agents, worktrees,
handoff local↔cloud. Для блога это ловушка: легко получить 6 окон
(Scout, Writer, Cover…), каждое думает, что оно пайплайн.

Excalibur: **одно** окно automation (Директор). Субагенты внутри него
(Task foreground). Человек видит один run на cursor.com/agents.

## Чего не делать в пайплайне

- Не переключать шаг в Cloud через dropdown / `/in-cloud`.
- Не handoff «оставшуюся статью» в новый cloud agent.
- Не звать `/babysit` вместо Fixer.
- Не `best-of-n` / isolated worktree на article_dir.

Handoff local↔cloud — для разработки плагина, не для Title→Writer.

## Queue / follow-up

В одном run можно ставить follow-up в очередь. Это всё ещё то же окно.
Не путать с новым Cloud Agent.

Cloud Agents раньше назывались Background Agents — путать с
`is_background` у субагента нельзя.
