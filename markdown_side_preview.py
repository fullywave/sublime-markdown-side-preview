"""Markdown Side Preview — Sublime Text 4 package.

Preview Markdown in an editor-side HtmlSheet (2-column layout), with
debounced live refresh. Pure-Python Markdown renderer (no pip deps).
"""

from __future__ import annotations

import os
import threading
from typing import Dict, Optional
from urllib.request import pathname2url

import sublime
import sublime_plugin

try:
    from .lib.md_to_html import markdown_to_html, wrap_document
except ImportError:
    try:
        from MarkdownSidePreview.lib.md_to_html import markdown_to_html, wrap_document
    except ImportError:  # running outside Sublime package context
        from lib.md_to_html import markdown_to_html, wrap_document

# view.id() → HtmlSheet
_PREVIEW_SHEETS: Dict[int, sublime.HtmlSheet] = {}
# view.id() → pending debounce timer
_DEBOUNCE_TIMERS: Dict[int, threading.Timer] = {}
_PACKAGE = "MarkdownSidePreview"
_SETTINGS_FILE = "MarkdownSidePreview.sublime-settings"


def _settings() -> sublime.Settings:
    return sublime.load_settings(_SETTINGS_FILE)


def _package_path() -> str:
    return os.path.join(sublime.packages_path(), _PACKAGE)


