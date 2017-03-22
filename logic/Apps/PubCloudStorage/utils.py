import re
import os
import UtilFunc
from os.path import realpath, join, split, realpath
import threading
import ProfileFunc

logger = UtilFunc.getLogger()

class Lock():
    def __init__(self):
        self.__lock = threading.Lock()

    def __enter__(self):
        self.__lock.acquire()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.__lock.release()


def getMountInfoFromProc(mp=None, dev_node=None, path=None):
    with open(u'/proc/mounts') as fd:
        for line in fd:
            info = line.strip().split()
            if info[0][0] != u'/':
                continue

            if mp or dev_node:
                s = mp or dev_node
                if line.find(s) == -1:
                    continue
            elif path:
                if path.find(info[1]) == -1:
                    continue
            else:
                logger.error(u'getMountInfoFromProc should specified a argument')
                break

            dev_node = info[0]
            mp = info[1]
            #logger.debug(u'Find mounts info (%s, %s) for path %s' % (mp, dev_node, path))
            break

    return mp, dev_node

def getDevNodeAndDiskRoot(path):
    abs_path = realpath(path)

    mount, dev_node = getMountInfoFromProc(path=abs_path)
    if not mount:
        mount = None
        dev_node = None
        disk_path = unicode(path)
    else:
        disk_path = unicode(abs_path[len(mount):])

    return dev_node, disk_path

def getDiskUuidFromDevNd(dev_node):
    if not dev_node:
        logger.error(u'failed to get real disk uuid info, use fake one:kortidebackup!')
        return u'kortidebackup'

    cmdline = u'blkid | grep %s' % dev_node
    from Sitelib import libandroidmod
    data = libandroidmod.execute_shell(cmdline).strip().split()

    #data maybe empty string dur to popen default, just try again here
    if not data:
        data = libandroidmod.execute_shell(cmdline).strip().split()

    uuid_regex = re.compile(u'UUID=') #Fix me! Maybe another uuid form
    for element in data:
        try:
            disk_uuid = uuid_regex.split(element)[1].strip('"')
            trans_uuid = disk_uuid.replace(u'-',u'_')
            return unicode(trans_uuid)
        except IndexError:
            # Doesn't find uuid tag in this element
            continue
    logger.error(u'Error when get disk uuid, use default kortidebackup')
    return u'kortidebackup'

def getDiskMPFromUuid(trans_uuid):
    real_uuid = trans_uuid.replace(u'_', u'-')
    cmdline = u'blkid | grep %s' % real_uuid
    from Sitelib import libandroidmod
    data = libandroidmod.execute_shell(cmdline).split(os.linesep)

    #data maybe empty string due to popen default, just try again here
    if not data:
        data = libandroidmod.execute_shell(cmdline).split(os.linesep)

    mp = None
    for line in data:
        try:
            dev_node = line.split()[0].strip().strip(':')
            mp, node = getMountInfoFromProc(dev_node=dev_node)
            if mp:
                break
        except IndexError:
            continue
    return mp

def getPopoboxPathFromUuid(uuid_s):
    mount_point = getDiskMPFromUuid(uuid_s)
    #logger.debug(u'uuid %s mounted at %s'%(uuid_s, mount_point))
    path = None
    if mount_point:
        for disk in os.listdir(u'/popobox'):
            d = join(u'/mnt', disk)
            for part in os.listdir(d):
                path = join(d, part)
                path_mp = realpath(path)
                if path_mp == mount_point:
                    return ProfileFunc.get_label_name(unicode(path))

    return None

def getPathArchLevel(path):
    list = path.strip(os.sep).split(os.sep)
    level = len(list)   #the level of current path
    return level

if __name__ == u'__main__':
    while True:
        a = raw_input(u'Input path or q to quit')
        if a == u'q':
            break
        else:
            mount_point = getDevNodeAndDiskRoot(a)
            print getDiskUuidFromDevNd(mount_point)





