import os
import unittest
import subprocess


class RealCaseTest(unittest.TestCase):
    """
    Test methods will be loaded at runtime
    """


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

def _create_test(case_names, expect_pass=True, method_name=None):
    path = os.path.join(os.path.dirname(__file__), 'cases')
    if not method_name:
        method_name = 'test_%s' % case_names[0].replace('.', '_')

    def test(self):
        cmd = "cd %s; runtest -vv %s" % (path, ' '.join(case_names))
        ret, msg = _popen(cmd)
        if expect_pass:
            self.assertEqual(0, ret, msg)
        else:
            self.assertNotEqual(0, ret, msg)

    test.__name__ = method_name
    setattr(RealCaseTest, method_name, test)

def _create_test_in_tproj(name):
    path = os.path.join(os.path.dirname(__file__), 'tproj', 'cases')
    funcname = 'test_tproj_%s' % name.replace('.', '_')
    def test(self):
        cmd = "cd %s; runtest -vv %s" % (path, name)
        ret, msg = _popen(cmd)
        self.assertEquals(0, ret, msg)
    setattr(RealCaseTest, funcname, test)


def _load_tests():
    _create_test(['simple.xml'])
    _create_test(['simple_false.xml'], False)
    _create_test(['cdata.xml'])
    _create_test(['qa.xml'])
    _create_test(['content_fixture.xml'])
    _create_test(['simple.xml', 'cdata.xml'],
        method_name="test_multi_case_pass")
    _create_test(['simple.xml', 'simple_false.xml'], False,
        method_name="test_multi_case_failed")

    _create_test_in_tproj('copy_fixture.xml')
    _create_test_in_tproj('template_fixture.xml')

_load_tests()
