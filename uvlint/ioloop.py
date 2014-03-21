
import collections
import functools
import logging

import pyuv

log = logging.getLogger(__name__)


class IOLoop(object):
    '''Simple version adopted from tornado-pyuv and rose.'''

    def __init__(self):
        self._loop = pyuv.Loop.default_loop()
        self._running = False
        self._stopped = False
        self._callbacks = collections.deque()
        self._callback_processor = pyuv.Check(self._loop)
        self._callback_processor.start(self._process_callbacks)
        self._waker = pyuv.Async(self._loop, lambda x: None)

    def start(self):
        if self._stopped:
            self._stopped = False
            return

        self._running = True
        while self._running:
            self._loop.run(pyuv.UV_RUN_ONCE)
        self._stopped = False

    def stop(self):
        self._running = False
        self._stopped = True
        self._waker.send()

    def add_callback(self, callback, *args, **kwargs):
        callback = functools.partial(callback, *args, **kwargs)
        self._callbacks.append(callback)
        self._waker.send()

    def _process_callbacks(self, handle):
        ntodo = len(self._callbacks)
        for i in range(ntodo):
            callback = self._callbacks.popleft()
            try:
                callback()
            except Exception:
                log.exception('Error in callback')
