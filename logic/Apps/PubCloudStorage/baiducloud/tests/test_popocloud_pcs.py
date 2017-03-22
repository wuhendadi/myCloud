__author__ = 'Fred'

import unittest
import threading
import time
import hashlib

import sys
sys.path.append('/system/popocloud')

from ..popoCloudPCS import PopoCloudPCS

"""
RUN:
cd /system/popocloud && python -m Apps.PubCloudStorage.baiducloud.tests.test_popocloud_pcs TestPopoCloudPCS.test_upload_large_file
"""


class TestPopoCloudPCS(unittest.TestCase):
    LARGE_FILE_PATH = u'/mnt/disk1/part1/large_file3.mkv'
    REMOTE_PARENT = u'/mnt/disk1/part1'
    BUFFER_SIZE = 4096

    def setUp(self):
        self.__pcs = PopoCloudPCS(None)

    def tearDown(self):
        pass

    def __get_file_md5(self, file_path):
        md5 = hashlib.md5()
        with open(file_path, 'r') as file:
            bytes = file.read(TestPopoCloudPCS.BUFFER_SIZE)
            while(bytes):
                md5.update(bytes)
                bytes = file.read(TestPopoCloudPCS.BUFFER_SIZE)
        return md5.hexdigest()

    @staticmethod
    def do_upload_large_file(self, target_result, stop_event=None):
        res = self.__pcs.upload_large_file(TestPopoCloudPCS.LARGE_FILE_PATH,
                                           TestPopoCloudPCS.REMOTE_PARENT,
                                           u'overwrite',
                                           stop_event=stop_event)
        if res[u'result'] == 0:
            self.assertEqual(unicode(self.__get_file_md5(TestPopoCloudPCS.LARGE_FILE_PATH)),
                             res[u'data'][u'baidupcsmd5'])
        elif res[u'result'] == 1:
            print repr(res)
        self.assertEqual(res[u'result'], target_result)

    def test_upload_large_file_stop(self):
        stop_event = threading.Event()
        upload_thread = threading.Thread(target=TestPopoCloudPCS.do_upload_large_file,
                                         args=(self, 2, stop_event))
        upload_thread.start()
        time.sleep(5)
        stop_event.set()
        upload_thread.join()

    def test_upload_large_file(self):
        self.do_upload_large_file(self, 0)

if __name__ == '__main__':
    unittest.main(verbosity=3, argv=sys.argv)