"""Pure-Python Markdown → HTML for Sublime MarkdownSidePreview.

Enough CommonMark/GFM for headings, paragraphs, lists, fenced code,
links, images, bold/italic, blockquotes, hr, and basic pipe tables.
No pip dependencies.
"""

from __future__ import annotations

import html
import re
from typing import List, Optional, Tuple


_RE_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_RE_HR = re.compile(r"^(?:-{3,}|\*{3,}|_{3,})\s*$")
_RE_FENCE = re.compile(r"^(`{3,}|~{3,})(\w*)\s*$")
_RE_UL = re.compile(r"^([ \t]*)([-*+])\s+(.*)$")
_RE_OL = re.compile(r"^([ \t]*)(\d+)\.\s+(.*)$")
_RE_BQ = re.compile(r"^>\s?(.*)$")
_RE_TABLE_SEP = re.compile(r"^\|?(\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")
_RE_INLINE_CODE = re.compile(r"`([^`]+)`")
_RE_BOLD = re.compile(r"(\*\*|__)(.+?)\1")
_RE_ITALIC = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)|(?<!_)_(?!_)(.+?)(?<!_)_(?!_)")
_RE_LINK = re.compile(r"(!?)\[([^\]]+)\]\(([^)]+)\)")
_RE_AUTOLINK = re.compile(r"(?<![\(\"'])(https?://[^\s<>\)]+)")


def escape_text(s: str) -> str:
    return html.escape(s, quote=True)


def render_inline(text: str) -> str:
    """Render inline markdown; returns HTML (already escaped where needed)."""

    # Extract code spans first so they are not further transformed
    placeholders: List[str] = []

    def _code_sub(m: re.Match) -> str:
        placeholders.append("<code>%s</code>" % escape_text(m.group(1)))
        return "\x00%d\x00" % (len(placeholders) - 1)

    text = _RE_INLINE_CODE.sub(_code_sub, text)

    # Links / images before escaping the rest of plain text pieces
    parts: List[str] = []
    last = 0
    for m in _RE_LINK.finditer(text):
        parts.append(escape_text(text[last : m.start()]))
        is_img, label, url = m.group(1), m.group(2), m.group(3)
        safe_url = escape_text(url.strip())
        safe_label = escape_text(label)
        if is_img:
            parts.append(
                '<img src="%s" alt="%s" title="%s" />' % (safe_url, safe_label, safe_label)
            )
        else:
            parts.append('<a href="%s">%s</a>' % (safe_url, safe_label))
        last = m.end()
    parts.append(escape_text(text[last:]))
    text = "".join(parts)

    # Autolink remaining bare URLs
    def _auto(m: re.Match) -> str:
        url = m.group(1)
        # url is already escaped as part of text
        return '<a href="%s">%s</a>' % (url, url)

    text = _RE_AUTOLINK.sub(_auto, text)

    # Bold then italic on already-escaped text (markers are ASCII)
    text = _RE_BOLD.sub(r"<strong>\2</strong>", text)

    def _italic(m: re.Match) -> str:
        inner = m.group(1) or m.group(2) or ""
        return "<em>%s</em>" % inner

    text = _RE_ITALIC.sub(_italic, text)

    # Restore code placeholders
    def _restore(m: re.Match) -> str:
        return placeholders[int(m.group(1))]

    text = re.sub(r"\x00(\d+)\x00", _restore, text)
    return text


def _is_table_row(line: str) -> bool:
    s = line.strip()
    return s.startswith("|") or ("|" in s and not s.startswith("```"))


