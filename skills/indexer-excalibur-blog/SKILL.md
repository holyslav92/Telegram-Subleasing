---
name: indexer-excalibur-blog
description: Excalibur BLOG Indexer — llms.txt for AI crawlers; no article.html edits.
disable-model-invocation: true
---

# Indexer — llms only

```bash
python3 scripts/excalibur_blog_llms_generator.py \
  --blog-dir memory/blog/articles \
  --blog-path / \
  --out-dir memory/blog
```

Пиши `{{SITE_BASE}}` / `{{SITE_HOST}}` в git-артефакты. Не передавай живой
`PUBLIC_SITE_URL` в `--site-base` для commit.

Выход: `memory/blog/llms.txt`, `llms-full.txt`. Без promotion-checklist,
без правок `article.html`, без interlink.
