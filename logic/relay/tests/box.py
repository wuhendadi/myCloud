# -*- coding: utf-8 -*-
__author__ = 'Fred'

# For run in console.
import os
import sys
parent = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(parent)
sys.path.append(os.path.join(parent, 'src'))

import socket
import time
import select
from message import Message, Type
from config import config
from relay import RelayConnection
import binascii

RELAY_ADDR = '127.0.0.1'
RELAY_PORT = 8100
RELAY_CLIENT_PORT = 8120
HUB_ADDR = RELAY_ADDR
HUB_PORT = 8200


def handle_file_download_with_client_broken_first(s):
    """ 模拟文件下载，对每个请求，返回5个包。
    TEST: 先知道client断开，再发送。
    """
    while True:
        msg = Message(s.recv(config.SOCKET_RECV_LEN))
        assert msg.is_valid
        assert msg.type == Type.CLIENT_DATA
        print 'Get client data: %s' % msg.content
        for i in range(5):
            content = 'Part %d' % i
            print 'Before send to client.'
            s.send(Message.create_server_data_data(msg.uuid, content))
            print 'After send to client: %s' % content
            rds, _, _ = select.select([s], [], [], 1)
            if rds:
                msg2 = Message(s.recv(config.SOCKET_RECV_LEN))
                assert msg2.is_valid
                if msg2.type == Type.CLIENT_ERROR:
                    print 'Get client error message.'
                    break


def handle_file_download_with_client_broken_unknown(s):
    """ 模拟文件下载，对每个请求，返回5个包。
    TEST: 发送的时候，得知客户端断开。
    """
    while True:
        msg = Message(s.recv(config.SOCKET_RECV_LEN))
        assert msg.is_valid
        if msg.type == Type.CLIENT_DATA:
            print 'Get client data: %s' % msg.content
            is_first_error = True
            is_break = False
            for i in range(5):
                content = 'Part %d' % i
                print 'Before send to client.'
                s.send(Message.create_server_data_data(msg.uuid, content))
                print 'After send to client: %s' % content
                rds, _, _ = select.select([s], [], [], 1)
                if rds:
                    msg2 = Message(s.recv(config.SOCKET_RECV_LEN))
                    assert msg2.is_valid
                    if msg2.type == Type.CLIENT_ERROR:
                        print 'Get client error message: %s' % str(is_first_error)
                        if is_first_error:
                            is_first_error = False
                        else:
                            is_break = True
                if is_break: break


def handle_file_download_with_client_no_recv(s):
    """ 模拟文件下载，对每个请求，返回5个包。
    TEST: 客户端不接收，Relay会阻塞吗？relay send to client会阻塞
    支持多客户端链接。
    """
    s.s.setblocking(False)
    clients = {}
    while True:
        try:
            msg = Message(s.recv(config.SOCKET_RECV_LEN))
            print binascii.b2a_hex(msg.data)
            assert msg.is_valid
            if msg.type == Type.CLIENT_DATA:
                print 'Get client data: %s' % msg.content
                assert not msg.uuid in clients.keys()
                client = dict()
                client['is_paused'] = False
                client['current'] = 0
                clients[msg.uuid] = client
            elif msg.type == Type.CLIENT_ERROR:
                print 'Get client %d error message.' % msg.uuid
                if msg.uuid in clients.keys():
                    del clients[msg.uuid]
            elif msg.type == Type.PAUSE:
                print 'Get pause request for client %d' % msg.uuid
                assert msg.uuid in clients.keys()
                client = clients[msg.uuid]
                client['is_paused'] = True
            elif msg.type == Type.RESUME:
                print 'Get resume request for client %d' % msg.uuid
                assert msg.uuid in clients.keys()
                client = clients[msg.uuid]
                client['is_paused'] = False
            elif msg.type == Type.CLOSE:
                print 'Quit box because of close message.'
                return
            else:
                print 'Get other message type: %d' % msg.type
        except socket.error as e:
            # print 'Receive failed'
            pass

        for uuid, client in clients.items():
            if not client['is_paused']:
                content = str(bytearray(8200))
                # print 'Before send to client.'
                s.send(Message.create_server_data_data(uuid, content))
                client['current'] += 1
                print 'Send msg %d to client %d.' % (client['current'], uuid)
            else:
                # print 'is_started: %s; is_paused: %s;' % (str(is_started), str(is_paused))
                pass

        time.sleep(1)


def handle_relay_close_message(s):
    """ 验证Box Relay Stop的时候，会发送CLOSE消息 """
    while True:
        msg = Message(s.recv(config.SOCKET_RECV_LEN))
        assert msg.is_valid
        if msg.type == Type.CLOSE:
            print 'Get CLOSE message from box relay.'
            break


def send_ping_message(s):
    while True:
        s.send(Message.create_ping_data())
        msg = Message(s.recv(config.SOCKET_RECV_LEN))
        assert msg.is_valid
        assert msg.type == Type.PING
        print 'Get PING from box relay.'
        time.sleep(1)


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((RELAY_ADDR, RELAY_PORT))
    content = {'deviceId': 'Box-Sn-Number', 'token': 'Box-Token-Number'}
    s.send(Message.create_connect_data(content))
    msg = Message(s.recv(config.SOCKET_RECV_LEN))
    assert msg.is_valid
    print 'Register response: %s' % msg.content

    # handle_file_download_with_client_broken_first(s)
    # handle_file_download_with_client_broken_unknown(s)

    # relay_conn = RelayConnection(s)
    # handle_file_download_with_client_no_recv(relay_conn)

    # handle_relay_close_message(s)
    send_ping_message(s)

main()

