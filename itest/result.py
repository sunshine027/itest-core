import os
import sys
import time
import json
import datetime
import traceback
import logging
from threading import Thread, Event


from itest.utils import get_local_ipv4, now, get_dist, get_arch
from itest.report import StatusFile, HTMLReport


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


class HTMLTestResult(TextTestResult):

    status_path = None
    env = None
    space = None

    def runner_start(self, test, space, env):
        super(HTMLTestResult, self).runner_start(test, space, env)
        self.space = space
        self.env = env
        self.status_path = os.path.join(space.logdir, 'STATUS')
        self._log_start(space, env, test)

    def runner_stop(self):
        super(HTMLTestResult, self).runner_stop()
        self._log_stop(self.stop_reason)
        self.make_final_report()

    def runner_exception(self, exc_info):
        super(HTMLTestResult, self).runner_exception(exc_info)
        self._log_stop(str(exc_info[1]))

    def add_success(self, test):
        super(HTMLTestResult, self).add_success(test)
        # MUST do this in add_success/add_failure rather than in test_stop
        # since test_stop is called before add_success/add_failure when
        # case is in an undetermined status
        self._log_case(test)

    def add_failure(self, test):
        super(HTMLTestResult, self).add_failure(test)
        self._log_case(test)

    def _collect_env(self, env):
        items = [
            ('Dist', get_dist()),
            ('Arch', get_arch()),
            ('IP', get_local_ipv4()),
            ]
        target = env.query_target()
        if target:
            items.append(('Target', str(target)))
        return items

    def _log_start(self, space, env, test):
        info = {
            'type': 'start',
            'start_time': now(),
            'workspace': space.workdir,
            'log_path': space.logdir,
            'total_cases': test.count,
            'env': self._collect_env(env),
            'deps': env.query_dependencies(),
            'tags': env.get_tags(),
        }
        self._dump(info)

    def _log_stop(self, why):
        info = {
            'type': 'done',
            'error': str(why) if why else '',
            'end_time': now(),
        }
        self._dump(info)

    def _log_case(self, test):
        info = {
            'type': 'case',
            'start_time': test.start_time,
            'cost_time': test.cost_time,
            'name': os.path.basename(test.filename),
            'file': test.filename,
            'log': test.logname,
            'component': test.component,
            'exit_code': 0 if test.was_successful else 1,
            'issue': test.issue,
            'id': test.id,
            'was_successful': test.was_successful,
            }
        self._dump(info)

    def _dump(self, data):
        msg = '|'.join([now(), json.dumps(data)]) + os.linesep
        with open(self.status_path, 'a') as f:
            f.write(msg)

    def update_report(self, silent=False):
        info = StatusFile(self.status_path).load()
        HTMLReport(info).generate(silent)

    def make_final_report(self):
        self._make_coverage_report()
        self.update_report()

    def _make_coverage_report(self):
        if not self.env.ENABLE_COVERAGE:
            return

        cmds = ['cd %s' % self.space.logdir,
                'coverage=$(which python-coverage 2>/dev/null || which coverage)',
                '$coverage combine',
                '$coverage report -m',
                'rm -rf htmlcov',
                '$coverage html',
                ]
        os.system(';'.join(cmds))


def sync(local_path, remote_path):
    cmd = "rsync -a '%s/'* '%s'" % (local_path, remote_path)
    logging.debug(cmd)
    ret = os.system(cmd)
    if ret == 0:
        return 0

    logging.warning('sync to %s failed, wait a few seconds and retry' % remote_path)
    time.sleep(5)
    ret = os.system(cmd)
    if ret == 0:
        return 0

    logging.warning('sync to %s failed, please check the network' % remote_path)
    return ret


def mkdir_in_remote(url):
    parts = url.split('@', 1)
    if len(parts) > 1:
        username, host_and_path = parts
    else:
        host_and_path = parts[0]
        username = ''
    host, path = host_and_path.split(':', 1)
    userhost = '%s@%s' % (username, host) if username else host

    cmd = "ssh '%s' mkdir -p '%s'" % (userhost, path)
    logging.debug(cmd)
    if os.system(cmd) != 0:
        raise Exception("can't mkdir %s in remote server %s" % (path, userhost))


class AutoUploadHTMLTestResult(HTMLTestResult):

    min_interval = 5
    interval = 5 * 60
    url = None

    to_die = None
    thread = None

    def runner_start(self, test, space, env):
        super(AutoUploadHTMLTestResult, self).runner_start(test, space, env)

        self.space = space

        if self.interval >= self.min_interval:
            mkdir_in_remote(self.url)
            self.thread, self.to_die = self.start_worker(space.logdir, self.url, self.interval)

    def runner_stop(self):
        super(AutoUploadHTMLTestResult, self).runner_stop()

        if self.thread:
            self.stop_worker()
            self.thread = None

        sync(self.space.logdir, self.url)

    def start_worker(self, local_path, remote_path, interval):
        to_die = Event()

        def _thread():
            while 1:
                to_die.wait(interval) #it always return None before py2.7
                if to_die.is_set():
                    break
                self.update_report(silent=True)
                sync(local_path, remote_path)
                msg = 'automatically upload report to %s' % remote_path
                logging.debug(msg)

            logging.debug('sync thread exit')

        proc = Thread(target=_thread)
        proc.start()
        msg = 'a worker had started to sync report to %s in period of %ss' \
            % (remote_path, interval)
        logging.info(msg)
        return proc, to_die

    def stop_worker(self):
        self.to_die.set()
        self.thread.join()
