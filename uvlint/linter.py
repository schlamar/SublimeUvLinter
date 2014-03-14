
import collections
import functools
import logging
import re

from SublimePyuv import pyuv

from UvLinter.uvlint import ui

log = logging.getLogger(__name__)


LINESEPS = [b'\r\n', b'\n']


class LineReaderPipe(pyuv.Pipe):

    def __init__(self, *args, **kwargs):
        super(LineReaderPipe, self).__init__(*args, **kwargs)
        self.callback = None
        self.buffer = b''

    def _line_generator(self, data):
        for line in data.splitlines(True):
            for sep in LINESEPS:
                if line[-len(sep):] == sep:
                    break
            else:
                # no line separator found
                self.buffer += line
                break

            line = line.strip()
            if self.buffer:
                line = self.buffer + line
                self.buffer = b''

            yield line

    def on_pipe_read(self, pipe, data, error):
        if error:
            pipe.close()
            return

        self.callback(self._line_generator(data))

    def start_read(self, callback):
        self.callback = callback
        super(LineReaderPipe, self).start_read(self.on_pipe_read)


class Linter(object):
    pattern = None
    command = None
    args = list()
    syntax = list()

    def __init__(self):
        self.messages = collections.defaultdict(list)
        self.regions = list()
        self.in_progress = False
        self.last_line = None

    def run(self, view):
        if self.in_progress:
            return

        self.in_progress = True
        self.last_line = None
        self.messages.clear()
        self.regions = list()
        ui.clear(view, self.__class__.__name__)
        self.run_command(view)

    def run_command(self, view):
        file_name = view.file_name()
        loop = pyuv.Loop.default_loop()
        pipe = LineReaderPipe(loop)
        proc = pyuv.Process(loop)

        ios = [pyuv.StdIO(),  # stdin - ignore
               pyuv.StdIO(pipe, flags=pyuv.UV_CREATE_PIPE |
                          pyuv.UV_WRITABLE_PIPE)]  # stdout - create pipe

        exit_cb = functools.partial(self.command_finished, view)
        args = self.args + [file_name]
        log.debug('Running %s %s' % (self.command, ' '.join(args)))
        proc.spawn(self.command, exit_cb, args, stdio=ios,
                   flags=pyuv.UV_PROCESS_WINDOWS_HIDE)

        line_cb = functools.partial(self.process_lines, view)
        pipe.start_read(line_cb)

    def process_lines(self, view, lines):
        for line in lines:
            line = line.decode('utf-8')
            match = self.pattern.match(line)
            if match:
                line = int(match.group('line_number')) - 1
                region = view.full_line(view.text_point(line, 0))
                self.regions.append(region)
                msg = '%(code)s %(reason)s' % {'code': match.group('code'),
                                               'reason': match.group('reason')}
                self.messages[line].append(msg)

        ui.add_regions(view, self.regions, self.__class__.__name__)

    def command_finished(self, view, proc, exit_status, term_signal):
        proc.close()
        self.in_progress = False

        if exit_status:
            log.error('Error on subprocess: %s %s'
                      % (exit_status, term_signal))
        else:
            self.print_status_message(view)

    def print_status_message(self, view):
        cur_line = ui.get_selected_lineno(view)
        if cur_line and cur_line != self.last_line:
            self.last_line = cur_line
            ui.update_status_message(view, self.messages.get(cur_line),
                                     self.__class__.__name__)


class Flake8(Linter):
    ''' Requires 2.0 '''
    pattern = re.compile(r'^(?P<file_name>.+):(?P<line_number>\d+):'
                         '(?P<position>\d+):\s+(?P<code>\w{4,4})\s+'
                         '(?P<reason>.*)$')
    command = 'flake8'
    args = ['--immediate', '--exit-zero']
    syntax = ['Python']


implementations = [Flake8]
