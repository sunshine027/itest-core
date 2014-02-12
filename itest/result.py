import os
import sys
import time
import datetime
import traceback


class TestResult(object):

    success = []
    failure = []
    skipped = []

    # should stop after current case finish
    should_stop = False
    stop_reason = None

    # time when test-runner start
    start_time = None
    # time cost for whole test-runner
    cost_time = None

    # seq number for current running test case
    current_no = 0

    def __init__(self, verbose=0):
        self.verbose = verbose

    def test_start(self, test):
        '''test case start'''
        test.start_time = time.time()
        self.current_no += 1

    def test_stop(self, test):
        '''test case stop'''
        now = time.time()
        test.cost_time = now - test.start_time
        test.cost_time_from_beginning = now - self.start_time

    def runner_start(self, _test):
        '''test runner start'''
        self.start_time = time.time()

    def runner_stop(self):
        '''test runner stop'''
        self.cost_time = time.time() - self.start_time

    def runner_exception(self, exc_info):
        type_, value, tb = exc_info
        traceback.print_exception(type_, value, tb)
        del tb

    def add_success(self, test):
        test.was_successful = True
        self.success.append(test)

    def add_failure(self, test):
        test.was_successful = False
        self.failure.append(test)

    def add_exception(self, test, exc_info):
        type_, value, tb = exc_info
        traceback.print_exception(type_, value, tb)
        del tb
        test.was_successful = False
        self.failure.append(test)

    def add_skipped(self, test, reason):
        '''Add a test case which had been skipped
        '''
        test.was_skipped = True
        test.skip_reason = reason
        self.skipped.append(test)

    @property
    def was_successful(self):
        return len(self.failure) == 0

    def stop(self, reason):
        print 'try to stop since', reason
        self.should_stop = True
        self.stop_reason = reason


class TextTestResult(TestResult):

    def test_start(self, test):
        '''test case start
        '''
        super(TextTestResult, self).test_start(test)
        if self.verbose:
            print '%d. %s ...' % (self.current_no,
                                  os.path.basename(test.filename)),
            sys.stdout.flush()

    def test_stop(self, test):
        '''When test stop
        '''
        super(TextTestResult, self).test_stop(test)

        if self.verbose:
            cost = datetime.timedelta(seconds=int(test.cost_time))
            from_beginning = datetime.timedelta(seconds=int(test.cost_time_from_beginning))

            if test.was_skipped:
                print 'skipped', test.skip_reason
            elif test.was_successful:
                print '(%s/%s) ok' % (cost, from_beginning)
            else:
                print
                print '-' * 40
                print '[FAILED]', os.path.basename(test.filename), '(%s/%s)' % (cost, from_beginning)
                print 'case    ', test.filename
                print 'rundir  ', test.rundir
                print 'logname ', test.logname
        else:
            if test.was_skipped:
                sys.stdout.write('s')
            elif test.was_successful:
                sys.stdout.write('.')
            else:
                sys.stdout.write('F')
        sys.stdout.flush()

    def print_summary(self):
        if not self.failure:
            return

        print
        print '=' * 40
        print 'Failure detail'
        for test in self.failure:
            print
            print os.path.basename(test.filename)
            print 'case    ', test.filename
            print 'rundir  ', test.rundir
            print 'logname ', test.logname


class XunitTestResult(TextTestResult):

    xunit_file = 'xunit.xml'

    def print_summary(self):
        '''Generate Xunit report and print summary
        '''
        super(XunitTestResult, self).print_summary()
        self._make_report()
        print
        print 'xunit report generate at', self.xunit_file

    def _make_report(self):
        '''Make the xunit format of xml located in testspace.
        XML file name is returned.
        '''
        xml = ['<?xml version="1.0" encoding="utf8"?>\n'
               '<testsuite name="itests" tests="%(total)d" errors="%(errors)d" '
               'failures="%(failures)d" skip="%(skipped)d">'
               % {'total': len(self.success) + len(self.failure) + len(self.skipped),
                  'errors': 0,
                  'failures': len(self.failure),
                  'skipped': len(self.skipped),
                  }]
        for test in self.success:
            xml.append(
                '<testcase classname="%(cls)s" name="%(name)s" '
                'time="%(taken).3f" />' %
                {'cls': test.component,
                 'name': os.path.basename(test.filename),
                 'taken': test.cost_time,
                 })
        for test in self.failure:
            xml.append(
                '<testcase classname="%(cls)s" name="%(name)s" time="%(taken).3f">'
                '<failure message="%(message)s"><![CDATA[%(log)s]]>'
                '</failure></testcase>' %
                {'cls': test.component,
                 'name': os.path.basename(test.filename),
                 'taken': test.cost_time,
                 'message': os.path.basename(test.logname),
                 'log': open(test.logname).read().replace('\r', '\n'),
                 })
        xml.append('</testsuite>')
        xml = '\n'.join(xml)

        with open(self.xunit_file, 'w') as fp:
            fp.write(xml)
