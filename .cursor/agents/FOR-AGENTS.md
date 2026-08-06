# Excalibur-2-Cloud — субагенты

Карта: [shared/pipeline-task-map.md](../shared/pipeline-task-map.md)

## Директор и Setup (не Task)

| Роль | Файл | Skill |
|------|------|-------|
| Setup (первый запуск) | `excalibur-blog-setup.md` | `setup-excalibur-blog` |
| Директор (пайплайн) | `excalibur-blog-director.md` | `director-excalibur-blog` |

## Субагенты (Task)

| # | Task | Роль |
|---|------|------|
| S1 | setup-voice | SOUL + examples + article-style |
| S2 | setup-visual | cover configs + assets |
| 🔍 | scout | Тема |
| ① | research | Facts |
| ①b | title | H1 |
| ② | writer | Смысл → `drafts/writer.html` |
| ②b | **sol** | **Финал `article.html` (слог SOUL)** |
| ②c | **description** | **Дзен/RSS карточка → `description-brief.json`** |
| ④a | cover-text | RU надписи |
| ④b | schema | JSON-LD |
| ④c | cover | Image API + figures |
| ⑤ | indexer | llms |
| ⑥ | publish | WP |
| ⑦ | fixer | Incidents |
| ⑦b | content-learner | Metrika |

После **Sol** → **Description** → shell `pipeline_canon --stamp` +
opening_meta / description_gate / html_linter.

Пока setup не complete — только Setup (+ setup-voice/visual).
