# Telegram Content Director — skill

## Когда использовать

- Ежедневная подготовка/публикация поста «Добрый дом Тюмень».
- Жалоба на повторы, шаблонные заходы, «одно и то же каждую неделю».
- Нужен отчёт: что опубликовано, что запомнено, риски повторов.

## Перед любым прогоном

```bash
python3 scripts/telegram_doctor.py
python3 scripts/telegram_ledger_sync.py
python3 scripts/telegram_content_learner.py --report
```

## Подготовка (1 фото + 3 текста)

```bash
python3 scripts/telegram_content_director.py --prepare --category <category_id>
```

Gate автоматически:
- cooldown topic_id (60 д) и entities (45 д);
- forbidden phrases (`shared/telegram-content-rules.json`);
- **similarity** против `ledger.json` (opening hook, n-grams);
- три варианта должны **различаться структурой** (`variants_too_similar`).

## Публикация

Менеджер выбирает вариант 1–3:

```bash
python3 scripts/publish_telegram_bundle.py --bundle <path> --variant N
```

После publish автоматически:
- запись в `ledger.json` (text_html, opening_hook, fingerprint);
- урок в `memory/telegram_posts/lessons.json`;
- отчёт в `memory/telegram_posts/reports/`.

## Отчёт директора

```bash
python3 scripts/telegram_content_director.py --report-only
# или
python3 scripts/telegram_content_learner.py --report
```

## Файлы памяти

| Файл | Назначение |
|------|------------|
| `memory/telegram_posts/ledger.json` | Все публикации: id, entities, text, hook |
| `memory/telegram_posts/lessons.json` | Уроки learner: hooks, angles по рубрикам |
| `memory/telegram_posts/reports/` | JSON-отчёты директора |

## Ошибки (NEEDS_ATTENTION)

- similarity FAIL → другая тема из банка (до 3 попыток pipeline).
- variants слишком похожи → перегенерация bundle.
- topic в cooldown → `get_next_topic` выберет другую.

## Не делать

- Не публиковать scout-мусор без валидации.
- Не использовать тему `care_tea` (заблокирована).
- Не обходить gate «вручную» через `sendMessage`.
