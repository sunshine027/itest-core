import sys
import time
import datetime

from itest.result import TextTestResult
from itest.signals import register_result


class TextTestRunner(object):

    result_class = TextTestResult

    def __init__(self, verbose):
        self.verbose = verbose

    def _make_result(self):
        return self.result_class(self.verbose)

    def run(self, test, space, env):
        print 'plan to run %d test%s' % (test.count, 's' if test.count > 1 else '')

        result = self._make_result()
        register_result(result)

        start_time = time.time()
        result.runner_start(test, space, env)
        try:
            test.run(result, space, self.verbose)
        except KeyboardInterrupt:
            result.stop(KeyboardInterrupt.__name__)
        except:
            result.runner_exception(sys.exc_info())
        finally:
            result.runner_stop()

        stop_time = time.time()
        cost = stop_time - start_time
        if cost >= 60:
            cost_display = datetime.timedelta(seconds=int(cost))
        else:
            cost_display = '%.3fs' % cost

        result.print_summary()
        run = len(result.success) + len(result.failure)

        print
        print 'Ran %d test%s in %s' % (run,
            's' if run > 1 else '', cost_display)
        if result.was_successful:
            print 'OK'
        else:
            print '%d FAILED' % len(result.failure)
        return result
