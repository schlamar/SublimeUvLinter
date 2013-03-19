
import collections
import threading

import sublime_plugin

from StreamingLinter.lib import ioloop, ui, linter


ioloop = ioloop.IOLoop()
io_thread = threading.Thread(target=ioloop.start)
io_thread.start()


def plugin_unloaded():
    ioloop.stop()


class Listener(sublime_plugin.EventListener):

    def __init__(self):
        self.linter = collections.defaultdict(list)

    def on_post_save(self, view):
        self.lint(view)

    def on_load(self, view):
        self.lint(view)

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
            ioloop.add_callback(lint.run, view)
