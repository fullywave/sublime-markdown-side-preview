# Markdown Side Preview Demo

Side-column preview inside **Sublime Text 4** via `HtmlSheet` — not browser-only.

## Features

- Live refresh (debounced)
- Headings, lists, links
- Fenced code blocks
- Basic tables

### Code

```python
def hello(name: str) -> str:
    return f"Hello, {name}!"
```

### List

1. Install into `Packages/MarkdownSidePreview`
2. Open this file
3. Toggle side preview

- Nested
  - Item A
  - Item B

### Table

| Feature | Status |
|---------|--------|
| HtmlSheet | yes |
| Mermaid | later |
| KaTeX | later |

> Tip: use **Ctrl+Alt+M** / **Cmd+Alt+M** to toggle.

[GitHub repo](https://github.com/fullywave/sublime-markdown-side-preview)

![alt text for relative image](./diagram.png)
