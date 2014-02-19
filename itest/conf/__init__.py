'''
These LazyObject, LazySettings and Settings are mainly copied from Django
'''

import os
import imp
import time


class Settings(object):

    def __init__(self):
        self.env_root = None
        self.cases_dir = None
        self.fixtures_dir = None

    def load(self, mod):
        for name in dir(mod):
            if name == name.upper():
                setattr(self, name, getattr(mod, name))

        if hasattr(self, 'TZ') and self.TZ:
            os.environ['TZ'] = self.TZ
            time.tzset()

    def setup_test_project(self, test_project_root):
        self.env_root = os.path.abspath(test_project_root)
        self.cases_dir = os.path.join(self.env_root, self.CASES_DIR)
        self.fixtures_dir = os.path.join(self.env_root, self.FIXTURES_DIR)


settings = Settings()


def load_settings(test_project_root=None):
    global settings

    mod = __import__('itest.conf.global_settings',
                     fromlist=['global_settings'])
    settings.load(mod)

    if test_project_root:
        settings_py = os.path.join(test_project_root, 'settings.py')
        try:
            mod = imp.load_source('settings', settings_py)
        except (ImportError, IOError), e:
            raise ImportError("Could not import settings '%s' (Is it on "
                              "sys.path?): %s" % (settings_py, e))
        settings.load(mod)
        settings.setup_test_project(test_project_root)
