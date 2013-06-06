
import os

import sublime


KEY = 'streaming_linter'


def clear(view, key):
    view.erase_regions(KEY + key)


def add_regions(view, regions, key):
    draw_type = sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED
    scope = 'keyword'
    view.add_regions(KEY + key, regions, scope, 'dot', draw_type)


def get_selected_lineno(view):
    sel = view.sel()
    if not sel:
        return None
    try:
        return view.rowcol(sel[0].end())[0]
    except IndexError:
        return None


def update_status_message(view, line_messages, key):
    if line_messages:
        view.set_status(KEY + key, ', '.join(line_messages))
    else:
        view.erase_status(KEY + key)


def get_syntax(view):
    syntax = os.path.basename(view.settings().get('syntax'))
    return os.path.splitext(syntax)[0]
