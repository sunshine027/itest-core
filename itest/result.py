import re
import time
import xml.etree.ElementTree as ET

from unittest2 import TextTestResult

from itest.case import id_split

SHELL_COLOR_PATTERN = re.compile(r'\x1b\[[0-9]*[mK]')


class XunitTestResult(TextTestResult):

    xunit_file = 'xunit.xml'

    def __init__(self, *args, **kw):
        super(XunitTestResult, self).__init__(*args, **kw)
        self.testsuite = ET.Element('testsuite')
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

        def get_log():
            with open(test.meta.logname) as reader:
                content = reader.read()
            content = content.replace('\r', '\n').replace('\x00', '')
            content = SHELL_COLOR_PATTERN.sub('', content)
            return content.decode('utf8', 'ignore')

        if hasattr(test, 'meta'):
            content = get_log()
        else:
            content = "Log file isn't available!"

        testcase = ET.SubElement(self.testsuite, 'testcase',
                                 classname=cls,
                                 name=name,
                                 time="%.3f" % self._time_taken())
        failure = ET.SubElement(testcase, 'failure',
                                message=str(err))
        failure.text = content

    def addSuccess(self, test):
        "Called when a test has completed successfully"
        super(XunitTestResult, self).addSuccess(test)
        cls, name = id_split(test.id())
        ET.SubElement(self.testsuite, 'testcase',
                      classname=cls,
                      name=name,
                      taken="%.3f" % self._time_taken())

    def stopTestRun(self):
        """Called once after all tests are executed.

        See stopTest for a method called after each test.
        """
        super(XunitTestResult, self).stopTestRun()

        ts = self.testsuite
        ts.set("tests", str(self.testsRun))
        ts.set("errors", str(len(self.errors)))
        ts.set("failures", str(len(self.failures)))
        ts.set("skip", str(len(self.skipped)))
        xml = ET.tostring(ts)

        with open(self.xunit_file, 'w') as fp:
            fp.write(xml)
