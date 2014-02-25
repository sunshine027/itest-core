"""This plugin provides test cases definition in XML format.

It's designed for functional testing of *nix commands.

Write a test case like this:

::

  <?xml version="1.0" encoding="UTF-8"?>
  <testcase>
    <summary>An example test</summary>
    <setup>
  touch a.txt
    </setup>
    <steps>
  cp a.txt b.txt
  test -f a.txt
    </steps>
    <teardown>
  rm *.txt
    </teardown>
 </testcase>

"""
import os
import logging
from os.path import (sep, join, isdir, isfile, exists,
                     dirname, basename, expanduser)

from jinja2 import Environment, FileSystemLoader
from nose.plugins import Plugin

from itest import conf
from itest.utils import in_dir
from itest.utils import makedirs
from itest.main import find_test_project_from_cwd
from itest import xmlparser
from itest.case import TestCase
from itest.loader import load_case
from itest import __version__


log = logging.getLogger("nose.plugins.xcase")


class XCase(Plugin):
    """
    As a Nose plugin
    """

    name = 'xcase'

    def options(self, parser, env):
        """
        Register options for this plugin

        A plugin's options() method receives a parser instance. It's good form
        for a plugin to use that instance only to add additional arguments
        that take only long arguments (-like-this). Most of nose's built-in
        arguments get their default value from an environment variable.
        """
        super(XCase, self).options(parser, env)
        parser.version = __version__
        parser.add_option('--V', '--xcase-version', action='version',
                          dest="xcase-version",
                          help="print xcase version")
        parser.add_option('--f', '--xcase-failfast', action='store_true',
                          help="stop on the first failure")
        parser.add_option('--c', '--xcase-catch', action='store_true',
                          help="catch ctrl-c and display results")
        parser.add_option('--b', '--xcase-buffer', action='store_true',
                          help="buffer stdout and stderr during test runs")
        parser.add_option('--xcase-tests', nargs='*')
        parser.add_option('--xcase-project-path', action="store", metavar="PATH",
                          default=env.get("XCASE_ENV_PATH"),
                          help='set test project path where settings.py '
                          'locate. [%s]' % env.get("XCASE_ENV_PATH"))
        parser.add_option('--xcase-workspace', action="store", metavar="PATH",
                          help='set test workspace path')
        parser.add_option('--xcase-with-xunit', action='store_true',
                          help='provides test resutls in standard XUnit XML '
                          'format')
        parser.add_option('--xcase-xunit-file', action='store',
                          default='xunit.xml',
                          help='Path to xml file to store the xunit report.'
                          'Default is xunit.xml in the working directory')
        parser.add_option('--xcase-test-env', action="store", metavar="PATH",
                          dest='test_env',
                          default=env.get("NOSE_XCASE_ENV"),
                          help="Path to test ENV containing fixtures and cases")
        parser.add_option('--xcase-cases-dir', action='store',
                          dest='cases_dir',
                          metavar='PATH', default='cases',
                          help="Path to case files, relative to `test-env` path")
        parser.add_option('--xcase-fixtures-dir', action='store',
                          dest='fixtures_dir',
                          metavar='PATH', default='fixtures',
                          help="Path to fixture files, relative to `test-env` path")
        parser.add_option('--xcase-sudo-password', action='store',
                          metavar='PASSWORD', default=env.get('NOSE_SUDO_PASSWORD'),
                          help="Password to run sudo")
        parser.add_option('--xcase-timeout-run-case', action='store',
                          metavar='SECONDS', default=30*60,  # half an hour
                          help="Timeout(in seconds) for running a single case")
        parser.add_option('--xcase-timeout-hanging', action='store',
                          metavar='SECONDS', default=5*60,  # five minutes
                          help="Timeout(in seconds) if there isn't any output")
        parser.add_option('--xcase-case-ext', action='store',
                          dest='case_ext',
                          metavar='EXT', default='xml',
                          help="Extension name of case file")

    def configure(self, options, config):
        """
        Coinfigure plugin.

        A plugin's configure() method receives the parsed OptionParser options
        object, as well as the current config object. Plugins should configure
        their behavior based on the user-selected settings, and may raise
        exceptions if the configured behavior is nonsensical.
        """
        super(XCase, self).configure(options, config)
        if not self.enabled:
            return
        self.options = options
        self.config = config

        # Check for Test Env
        if not options.test_env:
            path = find_test_project_from_cwd()
            if path:
                options.test_env = path

        if options.test_env:
            self._configure_test_env()

        conf.settings.verbosity = options.verbosity
        if options.xcase_project_path:
            conf.load_settings(options.xcase_project_path)
        else:
            conf.load_settings(find_test_project_from_cwd())

        if options.xcase_workspace:
            conf.settings.WORKSPACE = options.xcase_workspace
        makedirs(conf.settings.WORKSPACE)

    def prepareTestLoader(self, loader):
        """
        Capture loader
        """
        self.loader = loader

    def loadTestsFromName(self, name, module=None, importPath=None):
        """
        Return tests in this file or module. Return None if you are not able
        to load any tests, or an iterable if you are. May be a generator.
        """
        log.info("load from name %s", name)
        fromfile = self.loadTestsFromFile
        fromdir = self.loader.loadTestsFromDir

        if isfile(name):
            return fromfile(name)
        if isdir(name):
            return fromdir(name)
        if not self.options.test_env:
            return

        path = name.replace('.', sep)
        if isdir(path):
            return fromdir(path)
        path2 = join(self.options.cases_dir, path)
        if isdir(path2):
            return fromdir(path2)

        filename = ''.join([path, '.', self.options.case_ext])
        if exists(filename):
            return fromfile(filename)
        filename2 = join(self.options.cases_dir, filename)
        if exists(filename2):
            return fromfile(filename2)

    def loadTestsFromFile(self, filename):
        """
        Load test case

        Writing a plugin that loads tests from files other than python modules

        Implement wantFile and loadTestsFromFile. In wantFile, return True for
        files that you want to examine for tests. In loadTestsFromFile, for
        those files, return an iterable containing TestCases (or yield them as
        you find them; loadTestsFromFile may also be a generator).
        """
        yield load_case(filename)

    def wantFile(self, filename):
        """
        Want case file

        Implement any or all want* methods. Return False to reject the test
        candidate, True to accept it - which means that the test candidate
        will pass through the rest of the system, so you must be prepared to
        load tests from it if tests can't be loaded by the core loader or
        another plugin - and None if you don't care.
        """
        log.info("%s, %s", self.options.case_ext, filename)
        return filename.endswith('.' + self.options.case_ext)

    def wantDirectory(self, dirname):
        """
        Returns True if want to search into `dirname`

        Do search if `dirname` is inside test-env
        """
        if self.options.test_env:
            return in_dir(dirname, self.options.test_env)
        return False

    def addError(self, test, err):
        log.debug("AddError:----\n%s:%s\n%s:%s\n----",
                  type(test), test,
                  type(err), err)

    def addFailure(self, test, err):
        log.debug("AddFailure:----\n%s:%s\n%s:%s\n----",
                  type(test), test,
                  type(err), err)

    def _configure_test_env(self):
        opt = self.options
        opt.cases_dir = join(opt.test_env,
                             opt.cases_dir.lstrip(sep))
        opt.fixtures_dir = join(opt.test_env,
                                opt.fixtures_dir.lstrip(sep))
