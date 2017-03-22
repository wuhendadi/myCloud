__author__ = 'Fred'
# python -m unittest -v tests.test_relay

import sys
import os
import random
import unittest
import socket
import select
import json
import time
import struct
from threading import Thread, Event

# For run in console.
parent = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(parent)
sys.path.append(os.path.join(parent, 'src'))

from config import config
from message import Message, HubMessage, ECode, Type, RelayManagerMessage
from relay import RelayConnection

if config.HAS_POPOCLOUD or config.IS_TO_RELAY_MANAGER or config.IS_TO_HUB:
    raise RuntimeError('The test is only running in non-popocloud mode.')

RELAY_ADDR = '127.0.0.1'
RELAY_PORT = 8100
RELAY_CLIENT_PORT = 8120
HUB_ADDR = RELAY_ADDR
HUB_PORT = 8200


class TestBasic(unittest.TestCase):
    BOX_CONTENT = 'Box content.'
    CLIENT_CONTENT = 'Client content.'
    QUIT_BOX_CONTENT = 'Quit box.'

    def setUp(self):
        self.box_s = None # box server waiting socket.
        self.box_registered_event = None
        socket.setdefaulttimeout(5)

    @staticmethod
    def box_server_thread(self):
        content = {'deviceId': 'Box-Sn-Number', 'token': 'Box-Token-Number'}
        self.do_box_register(content)
        self.box_registered_event.set()
        relay_conn = RelayConnection(self.box_s)
        is_quit = False
        while not is_quit:
            read_list = [relay_conn]
            read_result, _, _ = select.select(read_list, [], [])
            for s in read_list:
                if s is relay_conn:
                    msg = Message(relay_conn.recv(config.SOCKET_RECV_LEN))
                    # import binascii
                    # print binascii.b2a_hex(msg.data)
                    self.assertTrue(msg.is_valid)
                    if msg.type == Type.CLIENT_DATA:
                        if msg.content == TestBasic.QUIT_BOX_CONTENT:
                            is_quit = True
                            break
                        print 'Get client data: %s.' % msg.content
                        self.assertEqual(msg.content, TestBasic.CLIENT_CONTENT)
                        relay_conn.send(Message.create_server_data_data(msg.uuid, TestBasic.BOX_CONTENT))
                    else:
                        print 'Get other message type %d in box.' % msg.type
        self.do_box_disconnect()

    def start_box_server(self):
        self.box_registered_event = Event()
        self.box_thread = Thread(target=TestBasic.box_server_thread, args=(self, ))
        self.box_thread.start()
        self.box_registered_event.wait()

    def stop_box_server(self):
        self.do_send_client_data(TestBasic.QUIT_BOX_CONTENT)

    def do_box_register(self, content):
        self.box_s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.box_s.connect((RELAY_ADDR, RELAY_PORT))
        self.box_s.send(Message.create_connect_data(content))
        msg = Message(self.box_s.recv(config.SOCKET_RECV_LEN))
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.type, Type.ACCEPT)
        self.assertTrue(isinstance(msg.content, dict))
        self.assertTrue('port' in msg.content)
        self.assertTrue(msg.content['port'])

    def do_box_disconnect(self):
        self.box_s.send(Message.create_disconnect_data())
        self.box_s.close()

    def do_send_client_data(self, content, reply_content=None):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((RELAY_ADDR, RELAY_CLIENT_PORT))
        s.send(content)
        if reply_content:
            self.assertEqual(s.recv(config.SOCKET_RECV_LEN), reply_content)
        time.sleep(1)
        s.close()

    def test_client_to_relay_to_box(self):
        self.start_box_server()
        self.do_send_client_data(TestBasic.CLIENT_CONTENT, TestBasic.BOX_CONTENT)
        self.stop_box_server()


