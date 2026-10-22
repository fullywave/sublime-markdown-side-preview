#!/usr/bin/env python3
"""Unit checks for lib/md_to_html.py (no Sublime required)."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from lib.md_to_html import markdown_to_html, wrap_document  # noqa: E402


def assert_in(needle: str, hay: str, label: str) -> None:
    if needle not in hay:
        raise AssertionError("%s: expected %r in output:\n%s" % (label, needle, hay))


def main() -> None:
    md = """# Title

Paragraph with **bold** and *italic* and `code`.

## List

- one
- two

```python
print("hi")
```

[link](https://example.com)

| A | B |
|---|---|
| 1 | 2 |

> quote
"""
    html = markdown_to_html(md)
    assert_in("<h1>", html, "h1")
    assert_in("Title", html, "title text")
    assert_in("<strong>bold</strong>", html, "bold")
    assert_in("<em>italic</em>", html, "italic")
    assert_in("<code>code</code>", html, "inline code")
    assert_in("<ul>", html, "ul")
    assert_in("<li>", html, "li")
    assert_in("<pre><code", html, "fence")
    assert_in("print(&quot;hi&quot;)", html, "escaped code")
    assert_in('<a href="https://example.com">link</a>', html, "link")
    assert_in("<table>", html, "table")
    assert_in("<th>", html, "th")
    assert_in("<blockquote>", html, "blockquote")

    # XSS-ish escape
    bad = markdown_to_html("<script>alert(1)</script>")
    assert_in("&lt;script&gt;", bad, "escape script")
    if "<script>" in bad:
        raise AssertionError("raw script tag leaked")

    doc = wrap_document(html, title="t", css="body{}", js="", theme="dark")
    assert_in("theme-dark", doc, "theme class")
    assert_in("<article", doc, "article")

    # relative image base
    img = markdown_to_html("![x](./a.png)", base_href="file:///tmp/doc/")
    assert_in('src="file:///tmp/doc/./a.png"', img, "relative img") or assert_in(
        'src="file:///tmp/doc/./a.png"', img, "relative img"
    )

    print("OK: all md_to_html checks passed")


if __name__ == "__main__":
    main()
