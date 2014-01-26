'''
These LazyObject, LazySettings and Settings are mainly copied from Django
'''

import os
import imp
import time

from itest.conf import global_settings


ENVIRONMENT_VARIABLE = "ITEST_ENV_PATH"


class LazyObject(object):
    """
    A wrapper for another class that can be used to delay instantiation of the
    wrapped class.

    By subclassing, you have the opportunity to intercept and alter the
    instantiation. If you don't need to do that, use SimpleLazyObject.
    """
    def __init__(self):
        self._wrapped = None

    def __getattr__(self, name):
        if self._wrapped is None:
            self._setup()
        return getattr(self._wrapped, name)

    def __setattr__(self, name, value):
        if name == "_wrapped":
            # Assign to __dict__ to avoid infinite __setattr__ loops.
            self.__dict__["_wrapped"] = value
        else:
            if self._wrapped is None:
                self._setup()
            setattr(self._wrapped, name, value)

    def __delattr__(self, name):
        if name == "_wrapped":
            raise TypeError("can't delete _wrapped.")
        if self._wrapped is None:
            self._setup()
        delattr(self._wrapped, name)

    def _setup(self):
        """
        Must be implemented by subclasses to initialise the wrapped object.
        """
        raise NotImplementedError

    # introspection support:
    __members__ = property(lambda self: self.__dir__())

    def __dir__(self):
        if self._wrapped is None:
            self._setup()
        return  dir(self._wrapped)



class LazySettings(LazyObject):
    """
    A lazy proxy for either global Django settings or a custom settings object.
    The user can manually configure settings prior to using them. Otherwise,
    Django uses the settings module pointed to by DJANGO_SETTINGS_MODULE.
    """
    def _setup(self):
        """
        Load the settings module pointed to by the environment variable. This
        is used the first time we need any settings at all, if the user has not
        previously configured the settings manually.
        """
        if ENVIRONMENT_VARIABLE in os.environ and os.environ[ENVIRONMENT_VARIABLE]:
            self._wrapped = Settings(os.environ[ENVIRONMENT_VARIABLE])
        else:
            self._wrapped = Settings()


class Settings(object):

    def __init__(self, settings_module=None):
        # update this dict from global settings (but only for ALL_CAPS settings)
        for setting in dir(global_settings):
            if setting == setting.upper():
                setattr(self, setting, getattr(global_settings, setting))

        self._set_predefined_vars(settings_module)

        if settings_module:
            self._load_settings(settings_module)

    def _set_predefined_vars(self, settings_module):
        """
        Set some pre-defined variables
        """
        if settings_module:
            self.env_root = os.path.abspath(settings_module)
            self.cases_dir = os.path.join(self.env_root, self.CASES_DIR)
            self.fixtures_dir = os.path.join(self.env_root, self.FIXTURES_DIR)
        else:
            self.env_root = None
            self.cases_dir = None
            self.fixtures_dir = None

    def _load_settings(self, settings_module):
        """
        Load settings.py and overwrite the default global settings
        """
        settings_fname = os.path.join(self.env_root, 'settings.py')
        try:
            mod = imp.load_source('settings', settings_fname)
        except (ImportError, IOError), e:
            raise ImportError("Could not import settings '%s' (Is it on sys.path?): %s" % (settings_fname, e))

        for setting in dir(mod):
            if setting == setting.upper():
                setting_value = getattr(mod, setting)
                setattr(self, setting, setting_value)

        if self.TZ:
            os.environ['TZ'] = self.TZ
            time.tzset()



settings = LazySettings()
