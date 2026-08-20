# Automations (выжимка Cursor, 2026-08-20)

Источник: https://cursor.com/docs/cloud-agent/automations

## Что создаёт automation

Каждый срабатывание = **один Cloud Agent** с:

- промптом automation;
- **моделью, которую выбрал владелец** в настройках automation;
- инструментами (MCP, Slack, Memories, computer use);
- репозиторием / environment.

Модель automation — это `inherit` для Директора, Setup, Research, Cover,
Publish. Её не хардкодим.

Текстовые субагенты **переопределяют** модель на Gemini 3.7 Flash
(YAML + явный `model` в Task), независимо от того, Grok это или Composer.

## Как настраивать Excalibur

1. Одна Daily automation, не по automation на Writer/Sol/Cover.
2. Промпт = Директор (`CLOUD-AUTOMATION.md` + `AGENTS.md`).
3. Memories = **OFF**.
4. Репозиторий: этот repo.
5. Модель automation = то, что хочет владелец для research/картинок/оркестрации.

Не включать в промпт «запусти cloud subagent» / `/in-cloud`.

## Memories

По умолчанию у automation Memories ON и пишут `MEMORIES.md` вне checkout.
Для блога это яд (чужой прогон). Выключатель в Tools обязателен
(`CLOUD-FIRST-RUN.md`).

## PR tool

Repo-backed automation по умолчанию умеет открывать PR. Директор открывает
PR **после** статьи, не каждый субагент свой PR.

## Trigger

Schedule / webhook — как у тенанта. Суть: один run = одна статья-цепочка.
