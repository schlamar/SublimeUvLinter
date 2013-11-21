
import collections
import logging
import threading

import sublime
import sublime_plugin

from SpeedLinter.slint import ioloop, ui, linter

# ST sets this attribute with all defined commands and
# instantiated event listeners in sublime_plugin.py
plugins = list()

logging.getLogger('SpeedLinter').setLevel(logging.DEBUG)

io_loop = ioloop.IOLoop()
io_thread = threading.Thread(target=io_loop.start)
io_thread.start()


def plugin_unloaded():
    io_loop.stop()


def plugin_loaded():
    for p in plugins:
        if isinstance(p, Listener):
            listener = p
            break

    for w in sublime.windows():
        for g in range(w.num_groups()):
            listener.on_load(w.active_view_in_group(g))


class Listener(sublime_plugin.EventListener):

    def __init__(self):
        self.linter = collections.defaultdict(list)

    def on_post_save(self, view):
        self.lint(view)

    def on_load(self, view):
        self.lint(view)

    def on_activated(self, view):
        self.lint(view)

    def on_close(self, view):
        self.linter.pop(view.buffer_id(), None)

    def on_selection_modified(self, view):
        for lint in self.linter[view.buffer_id()]:
            lint.print_status_message(view)

    def _create_linter(self, view):
        syntax = ui.get_syntax(view)
        for LinterClass in linter.implementations:
            if syntax in LinterClass.syntax:
                lint = LinterClass()
                self.linter[view.buffer_id()].append(lint)

    def lint(self, view):
        if not self.linter[view.buffer_id()]:
            self._create_linter(view)

        for lint in self.linter[view.buffer_id()]:
            io_loop.add_callback(lint.run, view)
