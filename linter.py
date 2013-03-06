
import sys
import os

__base__ = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, __base__)

import collections
import functools
import re
import threading

import pyuv
import sublime
import sublime_plugin

from ioloop import IOLoop


ioloop = IOLoop()
io_thread = threading.Thread(target=ioloop.start)
io_thread.start()

view_messages = dict()
view_regions = dict()
linting_views = set()
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
        _get_messages(view).clear()
        _get_regions(view)[:] = list()
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

            messages = _get_messages(view)
            regions = _get_regions(view)
            regions.append(view.full_line(view.text_point(line, 0)))
            msg = '%(code)s %(reason)s' % {'code': match.group('code'),
                                           'reason': match.group('reason')}
            messages[line].append(msg)

    @classmethod
    def command_finished(cls, view, proc, exit_status, term_signal):
        proc.close()
        regions = _get_regions(view)
        draw_type = sublime.DRAW_EMPTY_AS_OVERWRITE | sublime.DRAW_OUTLINED
        scope = 'keyword'
        key = 'lint++'
        view.erase_regions(key)
        view.add_regions(key, regions, scope, 'dot', draw_type)

        cur_line = get_selected_lineno(view)
        update_status_message(view, cur_line)
        linting_views.discard(view.id())


class Flake8(Linter):
    ''' Requires development snapshot:
        https://bitbucket.org/tarek/flake8/src/f35b78bc29c5/?at=flint-merge
    '''
    pattern = re.compile(r'^(?P<file_name>.+):(?P<line_number>\d+):'
                         '(?P<position>\d+):\s+(?P<code>\w{4,4})\s+'
                         '(?P<reason>.*)$')
    command = 'flake8'


def _get_messages(view):
    if view.id() not in view_messages:
        view_messages[view.id()] = collections.defaultdict(list)
    return view_messages[view.id()]


def _get_regions(view):
    if view.id() not in view_regions:
        view_regions[view.id()] = list()
    return view_regions[view.id()]


def get_selected_lineno(view):
    sel = view.sel()
    if not sel:
        return None
    return view.rowcol(sel[0].end())[0]


def update_status_message(view, cur_line):
    messages = _get_messages(view)
    line_messages = messages.get(cur_line)
    if line_messages:
        view.set_status('lint++', ', '.join(line_messages))
    else:
        view.erase_status('lint++')


def lint(view):
    if get_syntax(view) != 'Python':
        return
    if view.id() in linting_views:
        return

    linting_views.add(view.id())
    ioloop.add_callback(Flake8.run, view)


def get_syntax(view):
    syntax = os.path.basename(view.settings().get('syntax'))
    return os.path.splitext(syntax)[0]


def plugin_unloaded():
    ioloop.stop()


class Listener(sublime_plugin.EventListener):

    def __init__(self):
        self.last_line = None

    def on_post_save(self, view):
        lint(view)

    def on_selection_modified(self, view):
        cur_line = get_selected_lineno(view)
        if cur_line and cur_line != self.last_line:
            self.last_line = cur_line
            update_status_message(view, cur_line)
