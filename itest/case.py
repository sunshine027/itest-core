import os
import sys
import time
import uuid
import shutil
import logging

import unittest2 as unittest
from unittest2 import SkipTest
from jinja2 import Environment, FileSystemLoader
import pexpect
if hasattr(pexpect, 'spawnb'):  # pexpect-u-2.5
    spawn = pexpect.spawnb
else:
    spawn = pexpect.spawn

from itest.conf import settings
from itest.utils import now, cd, get_machine_labels, makedirs


def id_split(idstring):
    parts = idstring.split('.')
    if len(parts) > 1:
        return '.'.join(parts[:-1]), parts[-1]
    return '', idstring


class TimeoutError(Exception):
    pass


def pcall(cmd, args=(), expecting=(), output=None,
          eof_timeout=None, output_timeout=None, **spawn_opts):
    '''call cmd with expecting
    expecting: list of pairs, first is expecting string, second is send string
    output: redirect cmd stdout and stderr to file object
    eof_timeout: timeout for whole cmd in seconds. None means block forever
    output_timeout: timeout if no output in seconds. Disabled by default
    spawn_opts: keyword arguments passed to spawn call
    '''
    question = [pexpect.EOF, pexpect.TIMEOUT]
    question.extend([pair[0] for pair in expecting])
    if output_timeout:
        question.append(r'\r|\n')
    answer = [None]*2 + [i[1] for i in expecting]

    start = time.time()
    child = spawn(cmd, list(args), **spawn_opts)
    if output:
        child.logfile_read = output

    timeout = output_timeout if output_timeout else eof_timeout
    try:
        while True:
            if output_timeout:
                cost = time.time() - start
                if cost >= eof_timeout:
                    msg = 'Run out of time in %s seconds!:%s %s' % \
                        (cost, cmd, ' '.join(args))
                    raise TimeoutError(msg)

            i = child.expect(question, timeout=timeout)
            if i == 0:  # EOF
                break
            elif i == 1:  # TIMEOUT
                if output_timeout:
                    msg = 'Hanging for %s seconds!:%s %s'
                else:
                    msg = 'Run out of time in %s seconds!:%s %s'
                raise TimeoutError(msg % (timeout, cmd, ' '.join(args)))
            elif output_timeout and i == len(question)-1:
                # new line, stands for any output
                # do nothing, just flush timeout counter
                pass
            else:
                child.sendline(answer[i])
    finally:
        child.close()

    return child.exitstatus


# enumerate patterns for all distributions
# fedora16-64:
# [sudo] password for itestuser5707:
# suse121-32b
# root's password:
# suse122-32b
# itestuser23794's password:
# u1110-32b
# [sudo] password for itester:
SUDO_PASS_PROMPT_PATTERN = "\[sudo\] password for .*?:|" \
                           "root's password:|" \
                           ".*?'s password:"


def sudo(cmd):
    '''sudo command automatically input password'''
    cmd = 'sudo ' + cmd
    logging.info(cmd)

    expecting = [(SUDO_PASS_PROMPT_PATTERN, settings.SUDO_PASSWD)]
    return pcall(cmd, expecting=expecting, output=sys.stdout, eof_timeout=10)


class Tee(object):

    '''data write to original will write to another as well'''

    def __init__(self, original, another=sys.stdout):
        self.original = original
        self.another = another

    def write(self, data):
        self.another.write(data)
        return self.original.write(data)

    def flush(self):
        self.another.flush()
        return self.original.flush()

    def close(self):
        self.original.close()


