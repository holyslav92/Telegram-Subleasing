# Cursor Docs → Excalibur цепочка

Снимок правил Cursor про агентов, субагентов, автоматизации и модели.
Зачем: пайплайн блога должен идти **цепочкой в одном окне automation**,
а не каждым агентом как отдельный Cloud run.

| Файл | О чём |
|------|--------|
| [SOURCE.md](SOURCE.md) | URL и дата чтения |
| [subagents.md](subagents.md) | Task, foreground/background, nested, cloud subagents |
| [automations.md](automations.md) | Одна automation = один Cloud Agent + модель пользователя |
| [agents-window.md](agents-window.md) | Окна, handoff local↔cloud, `/in-cloud` |
| [models.md](models.md) | Gemini на текст, inherit на остальное |
| [hooks-and-skills.md](hooks-and-skills.md) | Хуки Task, skills vs subagents |

Канон репозитория (обязателен агентам):

- `shared/subagent-chain.md`
- `shared/pipeline-model-policy.json`
- хук `scripts/excalibur_blog_subagent_hook.py` + `.cursor/hooks.json`
