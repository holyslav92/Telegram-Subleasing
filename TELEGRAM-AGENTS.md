# Telegram Agents — «Добрый дом Тюмень»

Язык: **русский**. Канал бренда — см. `docs/TELEGRAM_CONTENT_SYSTEM.md`.

## Директор

**Агент:** `telegram-content-director`  
**Skill:** `.cursor/skills/director-telegram-content/SKILL.md`  
**Скрипт:** `scripts/telegram_content_director.py`

Отвечает за:
- синхронизацию памяти (`ledger.json`);
- gate + anti-repeat (similarity);
- подготовку bundle (1 фото + 3 **разных** текста);
- отчёт после публикации.

## Learner

**Скрипт:** `scripts/telegram_content_learner.py`

После каждой публикации:
- запоминает opening hook и topic_id;
- фиксирует урок в `memory/telegram_posts/lessons.json`;
- анализирует риски повторов;
- формирует отчёт для директора.

## Быстрый старт

```bash
# 1. Синхронизировать все известные посты
python3 scripts/telegram_ledger_sync.py

# 2. Отчёт (что уже было, риски повторов)
python3 scripts/telegram_content_director.py --report-only

# 3. Подготовить пост на сегодня (или --category host_story)
python3 scripts/telegram_content_director.py --prepare

# 4. Опубликовать выбранный вариант
python3 scripts/publish_telegram_bundle.py --bundle memory/telegram_posts/post_bundle_....json --variant 2
```

## Расписание

| День | Рубрика | category_id |
|------|---------|-------------|
| Пн | Афиша | afisha |
| Вт | Гид по районам | district_guide |
| Ср | Заметки радушного «хозяина» | host_story |
| Чт | Сервис и стандарты | service_standards |
| Пт | Выходные и термы | weekend_thermal |
| Сб | Спецпредложения | special_offers |
| Вс | Сибирское гостеприимство | siberian_hospitality |

## Память

- `memory/telegram_posts/ledger.json` — **единственный источник** опубликованного.
- Cooldown: topic_id 60 дней, entities 45 дней.
- Similarity: opening hook + n-grams против всего ledger.

## Craft-композитор (anti-robot)

Файлы:
- `shared/telegram-content-craft.json` — сцены, CTA, proof, save-worthy, аудитория
- `shared/telegram-topic-craft.json` — метаданные по topic_id
- `scripts/telegram_post_composer.py` — сборка текста

Принципы:
1. **Сцена** — разные стили захода, не «Планируете поездку…»
2. **Срочность** — когда уместно (событие, сезон, выходные)
3. **Micro-proof** — короткая цитата из отзыва, не «читайте Авито»
4. **Аудитория** — business/family/couple, не в каждом посте
5. **Контраст** — только если `contrast_ok` и в тему
6. **Save-worthy** — чек-лист ~1 раз в неделю или по флагу темы
7. **CTA** — ротация 9 типов, learner запоминает `used_cta_ids`

Три варианта: **История** | **Чек-лист** | **Диалог**

## Документация

- `docs/TELEGRAM_CONTENT_SYSTEM.md` — пайплайн, бренд, API.
- `CLOUD-AUTOMATION.md` — prompt для Cloud Automation.
- `shared/telegram-content-rules.json` — запреты (в т.ч. `care_tea`).

## Связь с Excalibur Blog

Этот репозиторий также содержит Excalibur Blog (`AGENTS.md`).  
Telegram-пайплайн **не смешивать** с blog Scout→Publish.  
Для Telegram всегда используй **telegram-content-director**.
