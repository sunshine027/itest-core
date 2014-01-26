import os
import uuid
import fcntl
import errno
import shutil
import logging
import tempfile

from itest.conf import settings
from itest.case import sudo
from itest.utils import calculate_directory_size


class TestSpace(object):

    def __init__(self, workdir):
        self.workdir = workdir
        self.lockname = os.path.join(tempfile.gettempdir(), 'itest.lock')
        self.lockfp = None
        self.logdir = os.path.join(workdir, 'logs')
        self.rundir = os.path.join(workdir, 'running')
        self.fixdir = os.path.join(workdir, 'fixtures')

    def setup(self, suite):
        if not self._acquire_lock():
            msg = "Another instance is working on this workspace(%s). " \
                "Please run ps to check." % self.workdir
            logging.error(msg)
            return False

        self._setup(suite)
        return True

    def new_test_dir(self):
        hash_ = str(uuid.uuid4()).replace('-', '')
        path = os.path.join(self.rundir, hash_)
        os.mkdir(path)
        if settings.env_root:
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

    def _setup(self, suite):
        os.mkdir(self.logdir)
        os.mkdir(self.rundir)

        logging.info('copying test cases ...')
        for test in suite:
            shutil.copy(test.filename, self.logdir)

        if settings.env_root:
            size = calculate_directory_size(settings.fixtures_dir)
            logging.info('copying test fixtures(%s) ...' % size)
            shutil.copytree(settings.fixtures_dir, self.fixdir)

    def _acquire_lock(self):
        fp = open(self.lockname, 'wb')
        try:
            fcntl.lockf(fp.fileno(), fcntl.LOCK_EX|fcntl.LOCK_NB)
        except IOError as err:
            if err.errno not in (errno.EACCES, errno.EAGAIN):
                raise
            return False
        else:
            self.lockfp = fp

        if os.path.exists(self.workdir):
            msg = 'removing old test space %s' % self.workdir
            logging.info(msg)
            if sudo('rm -rf %s' % self.workdir) != 0:
                raise Exception("can't clean old workspace, please fix manually")
        os.mkdir(self.workdir)

        return True

    def _release_lock(self):
        if self.lockfp is not None:
            self.lockfp.close()
            
    def __del__(self):
        self._release_lock()
