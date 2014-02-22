import os
import shutil
from jinja2 import Environment, FileSystemLoader

from itest.conf import settings
from itest.utils import makedirs


def Fixture(casedir, item):
    typ = item.pop('type')
    cls = globals().get(typ)
    if not cls:
        raise Exception("Unknown fixture type: %s" % typ)
    return cls(casedir, **item)


def guess_source(casedir, src):
    source = os.path.join(casedir, src)
    if not os.path.exists(source) and settings.fixtures_dir:
        source = os.path.join(settings.fixtures_dir, src)
    return source


def guess_target(todir, src, target):
    if target:
        return os.path.join(todir, target)
    return os.path.join(todir, os.path.basename(src))


class copy(object):

    def __init__(self, casedir, src, target=None):
        self.source = guess_source(casedir, src)
        self.target = target
        if not os.path.isfile(self.source):
            raise Exception("Fixutre <copy> '%s' doesn't exist" % src)

    def copy(self, todir):
        target = guess_target(todir, self.source, self.target)
        makedirs(os.path.dirname(target))
        shutil.copy(self.source, target)


class copydir(object):

    def __init__(self, casedir, src, target=None):
        self.source = guess_source(casedir, src.rstrip(os.path.sep))
        self.target = target
        if not os.path.isdir(self.source):
            raise Exception("Fixture <copydir> '%s' doesn't exist" % src)

    def copy(self, todir):
        target = guess_target(todir,
                              self.source,
                              self.target).rstrip(os.path.sep)
        makedirs(os.path.dirname(target))
        shutil.copytree(self.source, target)


class content(object):

    def __init__(self, casedir, target, text):
        self.target = target
        self.text = text

    def copy(self, todir):
        target = os.path.join(todir, self.target)
        makedirs(os.path.dirname(target))
        with open(target, 'w') as writer:
            writer.write(self.text)


class template(object):

    def __init__(self, casedir, src, target=None):
        self.source = guess_source(casedir, src)
        self.target = target

    def copy(self, todir):
        target = guess_target(todir, self.source, self.target)

        template_dirs = [os.path.abspath(os.path.dirname(self.source))]
        if settings.fixtures_dir:
            template_dirs.append(settings.fixtures_dir)

        jinja2_env = Environment(loader=FileSystemLoader(template_dirs))
        template = jinja2_env.get_template(os.path.basename(self.source))
        text = template.render()

        makedirs(os.path.dirname(target))
        with open(target, 'w') as writer:
            writer.write(text)
