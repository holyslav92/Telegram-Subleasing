# Excalibur-2-Cloud — цепочка в одном окне

Канон запуска субагентов после документации Cursor от **2026-08-20**:
[docs/cursor/README.md](../docs/cursor/README.md).
Модели: [pipeline-model-policy.json](pipeline-model-policy.json).

## Одно окно

Daily / First-run **Automation** поднимает **один** Cloud Agent
(Директор или Setup). Это единственный «главный» чат.

Специалисты — **foreground Task** в том же прогоне:

- свой контекст (так устроены subagents Cursor);
- тот же checkout, та же ветка;
- результат возвращается родителю;
- родитель зовёт **следующий** шаг.

Это оркестратор Cursor: planner → specialist → specialist,
а не дерево отдельных Cloud Agent / Agents Window чатов.

## Запрещено (ломает цепочку)

| Действие | Почему нельзя |
|----------|----------------|
| `Task(..., environment="cloud")` | Новый VM + ветка + окно (`/in-cloud`) |
| `/in-cloud`, `/babysit` на шаге пайплайна | Cloud subagent вне цепочки |
| `is_background: true` / `run_in_background: true` | Шаг не блокирует родителя, цепочка рассыпается |
| Isolated worktree / `best-of-n-runner` | Чужой checkout |
| `Task(excalibur-blog-director)` / `Task(excalibur-blog-setup)` | Оркестратор не субагент |
| Специалист вызывает `Task(excalibur-blog-*)` | Вложенный пайплайн (Cursor 2.5 это технически умеет на 1 уровень) |
| Автозапуск skill специалиста в чужой роли | Writer skill на Research → статья без канона |

Единственное вложенное Task: **Setup** → `setup-voice` и `setup-visual`.

Единственная параллель: **Cover-text ∥ Schema** (два foreground Task
в одном сообщении Директора), затем Cover.

## Кто какой моделью

- **Текст** (H1, черновик, финальная статья, карточка Дзена, надписи обложки,
  SOUL/article-style): YAML + Task `model: gemini-3.7-flash-high`
  (Gemini 3.7 Flash, latest Google в каталоге Cursor на дату доков).
- **Research, Scout, картинки, schema, publish, fixer, indexer, visual setup,
  Директор, Setup:** `model: inherit` — модель **этой** automation /
  выбранная пользователем.

Если Task **опускает** `model`, runtime часто берёт модель родителя
и может перебить YAML. Поэтому текстовые шаги Директор передаёт явно:
`model: gemini-3.7-flash-high`. Не-текст: `inherit` или поле не передавать.

## Как Директор вызывает Task

```text
Текстовый шаг:
  subagent_type: excalibur-blog-{title|writer|sol|description|cover-text}
  model: gemini-3.7-flash-high
  run_in_background: false
  (environment не передавать — default local)

Не-текст:
  subagent_type: excalibur-blog-{scout|research|schema|cover|indexer|publish|fixer|content-learner}
  model: inherit   # или опустить
  run_in_background: false
```

Полный prompt субагенту: входные пути, topic_id, article_dir, что уже
готово, что **не** делать. Субагент не видит историю родителя.

## Skills

Специалист-skills: `disable-model-invocation: true`.
Их читает **свой** агент по пути из `agents/*.md`, а не Auto всего чата.

Директор и Setup остаются auto-skills оркестратора.
