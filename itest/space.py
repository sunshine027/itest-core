import os
import uuid
import fcntl
import errno
import shutil
import logging
import tempfile

from jinja2 import Environment, FileSystemLoader

from itest.conf import settings
from itest.case import sudo
from itest.utils import calculate_directory_size, makedirs


class TestSpace(object):

    def __init__(self, workdir):
        self.workdir = workdir
        self.logdir = os.path.join(workdir, 'logs')

    def setup(self, suite):
        makedirs(self.logdir)

    def new_test_dir(self, casever, casedir, fixtures):
        hash_ = str(uuid.uuid4()).replace('-', '')
        path = os.path.join(self.workdir, hash_)
        os.mkdir(path)
        self._copy_fixtures(path, casever, casedir, fixtures)
        return path

    def _copy_fixtures(self, todir, casever, casedir, fixtures):
        if casever != 'xml1.0' and settings.fixtures_dir:
            return self._copy_all_fixtures(todir)

        def _copy(source, target):
            makedirs(os.path.dirname(target))
            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy(source, target)

        def _template(source, target):
            template_dirs = [os.path.abspath(os.path.dirname(source))]
            if settings.fixtures_dir:
                template_dirs.append(settings.fixtures_dir)
            jinja2_env = Environment(loader=FileSystemLoader(template_dirs))
            template = jinja2_env.get_template(os.path.basename(source))
            text = template.render()

            makedirs(os.path.dirname(target))
            with open(target, 'w') as writer:
                writer.write(text)

        def _write(text, target):
            makedirs(os.path.dirname(target))
            with open(target, 'w') as writer:
                writer.write(text)

        for item in fixtures:
            if 'src' in item and item['src']:
                source = os.path.join(casedir, item['src'])
                if not os.path.exists(source) and settings.fixtures_dir:
                    source = os.path.join(settings.fixtures_dir, item['src'])
            else:
                source = None
            if 'target' in item and item['target']:
                target = os.path.join(todir, item['target'])
            else:
                target = os.path.join(todir, os.path.basename(source))

            if item['type'] == 'copy':
                _copy(source, target)
            elif item['type'] == 'template':
                _template(source, target)
            elif item['type'] == 'content':
                _write(item['text'], target)
            else:
                raise Exception("Unknown fixture type: %s" % item['type'])

    def _copy_all_fixtures(self, todir):
        for name in os.listdir(settings.fixtures_dir):
            source = os.path.join(settings.fixtures_dir, name)
            target = os.path.join(todir, name)

            if os.path.isdir(source):
                shutil.copytree(source, target)
            else:
                shutil.copy(source, target)
