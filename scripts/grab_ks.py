import re
import os
import sys
import string
import shutil
import urllib
import logging
import datetime
import urlparse
import traceback
from collections import defaultdict

from urlgrabber.grabber import URLGrabber, URLGrabError


MIRROR_PATH = 'mirror'
SOCKET_TIMEOUT = 60 * 10


logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)
logger = logging



class URL(object):
    '''URL object with corresponding user and password'''

    AUTH = {
        'download.tizendev.org': {
            'user': 'xiaoning.zhu',
            'passwd': 'intel,123',
        },
        'download.tz.otcshare.org': {
            'user': 'hli85x',
            'passwd': 'intel,1234',
        },
    }

    def __init__(self, url, user=None, passwd=None):
        self.url = url
        if user or passwd:
            self.user, self.passwd = user, passwd
        else:
            self.user, self.passwd = self._check_user_passwd()

    def __str__(self):
        return self.url

    def _check_user_passwd(self):
        netloc = urlparse.urlsplit(self.url)[1]
        if netloc in self.AUTH:
            auth = self.AUTH[netloc]
            return auth['user'], auth['passwd']
        return None, None

    def full(self):
        '''return url embeded with user and passwd'''
        if not self.user or not self.passwd:
            return self.url

        parts = urlparse.urlsplit(self.url)

        userpass = '%s:%s' % (urllib.quote(self.user, safe=''),
                              urllib.quote(self.passwd, safe=''))
        netloc = '%s@%s' % (userpass, parts.netloc)
        comps = list(parts)
        comps[1] = netloc

        return urlparse.urlunsplit(comps)


class URLDirectoryService(object):

    # we think that link with same text and href is a subdir
    SUBDIR_PATTERN = re.compile(r'<a .*?href=(["\'])(.*?)\1.*?>(.*?)</a>')

    _grabber = None

    def parse_dir(self, page):
        '''Parse html page return sub-directory names'''
        dirs = []
        for _quote, href, text in re.findall(self.SUBDIR_PATTERN, page):
            if href == text:
                dirs.append(text.rstrip('/'))
        return dirs

    def listdir(self, url):
        '''give a url return all its sub directories'''
        # we have to add a '/' at the end of url like here, otherwise sever
        # will raise 401 error
        url.url = url.url.rstrip('/') + '/'

        fp = self.open(url)
        if fp:
            return self.parse_dir(fp.read())
        return []

    def join(self, base, *parts):
        '''join url path components'''
        user = None
        passwd = None
        if isinstance(base, URL):
            user = base.user
            passwd = base.passwd
            base = base.url

        return URL(os.path.join(base, *parts), user, passwd)

    def open(self, url):
        '''open an url and return a file-like object'''
        try:
            return self.grabber.urlopen(url.full(),
                                        ssl_verify_host=False,
                                        ssl_verify_peer=False,
                                        http_headers=(('Pragma', 'no-cache'),),
                                        quote=0,
                                        timeout=SOCKET_TIMEOUT,
                                        )
        except URLGrabError, err:
            # 14 - HTTPError (includes .code and .exception attributes)
            if err.errno == 14:
                if err.code == 404:
                    logger.error('No such url:404:%s' % url)
                    return None
                elif err.code == 401:
                    logger.error('Auth error:%s:%s' % (url, url.user))
                else:
                    logger.error('URL error:%s:%s' % (url, err))
            raise

    def grab(self, url, path):
        '''grab url and save it as path'''
        # urlgrab returns a path which will be different from pass-in path, but
        # it only occurs when copy_local==0 and url starts with file://, so we
        # ignore this case here. We assume that pass-in path will always equals
        # to the returned path.
        return self.grabber.urlgrab(url.full(), path,
                                    ssl_verify_host=False,
                                    ssl_verify_peer=False,
                                    http_headers=(('Pragma', 'no-cache'),),
                                    quote=0,
                                    timeout=SOCKET_TIMEOUT,
                                    )

    @property
    def grabber(self):
        '''only created one time for each service object'''
        if self._grabber is None:
            self._grabber = URLGrabber()
        return self._grabber


listdir = None
grab = None
join = None

def install_service(serv):
    '''install a service apis to global names'''
    global listdir
    global grab
    global join

    listdir = serv.listdir
    grab = serv.grab
    join = serv.join

install_service(URLDirectoryService())


IMAGES_URLS = (
    URL('http://download.tizen.org/snapshots/tizen/ivi/latest/images/'),
    URL('http://download.tizen.org/snapshots/tizen/mobile/latest/images/'),
    )


def clean():
    if os.path.exists(MIRROR_PATH):
        shutil.rmtree(MIRROR_PATH)


def mirror_images_url(url):
    '''Mirror all images start from this url
    For exmaple:
    http://download.tizen.org/snapshots/tizen/ivi/latest/images/
    http://download.tizen.org/snapshots/tizen/ivi/tizen_20130910.9/images/
    http://download.tizen.org/snapshots/tizen/mobile/latest/images/

    It will search and download all KS files recursively
    '''
    mirror = Mirror(MIRROR_PATH)

    for profile in listdir(url):
        path = join(url, profile)
        for filename in listdir(path):
            if filename.endswith('.ks'):
                ks = join(path, filename)
                mirror.download(ks)
                logger.info('found ks(%s)' % filename)


class Mirror(object):

    INDEX_NAME = 'index'

    def __init__(self, basedir):
        self.basedir = basedir
        self.index = os.path.join(basedir, self.INDEX_NAME)

    ESC_CHARS = string.punctuation.replace('.', '').replace('/', '')
    TRANSLATE_TABLE = string.maketrans(ESC_CHARS, '_'*len(ESC_CHARS))

    def _url_to_path(self, url):
        parts = urlparse.urlsplit(url)
        path = parts.path.lstrip('/').translate(self.TRANSLATE_TABLE)
        return os.path.join(parts.netloc, path)

    def download(self, url):
        name = self._url_to_path(url.url)
        ks = os.path.join(self.basedir, name)
        original_ks = ks + '.original'

        self._download(url, original_ks)
        self._replace_repo(url, original_ks, ks)
        self._write_index(name)

    def _download(self, url, path):
        dirp = os.path.dirname(path)

        if not os.path.exists(dirp):
            os.makedirs(dirp)

        grab(url, path)

    def _write_index(self, path):
        record = [
            datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
            path,
            ]

        with open(self.index, 'a') as f: # append mode
            print >> f, '\t'.join(record)

    def _replace_repo(self, url, before, after):
        prefix = url.url.split('/images/')[0]

        def _replace(line):
            if line.find('@BUILD_ID@') > 0:
                line = re.sub(r'(--baseurl=).*@BUILD_ID@',
                              r'\1%s' % prefix,
                              line)

            if url.user and url.passwd:
                line = re.sub(r'(--baseurl=.*://)',
                              r'\1%s:%s@' % (url.user, url.passwd),
                              line)
            return line

        with open(after, 'w') as to:
            with open(before) as from_:
                for line in from_:
                    if line.startswith('repo '):
                        line = _replace(line)
                    to.write(line)


def main():
    clean()
    for url in IMAGES_URLS:
        logger.info('mirror %s' % url)
        mirror_images_url(url)


if __name__ == '__main__':
    main()
