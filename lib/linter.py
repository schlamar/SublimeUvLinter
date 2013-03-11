
import functools
import os
import re

import sublime

from StreamingLinter import pyuv
from StreamingLinter.lib import ui


LINESEP = os.linesep.encode()


class LineReaderPipe(pyuv.Pipe):

    def __init__(self, *args, **kwargs):
        super(LineReaderPipe, self).__init__(*args, **kwargs)
        self.callback = None
        self.buffer = b''

    def on_pipe_read(self, pipe, data, error):
        if error:
            pipe.close()
            return

        for line in data.splitlines(True):
            if not line[-len(LINESEP):] == LINESEP:
                self.buffer += line
                return

            line = line.strip()
            if self.buffer:
                line = self.buffer + line
                self.buffer = b''

            self.callback(line)

    def start_read(self, callback):
        self.callback = callback
        super(LineReaderPipe, self).start_read(self.on_pipe_read)


class Linter(object):
    pattern = None
    command = None

    @classmethod
    def run(cls, view):
        ui.get_messages(view).clear()
        ui.get_regions(view)[:] = list()
        cls.run_command(view.file_name(), view)

    @classmethod
    def run_command(cls, file_name, view):
        loop = pyuv.Loop.default_loop()
        pipe = LineReaderPipe(loop)
        proc = pyuv.Process(loop)

        ios = [pyuv.StdIO(),  # stdin - ignore
               pyuv.StdIO(pipe, flags=pyuv.UV_CREATE_PIPE |
                          pyuv.UV_WRITABLE_PIPE)]  # stdout - create pipe
        exit_cb = functools.partial(cls.command_finished, view)
        proc.spawn(cls.command, exit_cb, (file_name,), stdio=ios,
                   flags=pyuv.UV_PROCESS_WINDOWS_HIDE)
        line_cb = functools.partial(cls.process_line, view)
        pipe.start_read(line_cb)

    @classmethod
    def process_line(cls, view, line):
        line = line.decode('utf-8')
        match = cls.pattern.match(line)
        if match:
            line = int(match.group('line_number')) - 1

            messages = ui.get_messages(view)
            regions = ui.get_regions(view)
            regions.append(view.full_line(view.text_point(line, 0)))
            msg = '%(code)s %(reason)s' % {'code': match.group('code'),
                                           'reason': match.group('reason')}
            messages[line].append(msg)

    @classmethod
    def command_finished(cls, view, proc, exit_status, term_signal):
        proc.close()
        regions = ui.get_regions(view)
        draw_type = sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED
        scope = 'keyword'
        key = 'lint++'
        view.erase_regions(key)
        view.add_regions(key, regions, scope, 'dot', draw_type)

        cur_line = ui.get_selected_lineno(view)
        ui.update_status_message(view, cur_line)
        ui.linting_views.discard(view.id())


class Flake8(Linter):
    ''' Requires 2.0 '''
    pattern = re.compile(r'^(?P<file_name>.+):(?P<line_number>\d+):'
                         '(?P<position>\d+):\s+(?P<code>\w{4,4})\s+'
                         '(?P<reason>.*)$')
    command = 'flake8'


def lint(view, ioloop):
    if ui.get_syntax(view) != 'Python':
        return
    if view.id() in ui.linting_views:
        return

    ui.linting_views.add(view.id())
    ioloop.add_callback(Flake8.run, view)