class Meta(object):
    """
    Meta information of a test case

    All meta information are put in a .meta/ directory under case running
    path. Scripts `setup`, `steps` and `teardown` are in this meta path.
    """

    meta = '.meta'

    def __init__(self, rundir, test):
        self.rundir = rundir
        self.test = test

        self.logname = None
        self.logfile = None
        self.setup_script = None
        self.steps_script = None
        self.teardown_script = None

    def begin(self):
        """
        Begin to run test. Generate meta scripts and open log file.
        """
        os.mkdir(self.meta)

        self.logname = os.path.join(self.rundir, self.meta, 'log')
        self.logfile = open(self.logname, 'a')
        if settings.verbosity >= 3:
            self.logfile = Tee(self.logfile)

        if self.test.setup:
            self.setup_script = self._make_setup_script()
        self.steps_script = self._make_steps_script()
        if self.test.teardown:
            self.teardown_script = self._make_teardown_script()

    def end(self):
        """
        Test finished, do some cleanup.
        """
        if not self.logfile:
            return

        self.logfile.close()

        #delete color code
        os.system("sed -i 's/\x1b\[[0-9]*m//g' %s" % self.logname)
        os.system("sed -i 's/\x1b\[[0-9]*K//g' %s" % self.logname)

        self.logfile = None

    def setup(self):
        if self.setup_script:
            self.log('setup start')
            self._psh(self.setup_script)
            self.log('setup finish')

    def steps(self):
        self.log('steps start')
        retu = self._psh(self.steps_script, self.test.qa)
        self.log('steps finish')
        return retu

    def teardown(self):
        if self.teardown_script:
            self.log('teardown start')
            self._psh(self.teardown_script)
            self.log('teardown finish')

    def log(self, msg, level="INFO"):
        self.logfile.write('%s %s: %s\n' % (now(), level, msg))

    def _make_setup_script(self):
        code = '''cd %(rundir)s
(set -o posix; set) > %(var_old)s
set -x
%(setup)s
set +x
(set -o posix; set) > %(var_new)s
diff --unchanged-line-format= --old-line-format= --new-line-format='%%L' \\
    %(var_old)s %(var_new)s > %(var_out)s
''' % {
            'rundir': self.rundir,
            'var_old': os.path.join(self.meta, 'var.old'),
            'var_new': os.path.join(self.meta, 'var.new'),
            'var_out': os.path.join(self.meta, 'var.out'),
            'setup': self.test.setup,
            }
        return self._make_code('setup', code)

    def _make_steps_script(self):
        code = '''cd %(rundir)s
if [ -f %(var_out)s ]; then
    . %(var_out)s
fi
set -o pipefail
set -ex
%(steps)s
''' % {
            'rundir': self.rundir,
            'var_out': os.path.join(self.meta, 'var.out'),
            'steps': self.test.steps,
            }
        return self._make_code('steps', code)

    def _make_teardown_script(self):
        code = '''cd %(rundir)s
if [ -f %(var_out)s ]; then
    . %(var_out)s
fi
set -x
%(teardown)s
''' % {
            'rundir': self.rundir,
            'var_out': os.path.join(self.meta, 'var.out'),
            'teardown': self.test.teardown,
            }
        return self._make_code('teardown', code)

    def _make_code(self, name, code):
        """Write `code` into `name`"""
        path = os.path.join(self.meta, name)
        data = code.encode('utf8') if isinstance(code, unicode) else code
        with open(path, 'w') as f:
            f.write(data)
        return path

    def _psh(self, script, more_expecting=()):
        expecting = [(SUDO_PASS_PROMPT_PATTERN, settings.SUDO_PASSWD)] + \
            list(more_expecting)
        try:
            return pcall('/bin/bash',
                         [script],
                         expecting=expecting,
                         output=self.logfile,
                         eof_timeout=float(settings.RUN_CASE_TIMEOUT),
                         output_timeout=float(settings.HANGING_TIMEOUT),
                         )
        except Exception as err:
            self.log('pcall error:%s\n%s' % (script, err), 'ERROR')
            return -1


