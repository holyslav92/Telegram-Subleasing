# Cloud First Run — Excalibur-2-Cloud

Официальные источники Cursor (перечитайте при сомнении):

- https://cursor.com/docs/cloud-agent
- https://cursor.com/docs/cloud-agent/setup
- https://cursor.com/docs/cloud-agent/automations
- https://cursor.com/docs/cloud-agent/security
- https://cursor.com/docs/subagents
- https://cursor.com/docs/agent/agents-window
- Выжимка в репо: `docs/cursor/README.md`

## 1. Environment

1. Dashboard → Cloud Agents → Environments.
2. Подключите этот репозиторий.
3. ` .cursor/environment.json` уже задаёт `install` (pip + doctor).
4. Дождитесь успешного Build.

## 2. Secrets

В Secrets (не в git) положите минимум:

| Secret | Зачем |
|--------|--------|
| `PUBLIC_SITE_URL` | Live сайт; в артефактах остаётся `{{SITE_BASE}}` |
| `FTP_HOST` / `FTP_USER` / `FTP_PASS` / `FTP_ROOT` | SFTP publish (имена FTP_*, транспорт SFTP) |
| `EXCALIBUR_BLOG_ALLOW_PUBLISH` | `yes` только когда готовы публиковать |
| Image API key (Kie / ваш провайдер) | Cover, когда Visual setup готов |
| MCP tokens | Wordstat / WP blob — по необходимости |
| `YANDEX_METRIKA_*` | Опционально Content-learner |

Рекомендуется Runtime Secrets для паролей (не светятся в transcript).

Шаблон имён: `.env.example`.

## 3. Memories — ВЫКЛЮЧИТЬ

В Automation → Tools: **Memories = OFF**.

По доке Cursor Memories **включены по умолчанию** и пишут `MEMORIES.md`
вне рабочей копии. Для блог-пайплайна это опасно: старый чужой прогон /
ошибочная «память» ломает следующие статьи. Setup и Daily prompt явно
говорят «игнорируй Automation Memory» — но UI-выключатель надёжнее.

## 4. MCP

Подключите нужные MCP в Cloud / automation tools:

- Wordstat (Scout)
- WordPress content blob (если используете MCP publish helpers)
- Image generation (если Cover через MCP)

## 5. Two automations

### A) First-run (один раз)

```text
Прочитай AGENTS.md и SETUP.md.
Если memory/setup/status.json не complete — работай как excalibur-blog-setup
(skill setup-excalibur-blog): блоки 0–7, заполняй файлы, вызывай
Task(excalibur-blog-setup-voice) model gemini-3.7-flash-high и
Task(excalibur-blog-setup-visual) model inherit — в этом же окне, не /in-cloud.
Не запускай Scout/Publish. Игнорируй Automation Memory.
Memories в Tools должны быть OFF.
```

### B) Daily blog (после setup)

См. `CLOUD-AUTOMATION.md`.

## 6. Проверка

```bash
python3 scripts/excalibur_blog_doctor.py
```

Doctor должен видеть `setup complete` только после Setup.
До этого пайплайн публикации блокируется.
