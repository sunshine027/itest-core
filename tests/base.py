import os
import unittest
import functools
from subprocess import call
from cStringIO import StringIO

from mock import patch

from itest.utils import cd as _cd


SELF_PATH = os.path.dirname(__file__)
CASES_PATH = os.path.join(SELF_PATH, 'cases')
PROJ_PATH = os.path.join(SELF_PATH, 'tproj')
PROJ_CASES_PATH = os.path.join(PROJ_PATH, 'cases')


class MockExit(object):

    def __call__(self, exitcode):
        self.exitcode = exitcode


def runtest(*argv):
    with patch('sys.argv', ['runtest'] + list(argv)):
        with patch('sys.exit', MockExit()) as mockexit:
            with patch('sys.stderr', StringIO()) as mockerr:
                from itest.main import main
                main()
    return mockexit.exitcode, mockerr.getvalue()


def cd(path):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kw):
            with _cd(path):
                return func(*args, **kw)
        return wrapper
    return decorator


def format_msg(exitcode, stderr):
    return """Exit code %s. STDERR:
%s
END""" % (exitcode, stderr)


class TestBase(unittest.TestCase):

    @cd(SELF_PATH)
    def setUp(self):
        call(["find", ".", "-regex", ".*/xunit.?.xml$", "-delete"])

    def assertPass(self, *argv):
        exitcode, stderr = runtest(*argv)
        self.assertTrue(exitcode == 0 and
                        stderr.find("Ran 0 tests in") == -1,
                        format_msg(exitcode, stderr))

    def assertFail(self, *argv):
        exitcode, stderr = runtest(*argv)
        self.assertNotEquals(0, exitcode,
                             format_msg(exitcode, stderr))

    def assertWithText(self, argv, text):
        exitcode, stderr = runtest(*argv)
        self.assertTrue(stderr.find(text) >= 0,
                        format_msg(exitcode, stderr))

    def assertWithoutText(self, argv, text):
        exitcode, stderr = runtest(*argv)
        self.assertEquals(-1, stderr.find(text),
                          format_msg(exitcode, stderr))
