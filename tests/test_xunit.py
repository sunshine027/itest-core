import os
import xml.etree.ElementTree as ET


from base import cd, TestBase, runtest, CASES_PATH


class XunitTest(TestBase):

    @cd(CASES_PATH)
    def test_with_xunit(self):
        runtest("--with-xunit", "simple.xml")
        # check whether xml is valid
        ET.parse('xunit.xml')

    @cd(CASES_PATH)
    def test_without_xunit(self):
        runtest("simple.xml")
        self.assertFalse(os.path.exists("xunit.xml"))

    @cd(CASES_PATH)
    def test_xunit_file(self):
        runtest("--with-xunit", "--xunit-file=xunit2.xml", "simple.xml")
        self.assertTrue(os.path.exists("xunit2.xml"))

    @cd(CASES_PATH)
    def test_xml_validation(self):
        runtest("--with-xunit", "simple.xml", "simple_false.xml")
        ET.parse('xunit.xml')
