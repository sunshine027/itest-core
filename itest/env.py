import os

from itest.utils import query_pkg_info


class TestEnv(object):

    def __init__(self, env_settings, opts):
        self.opts = opts
        self.settings = env_settings
        if self.settings.TZ:
            os.environ['TZ'] = self.settings.TZ
            import time
            time.tzset()

    def __getattr__(self, name):
        if name == name.upper():
            return getattr(self.settings, name)
        raise AttributeError("has no attribute %s" % name)

    @property
    def cases_dir(self):
        return os.path.join(self.ENV_PATH, self.CASES_DIR)

    @property
    def fixtures_dir(self):
        return os.path.join(self.ENV_PATH, self.FIXTURES_DIR)

    def query_target(self):
        name = self.TARGET_NAME
        if not name:
            return

        ver = self.TARGET_VERSION
        if not ver:
            ver = query_pkg_info(name)

        return (name, ver)

    def query_dependencies(self):
        deps = self.DEPENDENCIES
        if deps:
            return [ (pkg, query_pkg_info(pkg))
                     for pkg in deps ]

    def get_tags(self):
        '''get all tags which consists of several parts:
        1.predefined in global settings
        2.defined in env settings
        3.from command line
        '''
        tags = []
        for tag in self.TAGS:
            if callable(tag):
                tag = tag()
            tags.append(tag)

        tags.extend(self.opts.tag)

        return list(set(filter(None, tags)))
