
import os
import sys
import platform


class _Log():
    LOG_FILE = 'relay.log'

    def __init__(self):
        self.verbose = False
        self.__file = None
        parent = os.path.dirname(os.path.realpath(__file__))
        parent = os.path.dirname(parent)
        if 'Linux' == platform.system():
            if platform.machine() == 'x86_64':
                return
            parent = '/mnt/run'
        self.__file = open(os.path.join(parent, _Log.LOG_FILE), "w")

    def _out(self, out_str):
        if self.__file:
            self.__file.write(out_str + '\n')
            self.__file.flush()
        print out_str

    def d(self, msg):
        self._out('[D] %s' % msg)

    def e(self, msg):
        self._out('[E] %s' % msg)

    def v(self, msg):
        if self.verbose:  self._out('[V] %s' % msg)

    def __del__(self):
        if self.__file:
            self.__file.close()

log = _Log()
