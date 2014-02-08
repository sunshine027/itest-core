import os
import unittest
import subprocess


class RealCaseTest(unittest.TestCase):
    pass

def _create_test(name):
    print __file__
    path = os.path.join(os.path.dirname(__file__), 'cases')
    funcname = 'test_%s' % name.replace('.', '_')
    def test(self, *args, **kw):
        cmd = "cd %s; runtest -vv %s" % (path, name)
        proc = subprocess.Popen(cmd, shell=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate()
        msg = """Exit code %s != 0.
STDOUT:
%s
STDERR:
%s""" % (proc.returncode, stdout, stderr)
        self.assertEqual(0, proc.returncode, msg)
    setattr(RealCaseTest, funcname, test)

def _load_tests():
    _create_test('simple.xml')
    _create_test('cdata.xml')
    _create_test('qa.xml')

_load_tests()
