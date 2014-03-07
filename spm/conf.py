import os
import yaml


def load_conf():
    conf_file = os.path.expanduser('/etc/spm.yml')
    conf = None
    if os.path.exists(conf_file):
        with open(conf_file) as fobj:
            conf = yaml.load(fobj)
    return conf
