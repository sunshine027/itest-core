import os
import sys
import argparse

try:
    import unittest2 as unittest
    from unittest2 import TextTestResult
except ImportError:
    import unittest
    from unittest import TextTestResult

from itest import conf
from itest.utils import makedirs
from itest.loader import TestLoader
from itest import __version__


ENVIRONMENT_VARIABLE = "ITEST_ENV_PATH"


def find_test_project_from_cwd():
    '''
    Returns test project root directory or None
    '''
    path = os.getcwd()
    while 1:
        name = os.path.join(path, 'settings.py')
        if os.path.exists(name):
            return path

        if path == '/':
            return
        path = os.path.dirname(path)


class TestProgram(unittest.TestProgram):

    def parseArgs(self, argv):
        if len(argv) > 1 and argv[1].lower() == 'discover':
            self._do_discovery(argv[2:])
            return

        parser = argparse.ArgumentParser()
        parser.add_argument('-V', '--version', action='version',
                            version=__version__)
        parser.add_argument('-q', '--quiet', action='store_true',
                            help="minimal output")
        parser.add_argument('-v', '--verbose', action='count',
                            help="verbose output")
        parser.add_argument('-f', '--failfast', action='store_true',
                            help="stop on the first failure")
        parser.add_argument('-c', '--catch', action='store_true',
                            help="catch ctrl-c and display results")
        parser.add_argument('-b', '--buffer', action='store_true',
                            help="buffer stdout and stderr during test runs")
        parser.add_argument('tests', nargs='*')
        parser.add_argument('--test-project-path',
                            default=os.environ.get(ENVIRONMENT_VARIABLE),
                            help='set test project path where settings.py '
                            'locate. [%s]' % ENVIRONMENT_VARIABLE)
        parser.add_argument('--test-workspace', type=os.path.abspath,
                            help='set test workspace path')
        parser.add_argument('--with-xunit', action='store_true',
                            help='provides test resutls in standard XUnit XML '
                            'format')
        parser.add_argument('--xunit-file',
                            type=os.path.abspath, default='xunit.xml',
                            help='Path to xml file to store the xunit report.'
                            'Default is xunit.xml in the working directory')

        opts = parser.parse_args()

        # super class options
        if opts.quiet:
            self.verbosity = 0
        elif opts.verbose:
            # default verbosity is 1
            self.verbosity = opts.verbose + 1
        self.failfast = opts.failfast
        self.catchbreak = opts.catch
        self.buffer = opts.buffer

        # additional options
        if opts.with_xunit:
            if not os.access(os.path.dirname(opts.xunit_file), os.W_OK):
                print >> sys.stderr, "Permission denied:", opts.xunit_file
                sys.exit(1)
            from itest.result import XunitTestResult
            self.testRunner.resultclass = XunitTestResult
            self.testRunner.resultclass.xunit_file = opts.xunit_file
        else:
            self.testRunner.resultclass = TextTestResult

        if opts.test_project_path:
            conf.load_settings(opts.test_project_path)
        else:
            conf.load_settings(find_test_project_from_cwd())

        conf.settings.verbosity = self.verbosity

        if opts.test_workspace:
            conf.settings.WORKSPACE = opts.test_workspace
        makedirs(conf.settings.WORKSPACE)

        # copy from super class
        if len(opts.tests) == 0 and self.defaultTest is None:
            # createTests will load tests from self.module
            self.testNames = None
        elif len(opts.tests) > 0:
            self.testNames = opts.tests
            if __name__ == '__main__':
                # to support python -m unittest ...
                self.module = None
        else:
            self.testNames = (self.defaultTest,)
        self.createTests()


class TextTestRunner(unittest.TextTestRunner):

    def __init__(self, stream=None, descriptions=True, verbosity=1,
                 failfast=False, buffer=False, resultclass=None):
        if stream is None:
            stream = sys.stderr
        super(TextTestRunner, self).__init__(stream, descriptions, verbosity,
                                             failfast, buffer, resultclass)


def main():
    import logging
    logging.basicConfig()
    TestProgram(testLoader=TestLoader(), testRunner=TextTestRunner)
