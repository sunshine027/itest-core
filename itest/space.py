import os
import uuid
import shutil
import logging

from itest.case import sudo
from itest.utils import calculate_directory_size


class TestSpace(object):

    _locked = False

    def __init__(self, workdir):
        self.workdir = workdir
        self.lockname = os.path.join(workdir, 'LOCK')
        self.logdir = os.path.join(workdir, 'logs')
        self.rundir = os.path.join(workdir, 'running')
        self.fixdir = os.path.join(workdir, 'fixtures')

    def setup(self, suite, env):
        if not self._acquire_lock():
            msg = "another instance is working on this workspace(%s) " \
                "since the lock file(%s) exist. please run ps to " \
                "check." % (self.workdir, self.lockname)
            logging.error(msg)
            return False

        self._setup(suite, env)
        return True

    def new_test_dir(self):
        hash_ = str(uuid.uuid4()).replace('-', '')
        path = os.path.join(self.rundir, hash_)
        os.mkdir(path)
        self._copy_fixtures(path)
        return path

    def new_log_name(self, test):
        name = os.path.basename(test.filename) + '.log'
        return os.path.join(self.logdir, name)

    def _copy_fixtures(self, todir):
        for name in os.listdir(self.fixdir):
            source = os.path.join(self.fixdir, name)
            target = os.path.join(todir, name)

            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy(source, target)

    def _setup(self, suite, env):
        os.mkdir(self.logdir)
        os.mkdir(self.rundir)

        logging.info('copying test cases ...')
        for test in suite:
            shutil.copy(test.filename, self.logdir)

        size = calculate_directory_size(env.fixtures_dir)
        logging.info('copying test fixtures(%s) ...' % size)
        shutil.copytree(env.fixtures_dir, self.fixdir)

    def _acquire_lock(self):
        if os.path.exists(self.lockname):
            return False

        # race condition here, but i simply ignore this
        path = self.workdir
        if os.path.exists(path):
            msg = 'removing old test space %s' % path
            logging.info(msg)
            if sudo('rm -rf %s' % path) != 0:
                raise Exception("can't clean old workspace, please fix manually")

        os.mkdir(path)
        open(self.lockname, 'w').close()
        self._locked = True
        return True

    def _release_lock(self):
        try:
            os.unlink(self.lockname)
        except OSError, err:
            if err.errno == 2: # No such file or directory
                msg = "lock file(%s) should be there, " \
                    "but it doesn't exist" % self.lockname
                logging.warning(msg)
            else:
                raise

    def __del__(self):
        if self._locked:
            self._release_lock()
