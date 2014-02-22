from base import TestBase, CASES_PATH, cd


class SetupTeardownTest(TestBase):

    @cd(CASES_PATH)
    def test_setup_always_run(self):
        self.assertWithText(["-vv", "setup.xml"],
                            "This message only appears in setup section")

    @cd(CASES_PATH)
    def test_teardown_always_run(self):
        self.assertWithText(["-vv", "teardown.xml"],
                            "This message only appears in teardown section")

    @cd(CASES_PATH)
    def test_steps_wont_run_if_setup_failed(self):
        self.assertWithoutText(["-vv", "setup_failed.xml"],
                               "This message only appears in steps section")

    @cd(CASES_PATH)
    def test_vars_in_setup_can_be_saw_in_steps(self):
        self.assertPass("vars_in_setup.xml")

    @cd(CASES_PATH)
    def test_vars_in_setup_can_be_saw_in_teardown(self):
        self.assertWithText(["-vv", "vars_in_setup.xml"],
                            "value of a is 1")
