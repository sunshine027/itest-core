import weakref
import signal


_results = weakref.WeakKeyDictionary()
def register_result(result):
    _results[result] = 1


class KilledError(Exception):
    pass


class _StopHandler(object):

    called = False

    def __call__(self, signum, frame):
        if self.called:
            raise KilledError("Terminated by signal %d" % signum)

        self.called = True
        for result in _results.keys():
            result.stop('Terminated by signal %d' % signum)


_handler = None
def install_handler():
    global _handler
    if _handler is None:
        _handler = _StopHandler()
        signal.signal(signal.SIGTERM, _handler)
