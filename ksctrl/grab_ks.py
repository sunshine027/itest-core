import re
import os
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


logging.basicConfig(filename='/dev/fd/1', level=logging.DEBUG)
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


DOMAINS = (
    URL('http://download.tizen.org/snapshots/2.0/'),
    URL('https://download.tizendev.org/snapshots/tizen-2.1/'),
    )

MORE_DISTROS = (
    URL('https://download.tz.otcshare.org/snapshots/trunk/pc/'),
    )


def clean():
    if os.path.exists(MIRROR_PATH):
        shutil.rmtree(MIRROR_PATH)


def main():
    clean()
    for domain in DOMAINS:
        logger.info('deal with doamin(%s)' % domain)
        try:
            deal_with_domain(domain)
        except Exception:
            traceback.print_exc()
            logger.error("Skip to next domain")

    for dist in MORE_DISTROS:
        logger.info('deal with dist(%s)' % dist)
        try:
            deal_with_dist(dist)
        except Exception:
            traceback.print_exc()
            logger.error("Skip to next dist")


def deal_with_domain(domain):
    for dist in listdir(domain):
        dist = join(domain, dist)
        logger.info('deal with dist(%s)' % dist)

        try:
            deal_with_dist(dist)
        except Exception:
            traceback.print_exc()
            logger.error("Skip to next dist")


class BuildIDFallbackStrategy(object):

    BUILDID_PATTERN = re.compile(r'_(\d{8}).(\d+)$')
    FALLBACK_DAYS = 7
    FALLBACK_NUMBERS = 3

    def __init__(self, build_ids):
        self.build_ids = build_ids

    def __iter__(self):
        count = defaultdict(int)
        ids = self._sort_by_date_and_number(self.build_ids)

        for date, number, bid in ids:
            count[date] += 1

            if len(count) > self.FALLBACK_DAYS:
                break

            if count[date] > self.FALLBACK_NUMBERS:
                continue

            yield bid

    def _sort_by_date_and_number(self, build_ids):
        ids = []
        for bid in build_ids:
            m = self.BUILDID_PATTERN.search(bid)
            if m:
                date, number = int(m.group(1)), int(m.group(2))
                ids.append((date, number, bid))

        ids.sort(reverse=1)
        return ids


def deal_with_dist(dist):
    '''distro argument is a distribution URL which contains many repos like
    "latest", "tizen-2.0_20130401.11", etc.

    It will search repos in desc order by time, return image device names.
    '''

    mirror = Mirror(MIRROR_PATH)

    def deal_with_device(repo, device):
        path = join(dist, repo, 'images', device)
        files = listdir(path)
        ks = '%s.ks' % device

        if len(files) <= 2 or ks not in files:
            return False

        # len(..) > 2 means there are more files besides ks and log
        # files in which situation, image may exist.
        ks = join(path, ks)
        logger.info('found ks(%s)' % ks)
        mirror.download(ks)
        return True

    repos = BuildIDFallbackStrategy(listdir(dist))
    path = join(dist, 'latest', 'images')

    for device in listdir(path):
        found = False
        for repo in repos:
            try:
                if deal_with_device(repo, device):
                    found = True
                    break
            except Exception:
                traceback.print_exc()
                logger.error("Skip to next device")
                break
            logger.warn('bad repo(%s), skip to previous' % repo)

        if not found:
            logger.error('Failed to find any avaiable ks for device(%s)' % device)


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



if __name__ == '__main__':
    main()
