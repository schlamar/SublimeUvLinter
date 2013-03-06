
import os
import collections


view_messages = dict()
view_regions = dict()
linting_views = set()


def get_messages(view):
    if view.id() not in view_messages:
        view_messages[view.id()] = collections.defaultdict(list)
    return view_messages[view.id()]


def get_regions(view):
    if view.id() not in view_regions:
        view_regions[view.id()] = list()
    return view_regions[view.id()]


def get_selected_lineno(view):
    sel = view.sel()
    if not sel:
        return None
    return view.rowcol(sel[0].end())[0]


def update_status_message(view, cur_line):
    messages = get_messages(view)
    line_messages = messages.get(cur_line)
    if line_messages:
        view.set_status('lint++', ', '.join(line_messages))
    else:
        view.erase_status('lint++')


def get_syntax(view):
    syntax = os.path.basename(view.settings().get('syntax'))
    return os.path.splitext(syntax)[0]
