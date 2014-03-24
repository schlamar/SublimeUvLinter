
import collections
import logging
import os
import platform
import sys
import threading

import sublime
import sublime_plugin

__version__ = '0.1.0'

ROOT = os.path.abspath(os.path.dirname(__file__))
PLAT_PACKAGES = os.path.join(ROOT, 'packages', sys.platform)
if sys.platform != 'darwin':
    PLAT_PACKAGES = os.path.join(PLAT_PACKAGES, platform.architecture()[0])
sys.path.insert(0, PLAT_PACKAGES)

from UvLinter.uvlint import ioloop, ui, linter

listener = None

logger = logging.getLogger('UvLinter')
logger.setLevel(logging.DEBUG)

io_loop = ioloop.IOLoop()
io_thread = threading.Thread(target=io_loop.start)
io_thread.start()


def plugin_unloaded():
    io_loop.stop()


def plugin_loaded():
    for w in sublime.windows():
        for g in range(w.num_groups()):
            listener.on_load(w.active_view_in_group(g))

    logger.debug('UvLinter loaded: v%s' % __version__)


class Listener(sublime_plugin.EventListener):

    def __init__(self):
        global listener
        listener = self
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
        file_name = view.file_name()
        if file_name is None or not os.path.isfile(file_name):
            return

        if not self.linter[view.buffer_id()]:
            self._create_linter(view)

        for lint in self.linter[view.buffer_id()]:
            io_loop.add_callback(lint.run, view)
