# Команда для агента: «синхронизировать всё»

Скопируйте и отправьте агенту **одним сообщением** после любых доработок в чате:

---

```
Синхронизируй всё по Telegram-проекту:

1. Убедись, что все изменения закоммичены и запушены.
2. Если есть открытый PR с фиксами — смержи его в main (или создай PR и смержи).
3. Переключись на main и подтяни origin/main.
4. Обнови CLOUD-AUTOMATION.md и docs/TELEGRAM_CONTENT_SYSTEM.md, если код изменился.
5. Запусти python3 scripts/telegram_doctor.py и исправь, если секреты не видны.
6. Прогони тест: python3 scripts/daily_telegram_pipeline.py --no-send
7. Напиши мне чеклист: что в main, что осталось сделать мне вручную (Secrets в Cursor Environment, промпт Automation).

Не публикуй в Telegram без моей команды «опубликуй».
```

---

## Что агент может сделать сам

| Действие | Агент |
|----------|-------|
| Коммит, push, merge PR | ✅ |
| Обновить код и доки в репозитории | ✅ |
| `git pull` на main в Cloud Agent | ✅ |
| Тест пайплайна `--no-send` | ✅ |
| Добавить Secrets в Cursor Dashboard | ❌ только вы |
| Изменить текст Automation в UI Cursor | ❌ только вы |
| `git pull` на вашем локальном ПК | ❌ только вы |

## Что сделать вам один раз (вручную)

### Environment Secrets
https://cursor.com/dashboard/cloud-agents/environments

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID` = `-1003795523762`
- `GRSAI_API_KEY`
- `PEXELS_API_KEY`

### Automation «Суб - тг»
В инструкции automation вставьте:

```text
Прочитай CLOUD-AUTOMATION.md и docs/TELEGRAM_CONTENT_SYSTEM.md.
Перед запуском: python3 scripts/telegram_doctor.py
Публикация: python3 scripts/daily_telegram_pipeline.py
При ошибке — Fixer и повтор.
```

### Локально на компьютере
```bash
git checkout main && git pull origin main
```
