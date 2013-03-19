
import os

import sublime


KEY = 'streaming_linter'


def clear(view):
    view.erase_regions(KEY)


def add_regions(view, regions):
    regions.extend(view.get_regions(KEY))
    draw_type = sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED
    scope = 'keyword'
    view.add_regions(KEY, regions, scope, 'dot', draw_type)


def get_selected_lineno(view):
    sel = view.sel()
    if not sel:
        return None
    return view.rowcol(sel[0].end())[0]


def update_status_message(view, line_messages):
    if line_messages:
        view.set_status(KEY, ', '.join(line_messages))
    else:
        view.erase_status(KEY)


def get_syntax(view):
    syntax = os.path.basename(view.settings().get('syntax'))
    return os.path.splitext(syntax)[0]
