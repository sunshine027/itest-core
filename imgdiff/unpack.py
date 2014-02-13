#!/usr/bin/env python
'''This script unpack a whole image into a directory
'''
import os
import sys
import errno
import argparse
from subprocess import check_call

from imgdiff.info import get_partition_info, FSTab


def mkdir_p(path):
    '''Same as mkdir -p'''
    try:
        os.makedirs(path)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise


class ResourceList(object):
    '''
    Record all resource allocated into a file
    '''
    def __init__(self, filename):
        self.filename = filename

    def umount(self, path):
        '''record a mount point'''
        line = 'mountpoint:%s%s' % (os.path.abspath(path), os.linesep)
        with open(self.filename, 'a') as writer:
            writer.write(line)


class Mount(object):
    '''
    Mount image partions
    '''
    def __init__(self, limited_to_dir, resourcelist):
        self.limited_to_dir = limited_to_dir
        self.resourcelist = resourcelist

    def _check_path(self, path):
        '''Check whether path is ok to mount'''
        if not path.startswith(self.limited_to_dir):
            raise ValueError("Try to mount outside of jar: " + path)
        if os.path.ismount(path):
            raise Exception("Not allowed to override an exists "
                            "mountpoint: " + path)

        self.resourcelist.umount(path)
        mkdir_p(path)

    def mount(self, image, offset, fstype, path):
        '''Mount a partition starting from perticular
        position of a image to a direcotry
        '''
        self._check_path(path)
        cmd = ['sudo', 'mount',
               '-o', 'ro,offset=%d' % offset,
               '-t', fstype,
               image, path]
        print 'Mounting', '%d@%s' % (offset, image), '->', path, '...'
        check_call(cmd)

    def move(self, source, target):
        '''Remove mount point to another path'''
        self._check_path(target)
        cmd = ['sudo', 'mount', '--make-runbindable', '/']
        print 'Make runbindable ...', ' '.join(cmd)
        check_call(cmd)
        cmd = ['sudo', 'mount', '-M', source, target]
        print 'Moving mount point from', source, 'to', target, '...'
        check_call(cmd)


class Image(object):
    '''A raw type image'''
    def __init__(self, image):
        self.image = image
        self.partab = get_partition_info(self.image)

    @staticmethod
    def _is_fs_supported(fstype):
        '''Only support ext? and *fat*.
        Ignore others such as swap, tmpfs etc.
        '''
        return fstype.startswith('ext') or 'fat' in fstype

    def _mount_to_temp(self, basedir, mount):
        '''Mount all partitions into temp dirs like partx/p?
        '''
        num2temp, uuid2temp = {}, {}
        for part in self.partab:
            number = str(part['number'])
            fstype = part['blkid']['type']
            if not self._is_fs_supported(fstype):
                print >> sys.stderr, \
                    "ignore partition %s of type %s" % (number, fstype)
                continue

            path = os.path.join(basedir, 'partx', 'p'+number)
            mount.mount(self.image, part['start'], fstype, path)

            num2temp[number] = path
            uuid2temp[part['blkid']['uuid']] = path
        return num2temp, uuid2temp

    @staticmethod
    def _move_to_root(fstab, num2temp, uuid2temp, basedir, mount):
        '''Move partitions to their correct mount points according to fstab
        '''
        pairs = []
        for mountpoint in sorted(fstab.keys()):
            item = fstab[mountpoint]
            if 'number' in item and item['number'] in num2temp:
                source = num2temp[item['number']]
            elif 'uuid' in item and item['uuid'] in uuid2temp:
                source = uuid2temp[item['uuid']]
            else:
                print >> sys.stderr, "fstab mismatch with partition table:", \
                    item["entry"]
                return

            # remove heading / otherwise the path will reduce to root
            target = os.path.join(basedir, 'root',
                                  mountpoint.lstrip(os.path.sep))
            pairs.append((source, target))

        for source, target in pairs:
            mount.move(source, target)
        return True

    def unpack(self, basedir, resourcelist):
        '''Unpack self into the basedir and record all resource used
        into resourcelist
        '''
        mount = Mount(basedir, resourcelist)

        num2temp, uuid2temp = self._mount_to_temp(basedir, mount)

        fstab = FSTab.guess(num2temp.values())
        if not fstab:
            print >> sys.stderr, "Can't find fstab file from image"
            return
        return self._move_to_root(fstab,
                                  num2temp, uuid2temp,
                                  basedir, mount)


def parse_args():
    "Parse arguments"
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=os.path.abspath,
                        help='image file to unpack. Only raw format is '
                        'supported')
    parser.add_argument('basedir', type=os.path.abspath,
                        help='directory to unpack the image')
    parser.add_argument('resourcelist_filename', type=os.path.abspath,
                        help='will record each mount point when unpacking '
                        'the image. Make sure call cleanup script with this '
                        'file name to release all allocated resources.')
    return parser.parse_args()


def main():
    "Main"
    args = parse_args()
    img = Image(args.image)
    resfile = ResourceList(args.resourcelist_filename)
    return 0 if img.unpack(args.basedir, resfile) else 1


if __name__ == '__main__':
    sys.exit(main())
