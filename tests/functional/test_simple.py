from base import TestBase, CASES_PATH, cd


class BasicTest(TestBase):

    @cd(CASES_PATH)
    def test_simple(self):
        self.assertPass("simple.xml")

    @cd(CASES_PATH)
    def test_simple_false(self):
        self.assertFail("-vv", "simple_false.xml")

    @cd(CASES_PATH)
    def test_cdata(self):
        self.assertPass("cdata.xml")

    @cd(CASES_PATH)
    def test_qa(self):
        self.assertPass("qa.xml")

    @cd(CASES_PATH)
    def test_content_fixture(self):
        self.assertPass("content_fixture.xml")

    @cd(CASES_PATH)
    def test_multi_case_pass(self):
        self.assertPass("simple.xml", "cdata.xml")

    @cd(CASES_PATH)
    def test_multi_case_failed(self):
        self.assertFail("simple.xml", "simple_false.xml")

    @cd(CASES_PATH)
    def test_vars(self):
        self.assertPass("vars.xml")