def _split_row(line: str) -> List[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    return [c.strip() for c in s.split("|")]


def _flush_paragraph(buf: List[str], out: List[str]) -> None:
    if not buf:
        return
    text = " ".join(x.strip() for x in buf)
    out.append("<p>%s</p>" % render_inline(text))
    buf.clear()


def markdown_to_html(source: str, base_href: Optional[str] = None) -> str:
    """Convert Markdown source to an HTML fragment (no <html> wrapper).

    base_href: optional directory URL prefix for relative images (e.g. file:///path/).
    """
    lines = source.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    out: List[str] = []
    para: List[str] = []
    i = 0
    n = len(lines)

    while i < n:
        line = lines[i]

        # Fenced code
        fm = _RE_FENCE.match(line)
        if fm:
            _flush_paragraph(para, out)
            fence, lang = fm.group(1), fm.group(2)
            i += 1
            code_lines: List[str] = []
            while i < n and not lines[i].startswith(fence[0] * len(fence)):
                # allow closing fence of same char with >= length
                close = _RE_FENCE.match(lines[i])
                if close and close.group(1)[0] == fence[0] and len(close.group(1)) >= len(fence):
                    break
                code_lines.append(lines[i])
                i += 1
            if i < n:
                i += 1  # skip closing fence
            lang_attr = ' class="language-%s"' % escape_text(lang) if lang else ""
            out.append(
                "<pre><code%s>%s</code></pre>"
                % (lang_attr, escape_text("\n".join(code_lines)))
            )
            continue

        # Blank line
        if not line.strip():
            _flush_paragraph(para, out)
            i += 1
            continue

        # Heading
        hm = _RE_HEADING.match(line)
        if hm:
            _flush_paragraph(para, out)
            level = len(hm.group(1))
            out.append("<h%d>%s</h%d>" % (level, render_inline(hm.group(2).strip()), level))
            i += 1
            continue

        # HR
        if _RE_HR.match(line.strip()):
            _flush_paragraph(para, out)
            out.append("<hr />")
            i += 1
            continue

        # Blockquote (simple, single-level contiguous)
        bq = _RE_BQ.match(line)
        if bq:
            _flush_paragraph(para, out)
            bq_lines: List[str] = []
            while i < n:
                m = _RE_BQ.match(lines[i])
                if not m:
                    break
                bq_lines.append(m.group(1))
                i += 1
            inner = markdown_to_html("\n".join(bq_lines), base_href=base_href)
            out.append("<blockquote>%s</blockquote>" % inner)
            continue

        # Table: header + separator + rows
        if i + 1 < n and _is_table_row(line) and _RE_TABLE_SEP.match(lines[i + 1].strip()):
            _flush_paragraph(para, out)
            headers = _split_row(line)
            i += 2
            rows: List[List[str]] = []
            while i < n and _is_table_row(lines[i]) and lines[i].strip():
                rows.append(_split_row(lines[i]))
                i += 1
            thead = "".join("<th>%s</th>" % render_inline(h) for h in headers)
            body_parts = []
            for row in rows:
                # pad/truncate to header width
                cells = (row + [""] * len(headers))[: len(headers)]
                body_parts.append(
                    "<tr>%s</tr>" % "".join("<td>%s</td>" % render_inline(c) for c in cells)
                )
            out.append(
                "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>"
                % (thead, "".join(body_parts))
            )
            continue

        # Lists (flat + simple nesting by indent spaces)
        ul = _RE_UL.match(line)
        ol = _RE_OL.match(line)
        if ul or ol:
            _flush_paragraph(para, out)
            ordered = ol is not None
            tag = "ol" if ordered else "ul"
            items: List[Tuple[int, str]] = []
            while i < n:
                m_ul = _RE_UL.match(lines[i])
                m_ol = _RE_OL.match(lines[i])
                m = m_ol if ordered else m_ul
                if not m:
                    # allow continuation? keep simple — break
                    break
                indent = len(m.group(1).replace("\t", "    "))
                items.append((indent, m.group(3)))
                i += 1
            out.append(_render_list(tag, items))
            continue

        # Default: paragraph accumulation
        para.append(line)
        i += 1

    _flush_paragraph(para, out)
    body = "\n".join(out)
    if base_href:
        # Rewrite relative img src (no scheme, not //)
        def _img_base(m: re.Match) -> str:
            src = m.group(1)
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", src) or src.startswith("//"):
                return m.group(0)
            base = base_href if base_href.endswith("/") else base_href + "/"
            return 'src="%s%s"' % (escape_text(base), src)

        body = re.sub(r'src="([^"]+)"', _img_base, body)
    return body


def _render_list(tag: str, items: List[Tuple[int, str]]) -> str:
    """Render a flat-or-nested list from (indent, text) pairs."""
    if not items:
        return "<%s></%s>" % (tag, tag)

    # Normalize indents to levels
    indents = sorted({ind for ind, _ in items})
    level_of = {ind: idx for idx, ind in enumerate(indents)}

    parts: List[str] = ["<%s>" % tag]
    stack_depth = 0
    for ind, text in items:
        level = level_of[ind]
        while stack_depth < level:
            parts.append("<%s>" % tag)
            stack_depth += 1
        while stack_depth > level:
            parts.append("</%s>" % tag)
            stack_depth -= 1
            parts.append("</li>")
        # close previous sibling li if open at same level — track with flag
        # Simpler approach: each item is <li>… and nested lists live inside previous li
        parts.append("<li>%s" % render_inline(text))
        # We'll close li when depth decreases or at end — mark open
    while stack_depth > 0:
        parts.append("</li></%s>" % tag)
        stack_depth -= 1
    parts.append("</li></%s>" % tag)
    # Fix over-closed: rewrite with cleaner algorithm
    return _render_list_clean(tag, items, level_of)


def _render_list_clean(tag: str, items: List[Tuple[int, str]], level_of: dict) -> str:
    """Clean nested list renderer."""
    root: List = []  # list of dicts {text, children}
    stack = [root]  # stack of current list containers
    level_stack = [-1]

    for ind, text in items:
        level = level_of[ind]
        while len(level_stack) - 1 > level:
            stack.pop()
            level_stack.pop()
        while len(level_stack) - 1 < level:
            # nest under last item of current list
            if not stack[-1]:
                # create a dummy parent if needed
                node = {"text": "", "children": []}
                stack[-1].append(node)
            else:
                node = stack[-1][-1]
            stack.append(node["children"])
            level_stack.append(level_stack[-1] + 1)
        stack[-1].append({"text": text, "children": []})

    def walk(nodes: List) -> str:
        if not nodes:
            return ""
        bits = ["<%s>" % tag]
        for node in nodes:
            inner = render_inline(node["text"]) if node["text"] else ""
            kids = walk(node["children"])
            if kids:
                bits.append("<li>%s%s</li>" % (inner, kids))
            else:
                bits.append("<li>%s</li>" % inner)
        bits.append("</%s>" % tag)
        return "".join(bits)

    return walk(root)


def wrap_document(
    body_html: str,
    title: str = "Preview",
    css: str = "",
    js: str = "",
    theme: str = "light",
) -> str:
    """Full HTML document for HtmlSheet."""
    theme_class = "theme-dark" if theme == "dark" else "theme-light"
    return """<!DOCTYPE html>
<html class="%s">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>%s</title>
<style>
%s
</style>
</head>
<body>
<article class="markdown-body">
%s
</article>
<script>
%s
</script>
</body>
</html>
""" % (
        theme_class,
        escape_text(title),
        css,
        body_html,
        js,
    )
