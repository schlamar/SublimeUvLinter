
import threading

import sublime_plugin

from StreamingLinter.lib import ioloop, ui, linter


ioloop = ioloop.IOLoop()
io_thread = threading.Thread(target=ioloop.start)
io_thread.start()


# TODO: New architecture: create linter instance per view

def plugin_unloaded():
    ioloop.stop()


class Listener(sublime_plugin.EventListener):

    def __init__(self):
        self.last_line = None

    def on_post_save(self, view):
        linter.lint(view, ioloop)

    def on_load(self, view):
        linter.lint(view, ioloop)

    def on_selection_modified(self, view):
        cur_line = ui.get_selected_lineno(view)
        if cur_line and cur_line != self.last_line:
            self.last_line = cur_line
            ui.update_status_message(view, cur_line)
