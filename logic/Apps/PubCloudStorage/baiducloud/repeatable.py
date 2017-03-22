import threading

class RepeatableTimer(object):
    def __init__(self, interval, function, args=[], kwargs={}):
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs

    def start(self):
        self.stop()
        self._timer = threading.Timer(self.interval, self._run)
        self._timer.setDaemon(False)
        self._timer.start()

    def restart(self):
        self.start()

    def stop(self):
        if self.__dict__.has_key("_timer"):
            self._timer.cancel()
            del self._timer

    def _run(self):
        try:
            self.function(*self.args, **self.kwargs)
        except:
            pass
        self.restart()