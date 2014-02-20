from base import TestBase, cd, PROJ_PATH, PROJ_CASES_PATH


class InProjectTest(TestBase):

    @cd(PROJ_PATH)
    def test_copy_fixture_in_proj(self):
        self.assertPass("cases/copy_fixture.xml")

    @cd(PROJ_CASES_PATH)
    def test_render_template_fixture_in_proj(self):
        self.assertPass("template_fixture.xml")
