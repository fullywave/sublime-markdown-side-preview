# Markdown Side Preview

**Sublime Text 4** Markdown preview in an **editor-side `HtmlSheet`** (2-column layout) — not browser-only.

在 Sublime 编辑器**侧栏 HtmlSheet** 里预览 Markdown（双栏），保存/编辑自动刷新；不依赖外置浏览器作为主路径。

Repo: [fullywave/sublime-markdown-side-preview](https://github.com/fullywave/sublime-markdown-side-preview)  
License: MIT · Target: Sublime Text 4 (Python 3.8 plugin host)

## Why

Most Markdown preview packages open a **browser** tab. That works, but breaks the “edit left / read right” flow inside the editor.

This package uses ST4’s `window.new_html_sheet()` so the preview stays **inside Sublime**, beside your buffer.

> Note: HtmlSheet is **not** a full Chromium WebView. Complex JS (Mermaid, heavy KaTeX) is out of scope for v0.1.

## Install (macOS)

Package Control channel submission is **not** ready yet. Install by cloning into Packages:

```bash
# Package folder name MUST be MarkdownSidePreview
git clone https://github.com/fullywave/sublime-markdown-side-preview.git \
  ~/Library/Application\ Support/Sublime\ Text/Packages/MarkdownSidePreview
```

Or symlink:

```bash
git clone https://github.com/fullywave/sublime-markdown-side-preview.git ~/src/sublime-markdown-side-preview
ln -s ~/src/sublime-markdown-side-preview \
  ~/Library/Application\ Support/Sublime\ Text/Packages/MarkdownSidePreview
```

Restart Sublime Text (or `Package Control: Satisfy Dependencies` / reload plugins).

**Linux**: `~/.config/sublime-text/Packages/MarkdownSidePreview`  
**Windows**: `%APPDATA%\Sublime Text\Packages\MarkdownSidePreview`

## Usage

1. Open a `.md` file (try `example/demo.md`).
2. Toggle preview:
   - **Command Palette** → `Markdown Side Preview: Toggle`
   - **Tools → Markdown Side Preview → Toggle Side Preview**
   - Shortcut: **Ctrl+Alt+M** (Win/Linux) / **Cmd+Alt+M** (macOS) in Markdown syntax
3. Edit → preview refreshes (~300ms debounce). Save also refreshes immediately.
4. Toggle again to close; optional restore to single column when no previews remain.

Commands:

| Command | Action |
|---------|--------|
| `markdown_side_preview_toggle` | Open / close side preview |
| `markdown_side_preview_refresh` | Force refresh |

## Settings

`Preferences → Package Settings → Markdown Side Preview → Settings`

```json
{
  "debounce_ms": 300,
  "theme": "light",
  "restore_single_column": true,
  "resolve_relative_images": true
}
```

`theme`: `"light"` or `"dark"`.

## What renders (v0.1)

Pure-Python converter (`lib/md_to_html.py`), **no pip deps**:

- Headings, paragraphs, hr
- Bold / italic / inline code
- Links + images (relative → `file://` when enabled)
- Unordered / ordered lists (simple nesting)
- Fenced code blocks
- Blockquotes
- Basic pipe tables

## Limitations

- HtmlSheet ≠ full browser: limited CSS/JS; no Mermaid / math yet
- Relative images depend on ST allowing `file://` in HtmlSheet (varies by build); if broken, alt text / path still shows
- Not a full CommonMark/GFM suite (nested emphasis edge cases, footnotes, task lists — later)
- Keybinding only active in Markdown syntax scopes

## Roadmap

- [ ] Task lists, strikethrough, footnotes
- [ ] Scroll sync experiments
- [ ] Optional dark theme auto-follow UI
- [ ] Package Control channel
- [ ] Mermaid / KaTeX (if HtmlSheet permits, or export path)

## Develop / test without GUI

```bash
python3 scripts/test_md_to_html.py
python3 -m py_compile markdown_side_preview.py lib/md_to_html.py
```

## 中文速览

- **问题**：浏览器预览打断编辑流；需要 Sublime **内嵌侧栏**预览。
- **做法**：ST4 `HtmlSheet` + 双栏布局；保存与输入防抖刷新。
- **安装**：把仓库 clone/软链到 `Packages/MarkdownSidePreview`（文件夹名必须一致）。
- **快捷键**：`Cmd+Alt+M`（macOS）切换。
- **限制**：不是完整 Chromium；Mermaid 等后续再做。

## License

MIT © fullywave