class TestMessage(unittest.TestCase):
    def test_ping(self):
        data = Message.create_ping_data()
        target = '\x46\x88\x00\x07\x00\x00\x00\x00'
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.type, Type.PING)

    def test_ping_ack(self):
        data = Message.create_ping_ack_data()
        target = '\x46\x88\x00\x08\x00\x00\x00\x00'
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.type, Type.PING_ACK)

    def test_server_data(self):
        uuid = 0x80
        content = '\x81\x82\x83\x84'
        data = Message.create_server_data_data(uuid, content)
        target = '\x46\x88\x00\x11\x00\x00\x00\x0C'
        target += '\x00\x00\x00\x00\x00\x00\x00\x80'[::-1] # reverse
        target += content
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.uuid, uuid)
        self.assertEqual(msg.content, content)

    def test_connect(self):
        content = {'deviceId': '6CA1410B4F10EA00', 'token': '9774cea9831e5a0cde8b88b9102d4720'}
        body_len = len(json.dumps(content))
        data = Message.create_connect_data(content)
        target = '\x46\x88\x00\x01' + struct.pack('!i', body_len)
        target += json.dumps(content)
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.content['deviceId'], content['deviceId'])
        self.assertEqual(msg.content['token'], content['token'])

    def test_accept(self):
        content = {'port': '30000'}
        body_len = len(json.dumps(content))
        data = Message.create_accept_data(content)
        target = '\x46\x88\x00\x02' + struct.pack('!i', body_len)
        target += json.dumps(content)
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.content['port'], content['port'])

    def test_refuse(self):
        ecode = 0x5001
        data = Message.create_refuse_data(ecode)
        content = json.dumps({'reason': str(ecode), 'message': ''})
        target = '\x46\x88\x00\x04' + struct.pack('!i', len(content))
        target += content
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.ecode, ecode)

    def test_disconnect(self):
        data = Message.create_disconnect_data()
        target = '\x46\x88\x00\x05\x00\x00\x00\x00'
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)

    def test_close(self):
        data = Message.create_close_data()
        target = '\x46\x88\x00\x06\x00\x00\x00\x00'
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)

    def test_client_data(self):
        uuid = 0x80
        content = '\x81\x82\x83\x84'
        data = Message.create_client_data_data(uuid, content)
        target = '\x46\x88\x00\x12\x00\x00\x00\x0C'
        target += '\x00\x00\x00\x00\x00\x00\x00\x80'[::-1] # reverse
        target += content
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.uuid, uuid)
        self.assertEqual(msg.content, content)

    def test_server_error(self):
        uuid = 0x80
        ecode = 0x4001
        data = Message.create_server_error_data(uuid, ecode)
        content = json.dumps({'connection': str(uuid), 'error': str(ecode)})
        target = '\x46\x88\x00\x13' + struct.pack('!i', len(content))
        target += content
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.uuid, uuid)
        self.assertEqual(msg.ecode, ecode)

    def test_client_error(self):
        uuid = 0x80
        ecode = 0x5003
        data = Message.create_client_error_data(uuid, ecode)
        content = json.dumps({'connection': str(uuid), 'error': str(ecode)})
        target = '\x46\x88\x00\x14' + struct.pack('!i', len(content))
        target += content
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.uuid, uuid)
        self.assertEqual(msg.ecode, ecode)

    def test_pause(self):
        uuid = 0x80
        data = Message.create_pause_data(uuid)
        content = json.dumps({'connection': str(uuid)})
        target = '\x46\x88\x00\x22' + struct.pack('!i', len(content))
        target += content
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.uuid, uuid)

    def test_resume(self):
        uuid = 0x80
        data = Message.create_resume_data(uuid)
        content = json.dumps({'connection': str(uuid)})
        target = '\x46\x88\x00\x24' + struct.pack('!i', len(content))
        target += content
        self.assertEqual(data, target)
        msg = Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.uuid, uuid)


