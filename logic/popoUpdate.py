# -*- coding: utf-8 -*-

import os
import urllib
import xml.dom.minidom
import zipfile
#import UtilFunc
import PopoConfig
#import Log

class CUpdate(object):
    
    def __init__(self):
        
        self.filePath = os.path.join('d:/', 'Apps')
        self.fileSize= 0

    def check(self, appid, ver, os="Linux_Box"):
        try:
            url = r"http://%s:%d/update?appid=%s&os=%s&lang=cn&version=%s&sn=%s" % (PopoConfig.UpgradeHost, PopoConfig.UpgradePort, appid, os, ver, '8989u21737816289372187')
            data = urllib.urlopen(url).read()
            doc = xml.dom.minidom.parseString(data)
            node = doc.getElementsByTagName('updatecheck')
            if node[0].getAttribute('status') != 'noupdate' :
                version = node[0].getAttribute('version')
                fileUrl = node[0].getAttribute('codebase')
                fileHase = node[0].getAttribute('hash')
                self.fileSize = node[0].getAttribute('size')
                if version and fileUrl and fileHase:
                    return version, fileUrl, fileHase
        except Exception,e:
            Log.error("CheckUpdate Failed! Reason:[%s]"%e)
            
        return None,None,None
        

    def unZip(self, base_dir, dest_dir):
        z = zipfile.ZipFile(base_dir)
        for f in z.namelist():
            dest_file = os.path.join(dest_dir, f)
            dest_file = dest_file.replace('\\', '/')
            if dest_file.endswith('/'):
                if not os.path.exists(os.path.dirname(dest_file)):os.makedirs(os.path.dirname(dest_file))
            else:
                if os.path.exists(dest_file): os.remove(dest_file)
                file(dest_file, 'wb').write(z.read(f))
        z.close()

    def isDownloaded(self, filepath, fileMD5):
        try:
            if os.path.exists(filepath):
                if fileMD5 == UtilFunc.getMd5OfFile(filepath):
                    return True
                else:
                    os.remove(filepath)
            return False
        except Exception,e:
            Log.error("UpData Download Failed! Reason[%s]"%e)
            return False

    def download(self, filepath, fileMD5, fileurl):
        try:
            if self.isDownloaded(filepath, fileMD5): return True
            urllib.urlretrieve(fileurl, filepath)
            if os.path.exists(fileMD5):
                os.remove(fileMD5)
            if fileMD5 == UtilFunc.getMd5OfFile(filepath):
                return True
        except Exception, e:
            Log.error("UpDate Download Failed! Reason[%s]"%e)
        return False
    
    def startUpadte(self, filename, dataPath):
        try:
            filePath = os.path.join(self.filePath,filename)
            self.unZip(dataPath, filePath)
            if os.path.exists(UtilFunc.getBoxUpLockPath() + "/upgrading.lock"):
                os.remove(UtilFunc.getBoxUpLockPath() + "/upgrading.lock")
            return True
        except Exception,e:
            Log.debug('PopoUpadte Failed! Reason:[%s]'%e)
            return False
    
        return False
             
if __name__ == '__main__':
    CUpdate().check('popoCloud.com', '2.2.2')
