import time
from unittest2 import TextTestResult

from itest.case import id_split


class XunitTestResult(TextTestResult):

    xunit_file = 'xunit.xml'

    def __init__(self, *args, **kw):
        super(XunitTestResult, self).__init__(*args, **kw)
        self.caselist = []
        self._timer = time.time()

    def startTest(self, test):
        "Called when the given test is about to be run"
        super(XunitTestResult, self).startTest(test)
        self._timer = time.time()

    def _time_taken(self):
        if hasattr(self, '_timer'):
            taken = time.time() - self._timer
        else:
            # test died before it ran (probably error in setup())
            # or success/failure added before test started probably
            # due to custom TestResult munging
            taken = 0.0
        return taken

    def addError(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info().
        """
        super(XunitTestResult, self).addError(test, err)
        self._add_failure(test, err)

    def addFailure(self, test, err):
        """Called when an error has occurred. 'err' is a tuple of values as
        returned by sys.exc_info()."""
        super(XunitTestResult, self).addFailure(test, err)
        self._add_failure(test, err)

    def _add_failure(self, test, err):
        cls, name = id_split(test.id())
        self.caselist.append(
            '<testcase classname="%(cls)s" name="%(name)s" time="%(taken).3f">'
            '<failure message="%(message)s"><![CDATA[%(log)s]]>'
            '</failure></testcase>' %
            {'cls': cls,
             'name': name,
             'taken': self._time_taken(),
             'message': str(err),
             'log': open(test.meta.logname).read().replace('\r', '\n'),
             })

    def addSuccess(self, test):
        "Called when a test has completed successfully"
        super(XunitTestResult, self).addSuccess(test)
        cls, name = id_split(test.id())
        self.caselist.append(
            '<testcase classname="%(cls)s" name="%(name)s" '
            'time="%(taken).3f" />' %
            {'cls': cls,
             'name': name,
             'taken': self._time_taken(),
             })

    def stopTestRun(self):
        """Called once after all tests are executed.

        See stopTest for a method called after each test.
        """
        super(XunitTestResult, self).stopTestRun()
        xml = ['<?xml version="1.0" encoding="utf8"?>'
               '<testsuite tests="%(total)d" errors="%(errors)d" '
               'failures="%(failures)d" skip="%(skipped)d">'
               % {'total': self.testsRun,
                  'errors': len(self.errors),
                  'failures': len(self.failures),
                  'skipped': len(self.skipped),
                  }]
        xml.extend(self.caselist)
        xml.append('</testsuite>')
        xml = '\n'.join(xml)

        with open(self.xunit_file, 'w') as fp:
            fp.write(xml)
