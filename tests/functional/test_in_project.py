from base import TestBase, cd, PROJ_PATH, PROJ_CASES_PATH, DATA_PATH


class InProjectTest(TestBase):

    @cd(PROJ_PATH)
    def test_copy_fixture(self):
        self.assertPass("cases/copy_fixture.xml")

    @cd(PROJ_CASES_PATH)
    def test_render_template_fixture(self):
        self.assertPass("template_fixture.xml")

    @cd(PROJ_CASES_PATH)
    def test_copy_dir_fixture(self):
        self.assertPass("copy_dir_fixture.xml")

    @cd(PROJ_CASES_PATH)
    def test_copy_dir_fixture(self):
        self.assertPass("copy_part_of_dir_fixture.xml")

    @cd(PROJ_CASES_PATH)
    def test_copy_dir_with_tailing_slash(self):
        self.assertPass("copy_dir_with_tailing_slash.xml")

    @cd(DATA_PATH)
    def test_argument_test_project_path(self):
        self.assertPass("--test-project-path=sample_project",
                        "sample_project/cases/copy_fixture.xml")
