import os
import uuid
import fcntl
import errno
import shutil
import logging
import tempfile

from jinja2 import Environment, FileSystemLoader

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

    def setup(self, suite):
        if not self._acquire_lock():
            msg = "Another instance is working on this workspace(%s). " \
                "Please run ps to check." % self.workdir
            logging.error(msg)
            return False

        self._setup(suite)
        return True

    def new_test_dir(self, casever, casedir, fixtures):
        hash_ = str(uuid.uuid4()).replace('-', '')
        path = os.path.join(self.rundir, hash_)
        os.mkdir(path)
        self._copy_fixtures(path, casever, casedir, fixtures)
        return path

    def new_log_name(self, test):
        name = os.path.basename(test.filename) + '.log'
        return os.path.join(self.logdir, name)

    def _copy_fixtures(self, todir, casever, casedir, fixtures):
        if casever != 'xml1.0' and settings.fixtures_dir:
            return self._copy_all_fixtures(todir)

        def _make_dir(path):
            try:
                os.mkdir(path)
            except OSError as err:
                if err.errno != errno.EEXIST:
                    raise

        def _copy(source, target):
            _make_dir(os.path.dirname(target))
            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy(source, target)

        def _template(source, target):
            template_dirs = [os.path.abspath(os.path.dirname(source))]
            if settings.fixtures_dir:
                template_dirs.append(settings.fixtures_dir)
            jinja2_env = Environment(loader=FileSystemLoader(template_dirs))
            template = jinja2_env.get_template(os.path.basename(source))
            text = template.render()

            _make_dir(os.path.dirname(target))
            with open(target, 'w') as writer:
                writer.write(text)

        def _write(text, target):
            _make_dir(os.path.dirname(target))
            with open(target, 'w') as writer:
                writer.write(text)

        for item in fixtures:
            if 'src' in item and item['src']:
                source = os.path.join(casedir, item['src'])
                if not os.path.exists(source) and settings.fixtures_dir:
                    source = os.path.join(settings.fixtures_dir, item['src'])
            else:
                source = None
            if 'target' in item and item['target']:
                target = os.path.join(todir, item['target'])
            else:
                target = os.path.join(todir, os.path.basename(source))

            if item['type'] == 'copy':
                _copy(source, target)
            elif item['type'] == 'template':
                _template(source, target)
            elif item['type'] == 'content':
                _write(item['text'], target)
            else:
                raise Exception("Unknown fixture type: %s" % item['type'])

    def _copy_all_fixtures(self, todir):
        for name in os.listdir(settings.fixtures_dir):
            source = os.path.join(settings.fixtures_dir, name)
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
