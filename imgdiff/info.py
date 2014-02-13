'''Get image information, such as partition table, block id fstab etc.
'''
import re
import os
import sys
from subprocess import check_output, CalledProcessError
from itertools import ifilter, islice, chain


def parted(img):
    "Parse output of parted command"
    column = re.compile(r'([A-Z][a-z\s]*?)((?=[A-Z])|$)')

    def parse(output):
        '''Example:
        Model:  (file)
        Disk /home/xxx/tmp/images/small.raw: 839909376B
        Sector size (logical/physical): 512B/512B
        Partition Table: msdos

        Number  Start      End         Size        Type     File system  Flags
         1      1048576B   34602495B   33553920B   primary  ext4         boot
         2      34603008B  839909375B  805306368B  primary  ext4
        '''
        state = 'header'
        headers = {}
        parts = []
        for line in output.splitlines():
            if state == 'header':
                if line == '':
                    state = 'title'
                else:
                    key, val = line.split(':', 1)
                    headers[key.lower()] = val.strip()
            elif state == 'title':
                titles = []
                start = 0
                for col, _ in column.findall(line):
                    title = col.rstrip().lower()
                    getter = slice(start, start+len(col))
                    titles.append((title, getter))
                    start += len(col)
                state = 'parts'
            elif line.strip():
                part = dict([(title, line[getter].strip())
                             for title, getter in titles])
                for title in ('start',):  # start, end, size
                    part[title] = int(part[title][:-1])  # remove tailing "B"
                part['number'] = int(part['number'])
                parts.append(part)
        return parts

    cmd = ['parted', img, '-s', 'unit B print']
    output = check_output(cmd)
    return parse(output)


def blkid(img, offset_in_bytes):
    "Parse output of blkid command"
    def parse(output):
        '''Example:
        sdb.raw: LABEL="boot" UUID="2995b233-ff79-4719-806d-d7f42b34a133" \
             VERSION="1.0" TYPE="ext4" USAGE="filesystem"
        '''
        output = output.splitlines()[0].split(': ', 1)[1]
        info = {}
        for item in output.split():
            key, val = item.split('=', 1)
            info[key.lower()] = val[1:-1]  # remove double quotes
        return info

    cmd = ['blkid', '-p', '-O', str(offset_in_bytes), '-o', 'full', img]
    output = check_output(cmd)
    return parse(output)


def gdisk(img):
    "Parse output of gdisk"
    cmd = ['gdisk', '-l', img]

    def parse(output):
        """Example:
        GPT fdisk (gdisk) version 0.8.1

        Partition table scan:
          MBR: protective
          BSD: not present
          APM: not present
          GPT: present

        Found valid GPT with protective MBR; using GPT.
        Disk tizen_20131115.3_ivi-efi-i586-sdb.raw: 7809058 sectors, 3.7 GiB
        Logical sector size: 512 bytes
        Disk identifier (GUID): 4A6D60CE-C42D-4A81-B82B-120624CE867E
        Partition table holds up to 128 entries
        First usable sector is 34, last usable sector is 7809024
        Partitions will be aligned on 2048-sector boundaries
        Total free space is 2049 sectors (1.0 MiB)

        Number  Start (sector)    End (sector)  Size       Code  Name
           1            2048          133085   64.0 MiB    EF00  primary
           2          133120         7809023   3.7 GiB     0700  primary
        """
        lines = output.splitlines()

        line = [i for i in lines if i.startswith('Logical sector size:')]
        if not line:
            raise Exception("Can't find sector size from gdisk output:%s:%s"
                            % (" ".join(cmd), output))
        size = int(line[0].split(':', 1)[1].strip().split()[0])

        parts = []
        lines.reverse()
        for line in lines:
            if not line.startswith(' ') or \
                    not line.lstrip().split()[0].isdigit():
                break
            number, start, _ = line.lstrip().split(None, 2)
            parts.append(dict(number=int(number), start=int(start)*size))
        return parts

    output = check_output(cmd)
    return parse(output)


class FSTab(dict):
    '''
    A dict representing fstab file.
    Key is <mount point>, corresponding value is its whole entry
    '''
    def __init__(self, filename):
        with open(filename) as stream:
            output = stream.read()
        data = self._parse(output)
        super(FSTab, self).__init__(data)

    FS = re.compile(r'/dev/sd[a-z](\d+)|UUID=(.*)')

    def _parse(self, output):
        '''Parse fstab in this format:
        <file system> <mount point> <type> <options> <dump> <pass>
        '''
        mountpoints = {}
        for line in output.splitlines():
            fstype, mountpoint, _ = line.split(None, 2)
            mres = self.FS.match(fstype)
            if not mres:
                continue

            number, uuid = mres.group(1), mres.group(2)
            if number:
                item = {"number": number}
            else:
                item = {"uuid": uuid}
            item["entry"] = line
            mountpoints[mountpoint] = item
        return mountpoints

    @classmethod
    def guess(cls, paths):
        '''Guess fstab location from all partitions of the image
        '''
        guess1 = (os.path.join(path, 'etc', 'fstab') for path in paths)
        guess2 = (os.path.join(path, 'fstab') for path in paths)
        guesses = chain(guess1, guess2)
        exists = ifilter(os.path.exists, guesses)
        one = list(islice(exists, 1))
        return cls(one[0]) if one else None


def get_partition_info(img):
    '''Get partition table information of image'''
    try:
        parts = parted(img)
    except CalledProcessError as err:
        print >> sys.stderr, err
        # Sometimes parted could failed with error
        # like this, then we try gdisk.
        # "Error during translation: Invalid or incomplete
        # multibyte or wide character"
        parts = gdisk(img)
    for part in parts:
        part['blkid'] = blkid(img, part['start'])
    return parts
