# -*- coding: utf-8 -*-

__author__ = 'Fred'

import socket
import time
from config import config

RELAY_ADDR = '127.0.0.1'
RELAY_PORT = 8100
RELAY_CLIENT_PORT = 8120
HUB_ADDR = RELAY_ADDR
HUB_PORT = 8200


def request_download_file_with_broken(s):
    """ 测试下载的中途断开连接。
    """
    s.send('Please get me a file.')
    print 'Send data to box.'
    for i in range(2):
        data = s.recv(config.SOCKET_RECV_LEN)
        print 'Get data from box: %s' % data


def request_download_file_with_no_recv(s):
    """ 测试下载的中途不接收，也不断开。
    和handle_file_download_with_client_no_recv对应。
    """
    s.send('Please get me a file.')
    print 'Send data to box.'
    current = 1
    while True:
        data = s.recv(config.SOCKET_RECV_LEN)
        if not data: break
        current += 1
        print 'Get data from box: %d' % current
        time.sleep(30)
        for i in range(60):
            data = s.recv(config.SOCKET_RECV_LEN)
            if not data: break
            current += 1
            print 'Get data from box: %d' % current


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((RELAY_ADDR, RELAY_CLIENT_PORT))

    request_download_file_with_broken(s)
    # request_download_file_with_no_recv(s)

    s.close()

main()
