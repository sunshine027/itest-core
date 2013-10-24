#!/usr/bin/env python
'''This script will cleanup resources allocated by unpack_image.py
'''
import os
import sys
from subprocess import call


def umount(path):
    '''Umount a mount point at path
    '''
    if not os.path.isdir(path) or not os.path.ismount(path):
        return

    cmd = ['sudo', 'umount', '-l', path]
    print "Umounting", path, "..."
    return call(cmd)

def loopdel(val):
    '''Release loop dev at val
    '''
    devloop, filename = val.split(':', 1)
    print "Releasing %s(%s)" % (devloop, filename), "..."


def main():
    '''Main'''
    # cleanup mountpoint in reverse order
    lines = sys.stdin.readlines()
    lines.sort(reverse=1)

    handler = {
        'mountpoint': umount,
        'loopdev': loopdel,
        }

    for line in lines:
        key, val = line.strip().split(':', 1)
        if key in handler:
            handler[key](val)
        else:
            print >> sys.stderr, "Have no idea to release:", line,


if __name__ == '__main__':
    main()
