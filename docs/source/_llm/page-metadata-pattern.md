# Page Metadata Pattern

Use this metadata block at the top of concept/how-to pages when possible:

```md
---
title: <Page title>
summary: <One sentence summary for humans/agents>
updated-at: YYYY-MM-DD
canonical: https://guillotina.readthedocs.io/en/latest/<path>.html
---
```

Guidelines:
- Keep `summary` under 140 characters.
- Update `updated-at` when behavior, API semantics, or examples change.
- Keep `canonical` stable unless the page path changes.