class TestHubConnection(unittest.TestCase):
    def setUp(self):
        self.is_get_heartbeat = False
        self.is_get_status = False
        # pass

    def test_hub_message(self):
        content = {'msgType': 100, 'serialNo': '6CA1270B4F10EEC2'}
        body_len = len(json.dumps(content))
        data = HubMessage.create_content_data(content)
        target = '\x46\x88' + struct.pack('!i', body_len)
        target += json.dumps(content)
        self.assertEqual(data, target)
        msg = HubMessage(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.content['msgType'], content['msgType'])
        self.assertEqual(msg.content['serialNo'], content['serialNo'])

    def test_receiving_message(self):
        """
        Status message or heartbeat message.
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HUB_ADDR, HUB_PORT))
        s.listen(5)
        relays = []
        self.is_get_heartbeat = False
        self.is_get_status = False
        while not self.is_get_heartbeat or not self.is_get_status:
            read_list = []
            read_list.append(s)
            read_list.extend(relays)
            read_result, _, _ = select.select(read_list, [], [])
            for r in read_result:
                if r is s:
                    c, addr = s.accept()
                    print 'Connected by %s' % repr(addr)
                    relays.append(c)
                elif r in relays:
                    self._handle_relay_connection(r)
        for c in relays: c.close
        s.close()

    def _handle_relay_connection(self, c):
        msg = HubMessage(c.recv(config.SOCKET_RECV_LEN))
        self.assertTrue(msg.is_valid)
        self.assertTrue(isinstance(msg.content, dict))
        if msg.content['msgType'] == 3:
            self.assertTrue('macAddr' in msg.content)
            self.assertTrue('cpuRatio' in msg.content)
            self.assertTrue('mIpAddress' in msg.content)
            self.assertTrue('memoryRatio' in msg.content)
            self.assertTrue('boxSerial' in msg.content)
            self.assertTrue('relayPort' in msg.content)
            self.assertTrue('clientPort' in msg.content)
            self.assertTrue('ioRatio' in msg.content)
            self.assertEqual(msg.content['relayServerType'], '1')
            self.assertTrue('status' in msg.content)
            print 'Get status info %s' % repr(msg.content)
            self.is_get_status = True
            content = {'msgType': 99, 'msgCode': 'R1001'}
            c.send(HubMessage.create_content_data(content))
        elif msg.content['msgType'] == 100:
            self.assertTrue('boxSerial' in msg.content)
            self.assertTrue('mIpAddress' in msg.content)
            self.assertTrue('relayServerType' in msg.content)
            print 'Get heartbeat info %s' % repr(msg.content)
            self.is_get_heartbeat = True
            content = {'msgType': 99, 'msgCode': 'R1001'}
            c.send(HubMessage.create_content_data(content))
        else:
            self.assertTrue(False)

    def test_validate_box_information(self):
        pass


class TestRelayManagerMessage(unittest.TestCase):
    def test_connect(self):
        content = {'token': 'd7acfc03714bae74387570a79a9bbebe'}
        body_len = len(json.dumps(content))
        data = RelayManagerMessage.create_connect_data(content)
        target = '\x46\x88\x00\x01' + struct.pack('!i', body_len)
        target += json.dumps(content)
        self.assertEqual(data, target)

    def test_accept(self):
        data = '\x46\x88\x00\x02\x00\x00\x00\x00'
        msg = RelayManagerMessage(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.msg_type, RelayManagerMessage.Type.ACCEPT)

    def test_refuse(self):
        data = '\x46\x88\x00\x04\x00\x00\x00\x04\x01\x50\x00\x00'
        msg = RelayManagerMessage(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.msg_type, RelayManagerMessage.Type.REFUSE)
        self.assertEqual(msg.ecode, 0x5001)

    def test_disconnect(self):
        data = RelayManagerMessage.create_disconnect_data()
        target = '\x46\x88\x00\x05\x00\x00\x00\x00'
        self.assertEqual(data, target)

    def test_heartbeat(self):
        data = RelayManagerMessage.create_heartbeat_data()
        target = '\x46\x88\x00\x07\x00\x00\x00\x00'
        self.assertEqual(data, target)

    def test_load_balance(self):
        content = {'cpuRatio': 82.35}
        body_len = len(json.dumps(content))
        data = RelayManagerMessage.create_load_balance_data(content)
        target = '\x46\x88\x00\x09' + struct.pack('!i', body_len)
        target += json.dumps(content)
        self.assertEqual(data, target)

if __name__ == '__main__':
    unittest.main(verbosity=3)
