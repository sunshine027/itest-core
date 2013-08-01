import os
import sys
import time
import datetime
import traceback


class TestResult(object):

    success = []
    failure = []

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

    def runner_start(self, _test, _space, _env):
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

    @property
    def was_successful(self):
        return len(self.failure) == 0

    def stop(self, reason):
        print 'try to stop since', reason
        self.should_stop = True
        self.stop_reason = reason


class TextTestResult(TestResult):

    def test_start(self, test):
        '''test case start'''
        super(TextTestResult, self).test_start(test)
        if self.verbose:
            print '%d. %s ...' % (self.current_no,
                                  os.path.basename(test.filename)),
            sys.stdout.flush()

    def add_success(self, test):
        super(TextTestResult, self).add_success(test)
        if self.verbose:
            cost = datetime.timedelta(seconds=int(test.cost_time))
            from_beginning = datetime.timedelta(seconds=int(test.cost_time_from_beginning))
            print '(%s/%s) ok' % (cost, from_beginning)
        else:
            sys.stdout.write('.')
        sys.stdout.flush()

    def add_failure(self, test):
        super(TextTestResult, self).add_failure(test)
        if self.verbose:
            cost = datetime.timedelta(seconds=int(test.cost_time))
            from_beginning = datetime.timedelta(seconds=int(test.cost_time_from_beginning))
            print
            print '-' * 40
            print '[FAILED]', os.path.basename(test.filename), '(%s/%s)' % (cost, from_beginning)
            print 'case    ', test.filename
            print 'rundir  ', test.rundir
            print 'logname ', test.logname
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
