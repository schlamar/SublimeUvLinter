
import os
import collections

import sublime


view_messages = dict()
linting_views = set()


KEY = 'streaming_linter'


def clear(view):
    view.erase_regions(KEY)


def add_region(view, region):
    regions = view.get_regions(KEY)
    regions.append(region)

    draw_type = sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED
    scope = 'keyword'
    view.add_regions(KEY, regions, scope, 'dot', draw_type)


def get_messages(view):
    if view.id() not in view_messages:
        view_messages[view.id()] = collections.defaultdict(list)
    return view_messages[view.id()]


def get_selected_lineno(view):
    sel = view.sel()
    if not sel:
        return None
    return view.rowcol(sel[0].end())[0]


def update_status_message(view, cur_line):
    messages = get_messages(view)
    line_messages = messages.get(cur_line)
    if line_messages:
        view.set_status(KEY, ', '.join(line_messages))
    else:
        view.erase_status(KEY)


def get_syntax(view):
    syntax = os.path.basename(view.settings().get('syntax'))
    return os.path.splitext(syntax)[0]