class TestCase(unittest.TestCase):
    '''Single test case'''

    count = 1
    was_skipped = False
    was_successful = False

    def __init__(self, filename, fields):
        super(TestCase, self).__init__()
        self.filename = filename

        # Fields from case definition
        self.version = fields.get('version')
        self.summary = fields.get('summary')
        self.steps = fields.get('steps')
        self.setup = fields.get('steup')
        self.teardown = fields.get('teardown')
        self.qa = fields.get('qa', ())
        self.issue = fields.get('issue', {})
        self.conditions = fields.get('conditions', {})
        self.fixtures = fields.get('fixtures', ())

        self.component = self._guess_component(self.filename)

    def id(self):
        """
        This id attribute is used in xunit file.

        classname.name
        """
        if settings.env_root:
            retpath = self.filename[len(settings.cases_dir):]\
                .lstrip(os.path.sep)
            base = os.path.splitext(retpath)[0]
        else:
            base = os.path.splitext(os.path.basename(self.filename))[0]
        return base.replace(os.path.sep, '.')

    def __eq__(self, that):
        if type(self) is not type(that):
            return NotImplemented
        return self.id() == that.id()

    def __hash__(self):
        return hash((type(self), self.filename))

    def __str__(self):
        cls, name = id_split(self.id())
        if cls:
            return "%s (%s)" % (name, cls)
        return name

    def __repr__(self):
        return '<%s %s>' % (self.__class__.__name__, self.id())

    def setUp(self):
        self._check_conditions()
        self.rundir = rundir = self._new_rundir()
        self._copy_fixtures()

        self.meta = meta = Meta(rundir, self)
        with cd(rundir):
            meta.begin()
            meta.log('case start to run!')
            if self.setup:
                meta.setup()

    def tearDown(self):
        meta = self.meta
        if meta:
            meta.teardown()
            meta.log('case is finished!')
            meta.end()

    def runTest(self):
        meta = self.meta
        with cd(self.rundir):
            code = meta.steps()

        msg = "Nonzero exitcode. See log: %s" % self.meta.logname
        self.assertEqual(0, code, msg)

    def _check_conditions(self):
        '''Check if conditions match, raise SkipTest if some conditions are
        defined but not match.
        '''
        labels = set((i.lower() for i in get_machine_labels()))

        # blacklist has higher priority, if it match both black and white
        # lists, it will be skipped
        intersection = labels & self.conditions.get('distblacklist', set())
        if intersection:
            raise SkipTest('by distribution blacklist:%s' %
                           ','.join(intersection))

        kw = 'distwhitelist'
        if kw in self.conditions:
            intersection = labels & self.conditions[kw]
            if not intersection:
                raise SkipTest('not in distribution whitelist:%s' %
                               ','.join(self.conditions[kw]))

    def _guess_component(self, filename):
        # assert that filename is absolute path
        if not settings.env_root or \
                not filename.startswith(settings.cases_dir):
            return 'unknown'
        relative = filename[len(settings.cases_dir)+1:].split(os.sep)
        # >1 means [0] is an dir name
        return relative[0] if len(relative) > 1 else 'unknown'

    def _new_rundir(self):
        hash_ = str(uuid.uuid4()).replace('-', '')
        path = os.path.join(settings.WORKSPACE, hash_)
        os.mkdir(path)
        return path

    def _copy_fixtures(self):
        todir = self.rundir
        if self.version != 'xml1.0' and settings.fixtures_dir:
            return self._copy_all_fixtures(todir)

        def _copy(source, target):
            makedirs(os.path.dirname(target))
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

            makedirs(os.path.dirname(target))
            with open(target, 'w') as writer:
                writer.write(text)

        def _write(text, target):
            makedirs(os.path.dirname(target))
            with open(target, 'w') as writer:
                writer.write(text)

        casedir = os.path.dirname(self.filename)
        for item in self.fixtures:
            if 'src' in item and item['src']:
                source = os.path.join(casedir, item['src'])
                if not os.path.exists(source) and settings.fixtures_dir:
                    source = os.path.join(settings.fixtures_dir, item['src'])
            elif item['type'] != 'content':
                raise Exception("Attribute src can't be found")

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