def _read_package_file(*parts: str) -> str:
    path = os.path.join(_package_path(), *parts)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except OSError:
        # Fallback: same directory as this plugin (dev / symlink layouts)
        alt = os.path.join(os.path.dirname(__file__), *parts)
        try:
            with open(alt, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return ""


def _is_markdown_view(view: sublime.View) -> bool:
    if view is None or not view.is_valid():
        return False
    name = view.file_name() or ""
    if name.lower().endswith((".md", ".markdown", ".mdown", ".mkd")):
        return True
    syn = view.settings().get("syntax") or ""
    return "markdown" in syn.lower()


def _file_url_dir(path: str) -> str:
    """Return a file:// directory URL ending with / for relative assets."""
    directory = os.path.dirname(os.path.abspath(path))
    # pathname2url handles spaces; ensure trailing slash
    url = "file://" + pathname2url(directory)
    if not url.endswith("/"):
        url += "/"
    return url


def _build_html(view: sublime.View) -> str:
    source = view.substr(sublime.Region(0, view.size()))
    title = os.path.basename(view.file_name() or "Untitled.md")
    theme = _settings().get("theme", "light") or "light"
    resolve_imgs = bool(_settings().get("resolve_relative_images", True))

    base_href: Optional[str] = None
    if resolve_imgs and view.file_name():
        base_href = _file_url_dir(view.file_name())

    body = markdown_to_html(source, base_href=base_href)
    css = _read_package_file("static", "preview.css")
    js = _read_package_file("static", "preview.js")
    meta = '<p class="msp-meta">Markdown Side Preview · %s</p>' % _escape_basic(title)
    return wrap_document(meta + body, title=title, css=css, js=js, theme=theme)


def _escape_basic(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _set_two_column_layout(window: sublime.Window) -> None:
    window.set_layout(
        {
            "cols": [0.0, 0.5, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
        }
    )


def _set_single_column_layout(window: sublime.Window) -> None:
    window.set_layout(
        {"cols": [0.0, 1.0], "rows": [0.0, 1.0], "cells": [[0, 0, 1, 1]]}
    )


def _move_sheet_to_group(window: sublime.Window, sheet: sublime.Sheet, group: int) -> None:
    try:
        window.set_sheet_index(sheet, group, 0)
    except Exception:
        # Older API fallbacks are limited; ignore if move fails
        pass


def _any_preview_open_in_window(window: sublime.Window) -> bool:
    for sheet in list(_PREVIEW_SHEETS.values()):
        try:
            if sheet.window() and sheet.window().id() == window.id():
                return True
        except Exception:
            continue
    return False


def open_or_update_preview(view: sublime.View) -> None:
    window = view.window()
    if window is None:
        return

    html = _build_html(view)
    vid = view.id()
    existing = _PREVIEW_SHEETS.get(vid)

    if existing is not None:
        try:
            # HtmlSheet.set_contents available in ST4
            existing.set_contents(html)
            return
        except Exception:
            try:
                existing.close()
            except Exception:
                pass
            _PREVIEW_SHEETS.pop(vid, None)

    # Create side column if needed
    if window.num_groups() < 2:
        _set_two_column_layout(window)
        # Keep active markdown view in group 0
        try:
            window.focus_view(view)
            window.set_view_index(view, 0, 0)
        except Exception:
            pass

    title = "Preview: %s" % os.path.basename(view.file_name() or "Untitled.md")
    sheet = window.new_html_sheet(title, html, flags=0, group=-1)
    _PREVIEW_SHEETS[vid] = sheet

    # Place preview in group 1 when possible
    if window.num_groups() >= 2:
        _move_sheet_to_group(window, sheet, 1)
        try:
            window.focus_view(view)
        except Exception:
            pass


def close_preview(view: sublime.View, restore_layout: bool = True) -> None:
    vid = view.id()
    sheet = _PREVIEW_SHEETS.pop(vid, None)
    window = view.window()
    if sheet is not None:
        try:
            sheet.close()
        except Exception:
            pass

    timer = _DEBOUNCE_TIMERS.pop(vid, None)
    if timer is not None:
        try:
            timer.cancel()
        except Exception:
            pass

    if (
        restore_layout
        and window is not None
        and bool(_settings().get("restore_single_column", True))
        and not _any_preview_open_in_window(window)
        and window.num_groups() > 1
    ):
        # Only restore if the right group is empty-ish
        try:
            if len(window.sheets_in_group(1)) == 0:
                _set_single_column_layout(window)
        except Exception:
            _set_single_column_layout(window)


def schedule_refresh(view: sublime.View) -> None:
    vid = view.id()
    if vid not in _PREVIEW_SHEETS:
        return
    delay_ms = int(_settings().get("debounce_ms", 300) or 300)
    delay_s = max(0.05, delay_ms / 1000.0)

    old = _DEBOUNCE_TIMERS.pop(vid, None)
    if old is not None:
        try:
            old.cancel()
        except Exception:
            pass

    def _fire() -> None:
        def _on_ui() -> None:
            if not view.is_valid():
                return
            if view.id() not in _PREVIEW_SHEETS:
                return
            open_or_update_preview(view)

        sublime.set_timeout(_on_ui, 0)

    timer = threading.Timer(delay_s, _fire)
    timer.daemon = True
    _DEBOUNCE_TIMERS[vid] = timer
    timer.start()


class MarkdownSidePreviewToggleCommand(sublime_plugin.TextCommand):
    def is_enabled(self) -> bool:
        return _is_markdown_view(self.view)

    def run(self, edit: sublime.Edit) -> None:
        vid = self.view.id()
        if vid in _PREVIEW_SHEETS:
            close_preview(self.view)
        else:
            open_or_update_preview(self.view)


class MarkdownSidePreviewRefreshCommand(sublime_plugin.TextCommand):
    def is_enabled(self) -> bool:
        return _is_markdown_view(self.view) and self.view.id() in _PREVIEW_SHEETS

    def run(self, edit: sublime.Edit) -> None:
        if self.view.id() in _PREVIEW_SHEETS:
            open_or_update_preview(self.view)


class MarkdownSidePreviewListener(sublime_plugin.EventListener):
    def on_modified_async(self, view: sublime.View) -> None:
        if not _is_markdown_view(view):
            return
        if view.id() in _PREVIEW_SHEETS:
            schedule_refresh(view)

    def on_post_save_async(self, view: sublime.View) -> None:
        if not _is_markdown_view(view):
            return
        if view.id() in _PREVIEW_SHEETS:
            # Immediate refresh on save
            sublime.set_timeout(lambda: open_or_update_preview(view), 0)

    def on_close(self, view: sublime.View) -> None:
        if view.id() in _PREVIEW_SHEETS:
            close_preview(view, restore_layout=True)
