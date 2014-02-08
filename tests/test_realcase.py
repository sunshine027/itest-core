import os
import unittest
import subprocess


class RealCaseTest(unittest.TestCase):
    pass


def _popen(cmd):
    proc = subprocess.Popen(cmd, shell=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    stdout, stderr = proc.communicate()
    msg = """Exit code %s != 0.
STDOUT:
%s
STDERR:
%s""" % (proc.returncode, stdout, stderr)
    return proc.returncode, msg

def _create_test(name):
    path = os.path.join(os.path.dirname(__file__), 'cases')
    funcname = 'test_%s' % name.replace('.', '_')
    def test(self):
        cmd = "cd %s; runtest -vv %s" % (path, name)
        ret, msg = _popen(cmd)
        self.assertEqual(0, ret, msg)
    setattr(RealCaseTest, funcname, test)

def _create_test_in_tproj(name):
    path = os.path.join(os.path.dirname(__file__), 'tproj', 'cases')
    funcname = 'test_tproj_%s' % name.replace('.', '_')
    def test(self):
        cmd = "cd %s; runtest -vv %s" % (path, name)
        print cmd
        ret, msg = _popen(cmd)
        self.assertEquals(0, ret, msg)
    setattr(RealCaseTest, funcname, test)


def _load_tests():
    _create_test('simple.xml')
    _create_test('cdata.xml')
    _create_test('qa.xml')
    _create_test('content_fixture.xml')

    _create_test_in_tproj('copy_fixture.xml')
    _create_test_in_tproj('template_fixture.xml')

_load_tests()
