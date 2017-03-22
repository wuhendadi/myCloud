# -*- coding: utf-8 -*-

"""
test stun : Please Change the 'STUN_SERVER_ADDRESS' and 
'PEER_ADDRESS' according to the actual situation
"""

import unittest
import uuid
import struct
import socket
import os
import sys
import time

parent = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(parent)
sys.path.append(os.path.join(parent, 'src'))

import stun
import utils

STUN_SERVER_ADDRESS = ('127.0.0.1', 8300)
# STUN_SERVER_ADDRESS = ('192.168.4.165', 3478)
# STUN_SERVER_ADDRESS = ('192.168.7.157', 3478)
# STUN_SERVER_ADDRESS = ('192.168.3.162', 3478)
# STUN_SERVER_ADDRESS = ('192.168.7.154', 3478)
PEER_ADDRESS = ('192.168.3.89', 3001)


class TestAttribute(unittest.TestCase):
    def test_mapped_address(self):
        ip = utils.ip2int('255.168.0.4')
        port = 8000
        data = stun.Attribute.create_mapped_address(stun.Family.IPV4, port, ip)
        target = struct.pack('!HHBBHI', 1, 8, 0, 1, port, ip)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.MAPPED_ADDRESS)
        self.assertEqual(attr.body['family'], stun.Family.IPV4)
        self.assertEqual(attr.body['port'], port)
        self.assertEqual(attr.body['ip'], ip)
        self.assertEqual(attr.body['addr'], (ip, port))

    def test_username(self):
        username = 'username'
        data = stun.Attribute.create_username_data(username)
        target = struct.pack('!HH8s', 6, 8, username)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.USERNAME)
        self.assertEqual(attr.body['username'], username)

    def __create_raw_msg(self, length):
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        return struct.pack('!HHI%ds' % len(tid), 1, length, 0x2112A442, tid)

    def test_message_integrity(self):
        import hashlib
        import passlib.utils
        import hmac
        hash_data = 'a' * 200
        data = stun.Attribute.create_message_integrity_data(hash_data)
        header = self.__create_raw_msg(len(data))
        data = stun.Attribute.create_message_integrity_data(header)
        msg = stun.Message(header + data)
        msg.remain_data = data
        key = hashlib.md5(stun.USERNAME + ':'
                          + stun.REALM + ':'
                          + stun.PASSWORD).digest()
        value = hmac.new(key, header, hashlib.sha1).digest()
        target = struct.pack('!HH%ds' % len(value), 8, len(value), value)
        self.assertEqual(target, data)
        attr = stun.Attribute(msg, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.MESSAGE_INTEGRITY)
        self.assertEqual(attr.body['hash-data'], header)
        self.assertEqual(attr.body['data'], value)

    def test_error_code(self):
        attrs_data = '\x00\x00\x00\x02' * 4
        data = stun.Attribute.create_error_code_data(stun.Message.ECode.UNKNOWN_ATTRIBUTES,
                                                     attrs_data=attrs_data)
        target = struct.pack('!HHHBB16s', 9, 20, 0, 4, 20, attrs_data)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.ERROR_CODE)
        self.assertEqual(attr.body['ecode'], stun.Message.ECode.UNKNOWN_ATTRIBUTES)

        data = stun.Attribute.create_error_code_data(stun.Message.ECode.BAD_REQUEST)
        target = struct.pack('!HHHBB', 9, 4, 0, 4, 0)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.ERROR_CODE)
        self.assertEqual(attr.body['ecode'], stun.Message.ECode.BAD_REQUEST)

        ecode = stun.Message.ECode.UNAUTHORIZED
        data = stun.Attribute.create_error_code_data(ecode)
        target = struct.pack('!HHHBB', 9, 4, 0, 4, 1)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.ERROR_CODE)
        self.assertEqual(attr.body['ecode'], ecode)

    def test_unknown_attributes(self):
        attrs = {stun.Attribute.XOR_MAPPED_ADDRESS: 'Test'}
        data = stun.Attribute.create_unknown_attributes_data(attrs)
        target = '\x00\x20\x00\x20'
        self.assertEqual(target, data)

    def test_realm(self):
        realm = 'realm'
        data = stun.Attribute.create_realm_data(realm)
        target = struct.pack('!HH5s3s', 0x14, 5, realm, '\x00')
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.REALM)
        self.assertEqual(attr.body['realm'], realm)

    def test_nonce(self):
        nonce = 'nonce'
        data = stun.Attribute.create_nonce_data(nonce)
        target = struct.pack('!HH5s3s', 0x15, 5, nonce, '\x00')
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.NONCE)
        self.assertEqual(attr.body['nonce'], nonce)

    def test_xor_mapped_address(self):
        ip = utils.ip2int('255.168.0.4')
        port = 0x8000
        data = stun.Attribute.create_xor_mapped_address_data(None, stun.Family.IPV4, port, ip)
        target = struct.pack('!HHBBHI', 0x20, 8, 0, 1,
                             port ^ (stun.Message.MAGIC >> 16),
                             ip ^ stun.Message.MAGIC)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.XOR_MAPPED_ADDRESS)
        self.assertEqual(attr.body['family'], stun.Family.IPV4)
        self.assertEqual(attr.body['port'], port)
        self.assertEqual(attr.body['ip'], ip)
        self.assertEqual(attr.body['addr'], (ip, port))

    def test_software(self):
        software = 'TRUN 1.0'
        data = stun.Attribute.create_software_data(software)
        target = struct.pack('!HH8s', 0x8022, 8, software)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.SOFTWARE)
        self.assertEqual(attr.body['software'], software)

    def test_alternate_server(self):
        pass

    def test_fingerprint(self):
        import binascii
        crc_data = 'a' * 200
        data = stun.Attribute.create_fingerprint_data(crc_data)
        header = self.__create_raw_msg(len(data))
        data = stun.Attribute.create_fingerprint_data(header)
        msg = stun.Message(header + data)
        msg.remain_data = data
        value = binascii.crc32(header) ^ 0x5354554e
        target = struct.pack('!HHi', 0x8028, 4, value)
        self.assertEqual(target, data)
        attr = stun.Attribute(msg, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.FINGERPRINT)

    def test_channel_number(self):
        number = 4
        data = stun.Attribute.create_channel_number_data(number)
        target = struct.pack('!HHHH', 0xC, 4, number, 0)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.CHANNEL_NUMBER)
        self.assertEqual(attr.body['number'], number)

    def test_lifetime(self):
        lifetime = 4
        data = stun.Attribute.create_lifetime_data(lifetime)
        target = struct.pack('!HHI', 0xD, 4, lifetime)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.LIFETIME)
        self.assertEqual(attr.body['lifetime'], lifetime)

    def test_bandwidth(self):
        pass

    def test_xor_peer_address(self):
        ip = utils.ip2int('255.168.0.4')
        port = 0x8000
        data = stun.Attribute.create_xor_peer_address_data(None, stun.Family.IPV4, port, ip)
        target = struct.pack('!HHBBHI', 0x12, 8, 0, 1,
                             port ^ (stun.Message.MAGIC >> 16),
                             ip ^ stun.Message.MAGIC)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.XOR_PEER_ADDRESS)
        self.assertEqual(attr.body['family'], stun.Family.IPV4)
        self.assertEqual(attr.body['port'], port)
        self.assertEqual(attr.body['ip'], ip)
        self.assertEqual(attr.body['addr'], (ip, port))

    def test_data(self):
        data_value = 'A' * 16
        data = stun.Attribute.create_data_data(data_value)
        target = struct.pack('!HH16s', 0x13, 16, data_value)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.DATA)
        self.assertEqual(attr.body['data'], data_value)

    def test_xor_relayed_address(self):
        ip = utils.ip2int('255.168.0.4')
        port = 0x8000
        data = stun.Attribute.create_xor_relayed_address_data(None, stun.Family.IPV4, port, ip)
        target = struct.pack('!HHBBHI', 0x16, 8, 0, 1,
                             port ^ (stun.Message.MAGIC >> 16),
                             ip ^ stun.Message.MAGIC)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.XOR_RELAYED_ADDRESS)
        self.assertEqual(attr.body['family'], stun.Family.IPV4)
        self.assertEqual(attr.body['port'], port)
        self.assertEqual(attr.body['ip'], ip)
        self.assertEqual(attr.body['addr'], (ip, port))

    def test_even_port(self):
        is_reserved = True
        data = stun.Attribute.create_even_port_data(is_reserved)
        target = struct.pack('!HHBBH', 0x18, 1, is_reserved << 7, 0, 0)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.EVEN_PORT)
        self.assertEqual(attr.body['is_reserved'], is_reserved)

    def test_requested_transport(self):
        protocol = 17
        data = stun.Attribute.create_requested_transport_data(protocol)
        target = struct.pack('!HHBBH', 0x19, 4, protocol, 0, 0)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.REQUESTED_TRANSPORT)
        self.assertEqual(attr.body['protocol'], protocol)

    def test_dont_fragment(self):
        data = stun.Attribute.create_dont_fragment_data()
        target = struct.pack('!HH', 0x1A, 0)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.DONT_FRAGMENT)

    def test_time_val(self):
        pass

    def test_reservation_token(self):
        token = 'token_ab'
        data = stun.Attribute.create_reservation_token_data(token)
        target = struct.pack('!HH8s', 0x22, 8, token)
        self.assertEqual(target, data)
        attr = stun.Attribute(None, data)
        self.assertTrue(attr.is_valid)
        self.assertEqual(attr.type, stun.Attribute.RESERVATION_TOKEN)
        self.assertEqual(attr.body['token'], token)


class TestMessage(unittest.TestCase):
    def test_parse_header(self):
        suffix = '\x00\x01'  # Request with binding.
        length = '\x00\x00'
        magic = '\x21\x12\xA4\x42'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        data = suffix + length + magic + tid
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.cls, stun.Message.Cls.REQUEST)
        self.assertEqual(msg.method, stun.Message.Method.BINDING)
        self.assertEqual(msg.tid, tid)

    def test_create_header(self):
        suffix = '\x01\x01'  # Response with binding.
        length = '\x00\x00'
        magic = '\x21\x12\xA4\x42'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        target = suffix + length + magic + tid
        data = stun.Message.create_success_response(tid)
        self.assertEqual(target, data)

    def test_create_msg_success_response(self):
        suffix = '\x01\x01'  # Success response with binding.
        length = '\x00\x04'
        magic = '\x21\x12\xA4\x42'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        attr = '\x01\x02\x03\x04'
        target = suffix + length + magic + tid + attr
        data = stun.Message.create_success_response(tid, [attr])
        self.assertEqual(target, data)

    def test_create_msg_error_response(self):
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        err_attr = '\x01\x02\x03\x04'
        data = stun.Message.create_error_response(tid, err_attr)
        suffix = '\x01\x11'  # Error response with binding.
        length = '\x00\x04'
        magic = '\x21\x12\xA4\x42'
        target = suffix + length + magic + tid + err_attr
        self.assertEqual(target, data)

    def test_create_attr_xor_mapped_address(self):
        ip, port = '192.168.0.0', 8888
        ip_val = utils.ip2int(ip)
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        data = stun.Attribute.create_xor_mapped_address_data(
            tid, stun.Family.IPV4, port, ip_val)
        port_val = port ^ (stun.Message.MAGIC >> 16)
        ip_val ^= stun.Message.MAGIC
        header = '\x00\x20\x00\x08'
        target = header + '\x00\x01' + struct.pack('!HI', port_val, ip_val)
        self.assertEqual(target, data)

    def test_create_attr_unknown_attributes(self):
        attrs = {
            1: '',
        }
        data = stun.Attribute.create_unknown_attributes_data(attrs)
        target = '\x00\x01\x00\x01'
        self.assertEqual(target, data)

    def test_create_attr_error_code(self):
        attr_data = '\x00\x01\x00\x01'
        data = stun.Attribute.create_error_code_data(
            stun.Message.ECode.UNKNOWN_ATTRIBUTES, attrs_data=attr_data)
        err = 420
        header = '\x00\x09\x00\x08'
        target = struct.pack('!4sI4s', header, ((err // 100) << 8) + (err % 100), attr_data)
        self.assertEqual(target, data)


class TestServer(unittest.TestCase):

    def setUp(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 8402))
        socket.setdefaulttimeout(5)

    def tearDown(self):
        self.__sock.close()

    def test_binding(self):
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        data = stun.Message.create_request_binding(tid)
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        print STUN_SERVER_ADDRESS
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(stun.Message.Cls.RESPONSE_SUCCESS, msg.cls)
        self.assertEqual(stun.Message.Method.BINDING, msg.method)
        # self.assertTrue(not msg.unknown_required_attribute)
        print msg.unknown_required_attribute
        attrs = msg.attributes
        # self.assertEqual([stun.Attribute.XOR_MAPPED_ADDRESS], attrs.keys())
        self.assertTrue(set([stun.Attribute.XOR_MAPPED_ADDRESS,]).issubset(attrs.keys()))
        xor = attrs[stun.Attribute.XOR_MAPPED_ADDRESS]
        self.assertTrue('family' in xor.body.keys())
        family = xor.body['family']
        self.assertTrue(family in [stun.Family.IPV4, stun.Family.IPV6])
        print xor.body['port']
        if family == stun.Family.IPV4:
            print utils.ip2str(xor.body['ip'])
        else:
            print utils.ip2str(xor.body['ip'])

    def test_turn_all(self):
        # First Allocate.
        print '[TEST] First ALLOCATE ...'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        username = 'username'
        username_attr = stun.Attribute.create_username_data(username)
        transport = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        data = stun.Message.create_request_allocate_without_message_integrity(tid, [username_attr, transport])
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.REALM,
                        stun.Attribute.NONCE,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.FINGERPRINT]
        # self.assertTrue(set(target_attrs).issubset(msg.attributes))
        self.assertTrue(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.UNAUTHORIZED)
        # self.assertTrue(msg.attributes[stun.Attribute.REALM].body['realm'], stun.REALM)
        nonce = msg.attributes[stun.Attribute.NONCE].body['nonce']
        print 'NONCE:', nonce
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)

        # Second Allocate
        print '[TEST] Second ALLOCATE ...'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        trans_attr = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr])
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        target_attrs = [stun.Attribute.XOR_RELAYED_ADDRESS,
                        stun.Attribute.LIFETIME,
                        stun.Attribute.XOR_MAPPED_ADDRESS,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        relayed_address = msg.attributes[stun.Attribute.XOR_RELAYED_ADDRESS].body['addr']
        lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        mapped_address = msg.attributes[stun.Attribute.XOR_MAPPED_ADDRESS].body['addr']
        print 'XOR_RELAYED_ADDRESS:', relayed_address
        print 'LIFETIME:', lifetime
        print 'XOR_MAPPED_ADDRESS:', mapped_address
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])

        # Create Permission
        print '[TEST] CREATE_PERMISSION ...'
        addr = utils.addr2int(PEER_ADDRESS)
        peer_addr_attr = stun.Attribute.create_xor_peer_address_data(
            tid, stun.Family.IPV4, addr[1], addr[0])
        data = stun.Message.create_request_create_permission(
            tid, [peer_addr_attr, username_attr, nonce_attr, realm_attr])
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        target_attrs = [stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])

        # Send
        print '[TEST] SEND ...'
        print 'Peer addr: %s' % str(PEER_ADDRESS)
        df_attr = stun.Attribute.create_dont_fragment_data()
        data_attr = stun.Attribute.create_data_data('Data from client')
        data = stun.Message.create_indication_send(
            tid, [df_attr, peer_addr_attr, data_attr])
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.INDICATION)
        self.assertEqual(msg.method, stun.Message.Method.DATA)
        target_attrs = [stun.Attribute.XOR_PEER_ADDRESS,
                        stun.Attribute.DATA]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        self.assertTrue(utils.addr2int(PEER_ADDRESS),
                        msg.attributes[stun.Attribute.XOR_PEER_ADDRESS].body['addr'])
        data = msg.attributes[stun.Attribute.DATA].body['data']
        print 'RECV', data

        # Refresh
        print '[TEST] REFRESH ...'
        lifetime_attr = stun.Attribute.create_lifetime_data(10 * 60)
        data = stun.Message.create_request_refresh(
            tid, [lifetime_attr, username_attr, nonce_attr, realm_attr])
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        target_attrs = [stun.Attribute.LIFETIME,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        print 'LIFETIME:', lifetime
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])

        # Channel Bind
        print '[TEST] CHANNEL_BIND ...'
        channel_number = 0x4000
        number_attr = stun.Attribute.create_channel_number_data(channel_number)
        data = stun.Message.create_request_channel_bind(
            tid, [number_attr, peer_addr_attr, username_attr, nonce_attr, realm_attr])
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        target_attrs = [stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])

        # Channel Message
        print '[TEST] Channel message ...'
        data = stun.ChannelDataMessage.create_data(channel_number, 'Data from channel by client.')
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)
        msg = stun.ChannelDataMessage(data)
        self.assertTrue(msg.is_valid)
        print 'RECV:', msg.body

        # Clear allocation
        print '[TEST] REFRESH to clear allocation ...'
        lifetime_attr = stun.Attribute.create_lifetime_data(0)
        data = stun.Message.create_request_refresh(
            tid, [lifetime_attr, username_attr, nonce_attr, realm_attr])
        self.__sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = self.__sock.recvfrom(2048)

class Authenticationtest(unittest.TestCase):
    
    @staticmethod
    def send_no_MESSAGE_INTEGRITY(self, sock, tid, method):
        print '[TEST] no MESSAGE_INTEGRITY ...(%s)'%method
        if method == 'allocate':
            data = stun.Message.create_request_allocate_without_message_integrity(tid, [])
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'refresh':
            data = stun.Message.create_request_refresh_without_message_integrity(tid, [])
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'createpermission':
            data = stun.Message.create_request_create_permission_without_message_integrity(tid, [])
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'channelbind':
            data = stun.Message.create_request_channel_bind_without_message_integrity(tid, [])
            sock.sendto(data, STUN_SERVER_ADDRESS)                                
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR) 
        print "msg.attributes :",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        if method == 'allocate':
            self.assertEqual(msg.method, stun.Message.Method.ALLOCATE) 
        elif method == 'refresh':
            self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        elif method == 'createpermission':
            self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        elif method == 'channelbind':
            self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)             
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.REALM,
                        stun.Attribute.NONCE,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.UNAUTHORIZED)
        self.assertEqual(msg.attributes[stun.Attribute.REALM].body['realm'], stun.REALM)
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.MESSAGE_INTEGRITY not in msg.attributes.keys())
    
    @staticmethod                   
    def send_missing_USERNAME_REALM_NONCE(self, sock, tid ,Attr, method):
        print '[TEST] MISSING USERNAME_REALM_NONCE...(%s)'%method
        attr_datas = []
        if 'U' in Attr:
            attr_datas.append(stun.Attribute.create_username_data('User'))
        if 'R' in Attr:
            attr_datas.append(stun.Attribute.create_realm_data('Realm'))
        if 'N' in Attr:
            attr_datas.append(stun.Attribute.create_nonce_data('Nonce'))
        
        if method == 'allocate':
            data = stun.Message.create_request_allocate(tid, attr_datas)
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'refresh':
            data = stun.Message.create_request_refresh(tid, attr_datas) 
            sock.sendto(data, STUN_SERVER_ADDRESS)   
        elif method == 'createpermission':
            data = stun.Message.create_request_create_permission(tid, attr_datas) 
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'channelbind':
            data = stun.Message.create_request_channel_bind(tid, attr_datas) 
            sock.sendto(data, STUN_SERVER_ADDRESS)
                      
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        if method == 'allocate':
            self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        elif method == 'refresh':
            self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        elif method == 'createpermission':
            self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        elif method == 'channelbind':
            self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
            
        target_attrs = [stun.Attribute.ERROR_CODE,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.BAD_REQUEST)
        target_attrs1 = [stun.Attribute.USERNAME,
                        stun.Attribute.REALM,
                        stun.Attribute.NONCE,
                        stun.Attribute.MESSAGE_INTEGRITY]
        for a in target_attrs1:
            self.assertTrue(a not in msg.attributes.keys())
            
    @staticmethod
    def send_invalid_nonce(self, sock, tid, nonce, method):
        print '[TEST] SEND INVALID NONCE...(%s)'%method
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        if method == 'allocate':
            data = stun.Message.create_request_allocate(tid, [username_attr, nonce_attr, realm_attr])
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'refresh':
            data = stun.Message.create_request_refresh(tid, [username_attr, nonce_attr, realm_attr])    
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'createpermission':
            data = stun.Message.create_request_create_permission(tid, [username_attr, nonce_attr, realm_attr])    
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'channelbind':
            data = stun.Message.create_request_channel_bind(tid, [username_attr, nonce_attr, realm_attr])    
            sock.sendto(data, STUN_SERVER_ADDRESS)
                    
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        if method == 'allocate':
            self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        elif method == 'refresh':
            self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        elif method == 'createpermission':
            self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        elif method == 'channelbind':
            self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
                
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.REALM,
                        stun.Attribute.NONCE,
                        ]
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.STALE_NONCE)
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.MESSAGE_INTEGRITY not in msg.attributes.keys())
    
    @staticmethod
    def send_invalid_username(self, sock, tid, nonce, method):
        print '[TEST] SEND INVALID USERNAME...(%s)'%method
        username = 'paopaoyun'
        username_attr = stun.Attribute.create_username_data(username)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        if method == 'allocate':
            data = stun.Message.create_request_allocate(tid, [username_attr, nonce_attr, realm_attr])
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'refresh':
            data = stun.Message.create_request_refresh(tid, [username_attr, nonce_attr, realm_attr])
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'createpermission':
            data = stun.Message.create_request_create_permission(tid, [username_attr, nonce_attr, realm_attr])
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'channelbind':
            data = stun.Message.create_request_channel_bind(tid, [username_attr, nonce_attr, realm_attr])
            sock.sendto(data, STUN_SERVER_ADDRESS)
                    
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        if method == 'allocate':
            self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        elif method == 'refresh':
            self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        elif method == 'createpermission':
            self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        elif method == 'channelbind':
            self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
                 
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.REALM,
                        stun.Attribute.NONCE,
                        ]
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.UNAUTHORIZED)
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.MESSAGE_INTEGRITY not in msg.attributes.keys())
    
    @staticmethod
    def send_WrongValue_MESSAGE_INTEGRITY(self, sock, tid, nonce, method):
        print '[TEST] SEND WrongValue MESSAGE_INTEGRITY...(%s)'%method
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        if method == 'allocate':
            data = stun.Message.create_request_allocate(tid, [username_attr, nonce_attr, realm_attr])
            data = data[:-12] + 'AAAA'
            data += stun.Attribute.create_fingerprint_data(data)
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'refresh':
            data = stun.Message.create_request_refresh(tid, [username_attr, nonce_attr, realm_attr])
            data = data[:-12] + 'AAAA'
            data += stun.Attribute.create_fingerprint_data(data)
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'createpermission':
            data = stun.Message.create_request_create_permission(tid, [username_attr, nonce_attr, realm_attr])
            data = data[:-12] + 'AAAA'
            data += stun.Attribute.create_fingerprint_data(data)
            sock.sendto(data, STUN_SERVER_ADDRESS)
        elif method == 'channelbind':
            data = stun.Message.create_request_channel_bind(tid, [username_attr, nonce_attr, realm_attr])
            data = data[:-12] + 'AAAA'
            data += stun.Attribute.create_fingerprint_data(data)
            sock.sendto(data, STUN_SERVER_ADDRESS)
                        
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        if method == 'allocate':
            self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        elif method == 'refresh':
            self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        elif method == 'createpermission':
            self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        elif method == 'channelbind':
            self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)                   
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.REALM,
                        stun.Attribute.NONCE,
                        ]
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.UNAUTHORIZED)
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.MESSAGE_INTEGRITY not in msg.attributes.keys())
    

class TestAllocate(unittest.TestCase):

    def setUp(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 8402))
        socket.setdefaulttimeout(5)

    def tearDown(self):
        self.__sock.close()
    
    @staticmethod
    def send_first(self, sock, tid):
        # sock, tid -> nonce
        print '[SEND] First ALLOCATE ...'
        username = 'username'
        username_attr = stun.Attribute.create_username_data(username)
        transport = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        data = stun.Message.create_request_allocate_without_message_integrity(tid, [username_attr, transport])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        print "msg.Attributes : ",msg.attributes
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.REALM,
                        stun.Attribute.NONCE,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        self.assertTrue(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.UNAUTHORIZED)
        self.assertTrue(msg.attributes[stun.Attribute.REALM].body['realm'], stun.REALM)
        nonce = msg.attributes[stun.Attribute.NONCE].body['nonce']
        print 'NONCE:', nonce
        return nonce
    
    @staticmethod
    def send_normal(self, sock, tid, nonce):
        print '[SEND] Normal ALLOCATE ...'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        trans_attr = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        print "msg.Attributes : ",msg.attributes
        target_attrs = [stun.Attribute.XOR_RELAYED_ADDRESS,
                        stun.Attribute.LIFETIME,
                        stun.Attribute.XOR_MAPPED_ADDRESS,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        relayed_address = msg.attributes[stun.Attribute.XOR_RELAYED_ADDRESS].body['addr']
        lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        mapped_address = msg.attributes[stun.Attribute.XOR_MAPPED_ADDRESS].body['addr']
        print 'XOR_RELAYED_ADDRESS:', relayed_address
        print 'LIFETIME:', lifetime
        print 'XOR_MAPPED_ADDRESS:', mapped_address
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])
    
    def send_missing_REQUESTED_TRANSPORT(self, sock, tid, nonce):
        print '[SEND]  MISSING REQUESTED_TRANSPORT ...'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.BAD_REQUEST)
    
    def send_unsupported_REQUESTED_TRANSPORT(self, sock, tid, nonce):
        print '[SEND] INVALID REQUESTED_TRANSPORT'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        trans = 111
        trans_attr = stun.Attribute.create_requested_transport_data(trans)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.UNSUPPORTED_TRANSPORT_PROTOCOL)
           
    def send_with_different_tid(self, sock, tid, nonce):
        print '[SEND] ALLOCATE with different tid ...'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        trans_attr = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        print "msg.Attributes : ",msg.attributes
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.ALLOCATION_MISMATCH)
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.REALM not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.NONCE not in msg.attributes.keys())
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])
    
    def send_include_lifetime(self, sock, tid, nonce, duration):
        print '[SEND]  INCLUDE LIFETIME ( %d )'% duration
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        trans_attr = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        lifetime_attr = stun.Attribute.create_lifetime_data(duration)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr, lifetime_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        print "msg.Attributes : ",msg.attributes
        target_attrs = [stun.Attribute.XOR_RELAYED_ADDRESS,
                        stun.Attribute.LIFETIME,
                        stun.Attribute.XOR_MAPPED_ADDRESS,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        print 'RESPONSE LIFETIME:', lifetime
        if 0 <= duration <= stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT:
            self.assertEqual(lifetime, stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT)
        elif stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT < duration <= stun.TIME_TO_EXPIRY_ALLOCATION_MAX:
            self.assertEqual(lifetime, duration)
        elif duration > stun.TIME_TO_EXPIRY_ALLOCATION_MAX:
            self.assertEqual(lifetime, stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT)         
        return lifetime
          
    def get_lifetime(self, sock, tid, nonce):
        print 'GET THE LIFETIME ...'
        lifetime = 1*60
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        trans_attr = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        lifetime_attr = stun.Attribute.create_lifetime_data(lifetime)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr, lifetime_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        target_attrs = [stun.Attribute.XOR_RELAYED_ADDRESS,
                        stun.Attribute.LIFETIME,
                        stun.Attribute.XOR_MAPPED_ADDRESS,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        response_lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        print 'LIFETIME:', response_lifetime
        return response_lifetime
        
    def send_include_DONT_FRAGMENT(self, sock, tid, nonce):
        print '[SEND]  INCLUDE DONT_FRAGMENT'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        trans_attr = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        dontfragment_attr = stun.Attribute.create_dont_fragment_data()
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr, dontfragment_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        print "msg.Attributes : ",msg.attributes
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        target_attrs = [stun.Attribute.XOR_RELAYED_ADDRESS,
                        stun.Attribute.LIFETIME,
                        stun.Attribute.XOR_MAPPED_ADDRESS,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
              
    def send_allocate_exceed_MAX(self, sock, tid, nonce):
        print '[SEND]  ALLOCATE EXCEED THE MAX'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        trans_attr = stun.Attribute.create_requested_transport_data(stun.Protocol.UDP)
        data = stun.Message.create_request_allocate(
            tid, [username_attr, nonce_attr, realm_attr, trans_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        self.assertEqual(msg.method, stun.Message.Method.ALLOCATE)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                        stun.Message.ECode.ALLOCATION_QUOTA_REACHED)
    @staticmethod
    def send_refresh(self, sock, tid, nonce, duration):
        print '[SEND] REFRESH (duration %d) ...' % duration
        lifetime_attr = stun.Attribute.create_lifetime_data(duration)
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        data = stun.Message.create_request_refresh(
            tid, [lifetime_attr, username_attr, realm_attr, nonce_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        target_attrs = [stun.Attribute.LIFETIME,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.REALM not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.NONCE not in msg.attributes.keys())
        lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        print 'LIFETIME:', lifetime
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])
    
    def test_no_MESSAGE_INTEGRITY(self):
        print '[TEST ALLOCATE] NO MESSAGE_INTEGRITY'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        Authenticationtest.send_no_MESSAGE_INTEGRITY(self,self.__sock, tid, 'allocate')
           
    def test_missing_the_USERNAME_REALM_NONCE(self):
        print '[TEST ALLOCATE] SEND MISSING USERNAME OR REALM OR NONCE'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        attrs_list = ['U', 'R', 'N', 'UR', 'UN', 'RN', '']
        for attrs in attrs_list:
            Authenticationtest.send_missing_USERNAME_REALM_NONCE(self, self.__sock, tid, attrs, 'allocate')
            
    def test_nonce_is_invalid(self):
        print '[TEST ALLOCATE] NONCE IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = '111222'
        Authenticationtest.send_invalid_nonce(self, self.__sock, tid, nonce, 'allocate')
        
    def test_username_is_invalid(self):
        print '[TEST ALLOCATE] USERNAME IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_invalid_username(self, self.__sock, tid, nonce, 'allocate')
        
    def test_MESSAGE_INTEGRITY_WrongValue(self):
        print '[TEST ALLOCATE] THE VALUE OF MESSAGE_INTEGRITY IS WRONG'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_WrongValue_MESSAGE_INTEGRITY(self, self.__sock, tid, nonce, 'allocate')    
    
    def test_missing_REQUESTED_TRANSPORT(self):
        print '[TEST ALLOCATE] MISSING REQUESTED_TRANSPORT'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = self.send_first(self, self.__sock, tid)
        self.send_missing_REQUESTED_TRANSPORT(self.__sock, tid, nonce)

    def test_REQUESTED_TRANSPORT_is_unsupported(self):
        print '[TEST ALLOCATE] REQUESTED_TRANSPORT UNSUPPORTED'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = self.send_first(self, self.__sock, tid)
        self.send_unsupported_REQUESTED_TRANSPORT(self.__sock, tid, nonce)
                
    def test_with_different_tid(self):
        print '[TEST ALLOCATE] WITH DIFFERENT TID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = self.send_first(self, self.__sock, tid)
        self.send_normal(self, self.__sock, tid, nonce)
        tid2 = str(uuid.uuid1())[:stun.Message.TID_LEN]
        self.send_with_different_tid(self.__sock, tid2, nonce)
        self.send_refresh(self, self.__sock, tid, nonce, 0)
        
    def test_with_same_tid(self):
        print '[TEST ALLOCATE] WITH SAME TID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = self.send_first(self, self.__sock, tid)
        for i in range(0, 2):
            self.send_normal(self, self.__sock, tid, nonce)
        self.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_include_lifetime(self):
        print '[TEST ALLOCATE] DIFFERENT LIFITIEM VALUE'
        lifetime_list = [0 * 60, 5 * 60, 20 * 60, 60 * 60, 61 * 60]
#         lifetime_list = [0 * 60]      
        addrs_list = [('192.168.3.89',3001)]
        for L in lifetime_list:
            tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
            nonce = self.send_first(self, self.__sock, tid)
            lifetime = self.send_include_lifetime(self.__sock, tid, nonce, L)
            print 'Sleep %d(s)'%(lifetime - 1 * 60)
            time.sleep(lifetime - 1 * 60)
            nonce_new = self.send_first(self, self.__sock, tid)
            TestCreatePermission.send_normal(self, self.__sock, tid, nonce_new, addrs_list)
            print 'Sleep %d(s)'%(2 * 60)
            time.sleep(2 * 60)
            nonce_new2 = self.send_first(self, self.__sock, tid)
            TestCreatePermission.send_no_allocation_exist(self, self.__sock, tid, nonce_new2)
    
    def test_lieftime_is_valid(self):
        print '[TEST ALLOCATE] LIFETIME IS VALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        print 'tid =',tid
        nonce = self.send_first(self, self.__sock, tid)
        self.send_normal(self, self.__sock, tid, nonce)
        lifetime = self.get_lifetime(self.__sock, tid, nonce)
        print 'Sleep %d(s)'%(lifetime - 10)
        time.sleep(lifetime - 10)
        nonce_new = self.send_first(self, self.__sock, tid)
        tid1 = str(uuid.uuid1())[:stun.Message.TID_LEN]
        print 'tid1 =',tid1
        self.send_with_different_tid(self.__sock, tid1, nonce_new) 
        print 'Sleep 15(s)'
        time.sleep(15)
        tid2 = str(uuid.uuid1())[:stun.Message.TID_LEN]       
        print 'tid2 =',tid2
        self.send_normal(self, self.__sock, tid2, nonce_new)
        self.send_refresh(self, self.__sock, tid2, nonce_new, 0)
       
    def test_include_DONT_FRAGMENT(self):
        print '[TEST ALLOCATE] INCLUDE DONT FRAGMENT'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = self.send_first(self, self.__sock, tid)
        self.send_include_DONT_FRAGMENT(self.__sock, tid, nonce)   
        self.send_refresh(self, self.__sock, tid, nonce, 0)    
    
    def test_CAPCITY_MAX_ALLOCATION(self):
        print '[TEST ALLOCATE] CAPCITY MAX ALLOCATION'
        argv_list = []
        for i in range(0,21):
            print "ALLCATION %d" %(i+1)
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            socket.setdefaulttimeout(5)
            tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
            nonce = self.send_first(self, sock, tid)
            if i <= 19:
                self.send_normal(self, sock, tid, nonce)
                argv_list.append((sock, tid, nonce))
                print "argv_list =", argv_list
            elif i > 19:
                self.send_allocate_exceed_MAX(sock, tid ,nonce)
        for S, T, N in argv_list:
            self.send_refresh(self, S, T, N, 0)

class TestRefresh(unittest.TestCase):
    
    def setUp(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 8402))
        socket.setdefaulttimeout(5)

    def tearDown(self):
        self.__sock.close()
    
    @staticmethod
    def send_include_lifetime_attr(self, sock, tid, nonce, duration):
        print '[SEND] INCLUDE LIFETIME: REFRESH (duration %d) ...' % duration
        lifetime_attr = stun.Attribute.create_lifetime_data(duration)
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        data = stun.Message.create_request_refresh(
            tid, [lifetime_attr, username_attr, realm_attr, nonce_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        target_attrs = [stun.Attribute.LIFETIME,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.REALM not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.NONCE not in msg.attributes.keys())
        lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        print 'LIFETIME:', lifetime
        if 0 < duration <= stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT:
            self.assertEqual(lifetime, stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT)
        elif stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT < duration <= stun.TIME_TO_EXPIRY_ALLOCATION_MAX or duration == 0:
            self.assertEqual(lifetime, duration)
        elif duration > stun.TIME_TO_EXPIRY_ALLOCATION_MAX:
            self.assertEqual(lifetime, stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT)         
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])
        return lifetime
    
    def send_no_lifetime_attr(self, sock, tid, nonce):
        print '[SEND] NO LIFETIE ATTR'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        data = stun.Message.create_request_refresh(
            tid, [username_attr, realm_attr, nonce_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        target_attrs = [stun.Attribute.LIFETIME,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.REALM not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.NONCE not in msg.attributes.keys())
        lifetime = msg.attributes[stun.Attribute.LIFETIME].body['lifetime']
        print 'LIFETIME:', lifetime
        self.assertEqual(lifetime, stun.TIME_TO_EXPIRY_ALLOCATION_DEFAULT)      
    
    def send_no_allocation_exist(self, sock, tid, nonce):
        print '[SEND] NO ALLOCATION EXIST'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        data = stun.Message.create_request_refresh(
            tid, [username_attr, realm_attr, nonce_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print "msg.Attributes : ",msg.attributes
        self.assertEqual(msg.method, stun.Message.Method.REFRESH)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.ALLOCATION_MISMATCH)
        self.assertTrue(stun.Attribute.USERNAME not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.REALM not in msg.attributes.keys())
        self.assertTrue(stun.Attribute.NONCE not in msg.attributes.keys()) 
                
    def test_no_MESSAGE_INTEGRITY(self):
        print '[TEST REFRESH] NO MESSAGE_INTEGRITY'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        Authenticationtest.send_no_MESSAGE_INTEGRITY(self,self.__sock, tid, 'refresh')
           
    def test_missing_the_USERNAME_REALM_NONCE(self):
        print '[TEST REFRESH] SEND MISSING USERNAME OR REALM OR NONCE'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        attrs_list = ['U', 'R', 'N', 'UR', 'UN', 'RN', '']
        for attrs in attrs_list:
            Authenticationtest.send_missing_USERNAME_REALM_NONCE(self, self.__sock, tid, attrs, 'refresh')
            
    def test_nonce_is_invalid(self):
        print '[TEST REFRESH] NONCE IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = '111222'
        Authenticationtest.send_invalid_nonce(self, self.__sock, tid, nonce, 'refresh')
        
    def test_username_is_invalid(self):
        print '[TEST REFRESH] USERNAME IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_invalid_username(self, self.__sock, tid, nonce, 'refresh')
        
    def test_MESSAGE_INTEGRITY_WrongValue(self):
        print '[TEST REFRESH] THE VALUE OF MESSAGE_INTEGRITY IS WRONG'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_WrongValue_MESSAGE_INTEGRITY(self, self.__sock, tid, nonce, 'refresh')    
    
    def test_include_lifetime_attr(self):
        print '[TEST REFRESH] TEST DEFFERENT LIFETIME'     
        lifetime_list = [5 * 60, 20 * 60, 60 * 60, 61 * 60]
#         lifetime_list = [5 * 60,61 * 60]
        addrs_list = [('192.168.3.89',3001)]
        for L in lifetime_list:
            tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
            nonce =TestAllocate.send_first(self, self.__sock, tid)
            TestAllocate.send_normal(self, self.__sock, tid, nonce)   
            lifetime = self.send_include_lifetime_attr(self, self.__sock, tid, nonce, L)
            print 'Sleep %d(s)'%(lifetime - 1 * 60)
            time.sleep(lifetime - 1 * 60)
            nonce_new =TestAllocate.send_first(self, self.__sock, tid)
            TestCreatePermission.send_normal(self, self.__sock, tid, nonce_new, addrs_list)
            print 'Sleep %d(s)'%(2 * 60)
            time.sleep(2 * 60)
            nonce_new2 =TestAllocate.send_first(self, self.__sock, tid)
            TestCreatePermission.send_no_allocation_exist(self, self.__sock, tid, nonce_new2)
    
    def test_no_lifetime_attr(self):
        print '[TEST REFRESH] TEST NO LIFETIME ATTR'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce =TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_no_lifetime_attr(self.__sock, tid, nonce)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)   
    
    def test_no_allocation_exist(self):
        print '[TEST REFRESH] TEST NO ALLOCATION EXITST'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce =TestAllocate.send_first(self, self.__sock, tid)
        self.send_no_allocation_exist(self.__sock, tid, nonce)
    
class TestCreatePermission(unittest.TestCase):
    
    def setUp(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 8402))
        socket.setdefaulttimeout(5)

    def tearDown(self):
        self.__sock.close()
    
    @staticmethod
    def send_normal(self, sock, tid, nonce, addrs_list):
        print '[SEND] NORMAL CREATEPERMISSION'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        attrs_list = [username_attr, realm_attr, nonce_attr]
        print addrs_list
        xor_peer_addr_attrs_list = []
        for ip, port in addrs_list:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_create_permission(tid,attrs_list )
        sock.sendto(data,STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        print "msg =",msg.attributes
        target_attrs = [stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])
    
    def send_xor_peer_address_exceed_max(self, sock, tid, nonce, addrs_list):
        print '[SEND] XOR PEER ADDRESS ATTRS EXCEED MAX'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        attrs_list = [username_attr, realm_attr, nonce_attr]
        print addrs_list
        xor_peer_addr_attrs_list = []
        for ip, port in addrs_list:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_create_permission(tid,attrs_list )
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.INSUFFICIENT_CAPACITY)
              
    def send_missing_xor_peer_address(self, sock, tid, nonce):
        print '[SEND] MISSING XOR PEER ADDRESS'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        data = stun.Message.create_request_create_permission(
            tid, [username_attr, nonce_attr, realm_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print 'msg ',msg.attributes
        self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.BAD_REQUEST)
    
    @staticmethod
    def send_no_allocation_exist(self, sock ,tid, nonce):
        print '[SEND] NO ALLOCATION EXIST'
        ip = utils.ip2int('192.168.3.1')
        port = 3000
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip)
        data = stun.Message.create_request_create_permission(
            tid, [username_attr, nonce_attr, realm_attr, xor_peer_addr_attr])
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        print 'msg ',msg.attributes
        self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.ALLOCATION_MISMATCH)
    
    def send_permission_exceed_max(self, sock, tid, nonce, addrs_list):
        print '[SEND] PERMISSION EXCEED MAX'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        attrs_list = [username_attr, realm_attr, nonce_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in addrs_list:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_create_permission(tid,attrs_list )
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        self.assertEqual(msg.method, stun.Message.Method.CREATE_PERMISSION)
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.INSUFFICIENT_CAPACITY)
           
    def test_no_MESSAGE_INTEGRITY(self):
        print '[TEST CREATEPERMISSION] NO MESSAGE_INTEGRITY'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        Authenticationtest.send_no_MESSAGE_INTEGRITY(self,self.__sock, tid, 'createpermission')
           
    def test_missing_the_USERNAME_REALM_NONCE(self):
        print '[TEST CREATEPERMISSION] SEND MISSING USERNAME OR REALM OR NONCE'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        attrs_list = ['U', 'R', 'N', 'UR', 'UN', 'RN', '']
        for attrs in attrs_list:
            Authenticationtest.send_missing_USERNAME_REALM_NONCE(self, self.__sock, tid, attrs, 'createpermission')
            
    def test_nonce_is_invalid(self):
        print '[TEST CREATEPERMISSION] NONCE IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = '111222'
        Authenticationtest.send_invalid_nonce(self, self.__sock, tid, nonce, 'createpermission')
        
    def test_username_is_invalid(self):
        print '[TEST CREATEPERMISSION] USERNAME IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_invalid_username(self, self.__sock, tid, nonce, 'createpermission')
        
    def test_MESSAGE_INTEGRITY_WrongValue(self):
        print '[TEST CREATEPERMISSION] THE VALUE OF MESSAGE_INTEGRITY IS WRONG'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_WrongValue_MESSAGE_INTEGRITY(self, self.__sock, tid, nonce, 'createpermission')    
    
    def test_send_normal(self):
        print '[TEST CREATEPERMISSION] TEST NORMAL REQUEST'
        addrs_list = [('192.168.3.89',3001)]
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_normal(self, self.__sock, tid, nonce, addrs_list)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_include_more_xor_peer_address(self):
        print '[TEST CREATEPERMISSION] TEST INCLUDE MORE XOR PEER ADDRESS'
        addrs_list = []
        for i in range(20):
            addrs_list.append(("192.168.3." + str(i + 1), 3001))
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_normal(self, self.__sock, tid, nonce, addrs_list)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_xor_peer_address_exceed_max(self):
        print '[TEST CREATEPERMISSION] TEST XOR PEER ADDRESS ATTRS EXCEED MAX'
        addrs_list = []
        for i in range(21):
            addrs_list.append(("192.168.3." + str(i + 1), 3001))
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_xor_peer_address_exceed_max(self.__sock, tid, nonce, addrs_list)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
        
    def test_missing_xor_peer_address(self):
        print '[TEST CREATEPERMISSION] TEST MISSING XOR PEER ADDRESS'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        self.send_missing_xor_peer_address(self.__sock, tid, nonce)
  
    def test_no_allocation_exist(self):
        print '[TEST CREATEPERMISSION] TEST NO ALLOCATION EXITST' 
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        self.send_no_allocation_exist(self, self.__sock, tid, nonce)
        
    def test_capcity_max_permission(self):
        print '[TEST CREATEPERMISSION] TEST CAPCITY MAX PERMISSION'       
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        i = 0
        while True:
            if i <= 19:
                print "CREATEPERMISSION %d" %(i+1)
                ip_addr = [("192.168.3." + str(i + 1), 3001)]
                self.send_normal(self, self.__sock, tid, nonce, ip_addr)
                i = i + 1
            elif i > 19:
                print "CREATEPERMISSION %d" %(i+1)
                ip_addr = [("192.168.3." + str(i + 1), 3001)]
                self.send_permission_exceed_max(self.__sock, tid, nonce, ip_addr)
                break
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
                     
class TestChannelBind(unittest.TestCase):
    
    def setUp(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 8402))
        socket.setdefaulttimeout(5)

    def tearDown(self):
        self.__sock.close()
    
    @staticmethod
    def send_normal(self, sock, tid, nonce, number, ip_addr):
        print '[SEND] NORMALL CHANNELBIND'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        channel_attr = stun.Attribute.create_channel_number_data(number)
        attrs_list = [username_attr, realm_attr, nonce_attr, channel_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_channel_bind(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_SUCCESS)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        print "msg =",msg.attributes
        target_attrs = [stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes))
        self.assertTrue(msg.attributes[stun.Attribute.SOFTWARE].body['software'], stun.SOFTWARE)
        hmac = stun.Attribute.get_hmac_sha1(
            msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['hash-data'],
            username=stun.USERNAME, realm=stun.REALM)
        self.assertEqual(hmac, msg.attributes[stun.Attribute.MESSAGE_INTEGRITY].body['data'])
    
    def send_missing_channel_number(self, sock, tid, nonce, ip_addr):
        print '[SEND] MISSING CHANNEL NUMBER'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        attrs_list = [username_attr, realm_attr, nonce_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_channel_bind(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.BAD_REQUEST)
    
    def send_missing_xor_peer_address(self, sock, tid, nonce, number):
        print '[SEND] MISSING XOR PEER ADDRESS'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        channel_attr = stun.Attribute.create_channel_number_data(number)
        attrs_list = [username_attr, realm_attr, nonce_attr, channel_attr]
        data = stun.Message.create_request_channel_bind(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.BAD_REQUEST)
    
    def send_channelnumber_out_of_range(self, sock, tid, nonce, number, ip_addr):
        print '[SEND] CHANNELNUMBER OUT OF RANGE'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        channel_attr = stun.Attribute.create_channel_number_data(number)
        attrs_list = [username_attr, realm_attr, nonce_attr, channel_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_channel_bind(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.BAD_REQUEST)
    
    def send_channelnumber_or_ipaddr_already_bound(self, sock, tid, nonce, number, ip_addr):
        print '[SEND] CHANNELNUMBER OR IP ADDR ALREADY BOUND'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        channel_attr = stun.Attribute.create_channel_number_data(number)
        attrs_list = [username_attr, realm_attr, nonce_attr, channel_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_channel_bind(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.BAD_REQUEST)
    
    def send_channelbind_exceed_max(self, sock, tid, nonce, number, ip_addr):
        print "[SEND] CHANNELBING EXCEED MAX"
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        channel_attr = stun.Attribute.create_channel_number_data(number)
        attrs_list = [username_attr, realm_attr, nonce_attr, channel_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_channel_bind(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.SOFTWARE,
                        stun.Attribute.MESSAGE_INTEGRITY,
                        stun.Attribute.FINGERPRINT]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.INSUFFICIENT_CAPACITY)
    
    def send_no_allocation_exist(self, sock, tid, nonce, number, ip_addr):
        print '[SEND] NO ALLOCATION EXIST'
        username_attr = stun.Attribute.create_username_data(stun.USERNAME)
        realm_attr = stun.Attribute.create_realm_data(stun.REALM)
        nonce_attr = stun.Attribute.create_nonce_data(nonce)
        channel_attr = stun.Attribute.create_channel_number_data(number)
        attrs_list = [username_attr, realm_attr, nonce_attr, channel_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_request_channel_bind(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.tid, tid)
        self.assertEqual(msg.cls, stun.Message.Cls.RESPONSE_ERROR)
        self.assertEqual(msg.method, stun.Message.Method.CHANNEL_BIND)
        print "msg =",msg.attributes
        print 'ECODE : ',msg.attributes[stun.Attribute.ERROR_CODE].body['ecode']
        target_attrs = [stun.Attribute.ERROR_CODE,
                        stun.Attribute.MESSAGE_INTEGRITY,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))
        self.assertEqual(msg.attributes[stun.Attribute.ERROR_CODE].body['ecode'],
                         stun.Message.ECode.ALLOCATION_MISMATCH)
        
    def test_no_MESSAGE_INTEGRITY(self):
        print '[TEST CHANNELBIND] NO MESSAGE_INTEGRITY'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        Authenticationtest.send_no_MESSAGE_INTEGRITY(self,self.__sock, tid, 'channelbind')
           
    def test_missing_the_USERNAME_REALM_NONCE(self):
        print '[TEST CHANNELBIND] SEND MISSING USERNAME OR REALM OR NONCE'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        attrs_list = ['U', 'R', 'N', 'UR', 'UN', 'RN', '']
        for attrs in attrs_list:
            Authenticationtest.send_missing_USERNAME_REALM_NONCE(self, self.__sock, tid, attrs, 'channelbind')
            
    def test_nonce_is_invalid(self):
        print '[TEST CHANNELBIND] NONCE IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = '111222'
        Authenticationtest.send_invalid_nonce(self, self.__sock, tid, nonce, 'channelbind')
        
    def test_username_is_invalid(self):
        print '[TEST CHANNELBIND] USERNAME IS INVALID'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_invalid_username(self, self.__sock, tid, nonce, 'channelbind')
        
    def test_MESSAGE_INTEGRITY_WrongValue(self):
        print '[TEST CHANNELBIND] THE VALUE OF MESSAGE_INTEGRITY IS WRONG'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        Authenticationtest.send_WrongValue_MESSAGE_INTEGRITY(self, self.__sock, tid, nonce, 'channelbind')    
    
    def test_send_normal(self):
        print '[TEST CHANNELBIND] NORMAL CHANNELBIND'
        addrs_list = [('192.168.3.89',3001)]
        channel_number = 0x4000
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
     
    def test_missing_channel_number(self):
        print '[TEST CHANNELBIND] MISSING CHANNEL NUMBER'
        addrs_list = [('192.168.3.89', 3001)]
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        self.send_missing_channel_number(self.__sock, tid, nonce, addrs_list)
    
    def test_missing_xor_peer_address(self):
        print '[TEST CHANNELBIND] MISSING XOR PEER ADDRESS'
        channel_number = 0x4000
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        self.send_missing_xor_peer_address(self.__sock, tid, nonce, channel_number)
        
    def test_channelnumber_out_of_range(self):
        print '[TEST CHANNELBIND] CHANNEL NUMBER IS OUT OF RANGE(0x4000~0x7FFE)'
        addrs_list = [('192.168.3.89', 3001)]
        channel_number = 0x3999
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_channelnumber_out_of_range(self.__sock, tid, nonce, channel_number, addrs_list)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
        
    def test_channelnumber_already_bound(self):
        print "[TEST CHANNELBIND] CHANNELNUMBER ALREADY BOUND"
        addrs_list = [('192.168.3.89', 3001)]
        channel_number = 0x4000
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        addrs_list2 = [('192.168.3.1', 3001)]
        self.send_channelnumber_or_ipaddr_already_bound(self.__sock, tid, nonce, channel_number, addrs_list2)        
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_ipaddr_already_bound(self):
        print '[TEST CHANNELBIND] IP ADDRS ALREADY BOUND'
        addrs_list = [('192.168.3.89', 3001)]
        channel_number = 0x4000
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        channel_number2 = 0x4001
        self.send_channelnumber_or_ipaddr_already_bound(self.__sock, tid, nonce, channel_number2, addrs_list)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_capcity_max_channelbind(self):
        print '[TEST CHANNELBIND] TEST CAPCITY MAX CHANNELBIND'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        i = 0
        channel = 0x4000
        while True:
            print 'CHANNEL BIND ( %d )' %(i+1)
            ip_addr = [['192.168.3' + str(i + 1), 3001]]
            channel_number = channel + i
            if i <= 19:
                self.send_normal(self, self.__sock, tid, nonce, channel_number, ip_addr)
                i = i + 1
            elif i > 19:
                self.send_channelbind_exceed_max(self.__sock, tid, nonce, channel_number, ip_addr)    
                break
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
        
    def test_no_allocation_exist(self):
        print '[TEST CHANNELBIND] TEST NO ALLOCATION EXIST'
        ip_addr = [('192.168.3.89', 3001)]
        channel_number = 0x4000
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        self.send_no_allocation_exist(self.__sock, tid, nonce, channel_number, ip_addr)

class TestSend(unittest.TestCase):
    
    def setUp(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 8402))
        socket.setdefaulttimeout(5)

    def tearDown(self):
        self.__sock.close()
    
    def send_normal(self, sock, tid, ip_addr, value):
        print '[SEND] NORMAL SEND INDICATION '
        data_attr = stun.Attribute.create_data_data(value)
        attrs_list = [data_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_indication_send(tid,attrs_list)
        print 'datalength:', len(data)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.cls, stun.Message.Cls.INDICATION)
        self.assertEqual(msg.method, stun.Message.Method.DATA)
        print "msg =",msg.attributes 
        target_attrs = [stun.Attribute.XOR_PEER_ADDRESS,
                        stun.Attribute.DATA,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))         
        print 'XOR_PEER_ADDRESS : ',msg.attributes[stun.Attribute.XOR_PEER_ADDRESS].body['addr']
        print 'DATA : ',msg.attributes[stun.Attribute.DATA].body['value']
    
    def send_include_dont_fragment_attr(self, sock, tid, ip_addr, value):
        print '[SEND] INCLUDE DONT FRAGMENT'
        data_attr = stun.Attribute.create_data_data(value)
        dont_fragment_attr = stun.Attribute.create_dont_fragment_data()
        attrs_list = [data_attr, dont_fragment_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_indication_send(tid,attrs_list)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.Message(data)
        self.assertTrue(msg.is_valid)
        self.assertEqual(msg.cls, stun.Message.Cls.INDICATION)
        self.assertEqual(msg.method, stun.Message.Method.DATA)
        print "msg =",msg.attributes 
        target_attrs = [stun.Attribute.XOR_PEER_ADDRESS,
                        stun.Attribute.DATA,]
        self.assertTrue(set(target_attrs).issubset(msg.attributes.keys()))         
        print 'XOR_PEER_ADDRESS : ',msg.attributes[stun.Attribute.XOR_PEER_ADDRESS].body['addr']
        print 'DATA : ',msg.attributes[stun.Attribute.DATA].body['value']
            
    def send_missing_xor_peer_address(self, sock, tid, value):
        print '[SEND] MISSING XOR PEER ADDRESS'
        data_attr = stun.Attribute.create_data_data(value)
        data = stun.Message.create_indication_send(tid,[data_attr])
        try:
            sock.sendto(data, STUN_SERVER_ADDRESS)
            data, addr = sock.recvfrom(2048)
            self.assertTrue(False)
        except socket.timeout, e:
            print 'error :', e
               
    def send_missing_data(self, sock, tid, ip_addr):
        print '[SEND] MISSING XOR PEER ADDRESS'
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        data = stun.Message.create_indication_send(tid,xor_peer_addr_attrs_list)
        try:
            sock.sendto(data, STUN_SERVER_ADDRESS)
            data, addr = sock.recvfrom(2048)
            self.assertTrue(False)
        except socket.timeout, e:
            print 'error :',e
        
    def send_no_allocation_or_permission(self, sock, tid, ip_addr, value):
        print '[SEND] NO ALLOCATION OR PERMISSION'
        data_attr = stun.Attribute.create_data_data(value)
        attrs_list = [data_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_indication_send(tid,attrs_list)
        try:
            sock.sendto(data, STUN_SERVER_ADDRESS)
            data, addr = sock.recvfrom(2048)
            self.assertTrue(False)
        except socket.timeout, e:
            print 'error :',e
    
    def send_time_to_expiry_permission(self, sock, tid, ip_addr, value):
        print '[SEND] TIME TO EXPIRY PERMISSION'
        data_attr = stun.Attribute.create_data_data(value)
        attrs_list = [data_attr]
        xor_peer_addr_attrs_list = []
        for ip, port in ip_addr:
            ip_data = utils.ip2int(ip)
            xor_peer_addr_attr = stun.Attribute.create_xor_peer_address_data(tid, stun.Family.IPV4, port, ip_data)
            xor_peer_addr_attrs_list.append(xor_peer_addr_attr)
        attrs_list.extend(xor_peer_addr_attrs_list)
        print 'attrs_list :',attrs_list
        data = stun.Message.create_indication_send(tid,attrs_list)
        try:
            sock.sendto(data, STUN_SERVER_ADDRESS)
            data, addr = sock.recvfrom(2048)
            self.assertTrue(False)
        except socket.timeout, e:
            print 'error :',e
    
    @staticmethod
    def FileConnect(self, path):
        path = path.replace("\\","/")
        a = open(path.decode('utf-8'),'rb')
        connect = a.read()
        statinfo = os.stat(path.decode('utf-8'))
        filesize = statinfo.st_size
        print filesize        
        return connect,filesize    
        
    def test_send_normal(self):
        print '[TEST SEND] NORMAL SEND INDICATION'
        ip_addr = [PEER_ADDRESS]
        data = 'A' * 16
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce, ip_addr)
        self.send_normal(self.__sock, tid, ip_addr, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)       
    
    def test_include_dont_fragment_attr(self):
        print '[TEST SEND] INCLUDE FRAGMENT ATTR'
        ip_addr = [PEER_ADDRESS]
        data = 'A' * 17
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce, ip_addr)
        self.send_include_dont_fragment_attr(self.__sock, tid, ip_addr, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)       
        
    def test_data_is_zero_length(self):
        print '[TEST SEND] DATA IS ZERO LENGTH'
        ip_addr = [PEER_ADDRESS]
        data = '' 
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce, ip_addr)
        self.send_normal(self.__sock, tid, ip_addr, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)     
    
    def test_missing_xor_peer_address(self):
        print '[TEST SEND] MISSING XOR PEER ADDRESS'
        ip_addr = [PEER_ADDRESS]
        data = 'B' * 16
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce, ip_addr)
        self.send_missing_xor_peer_address(self.__sock, tid, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0) 
    
    def test_missing_data(self):
        print '[TEST SEND] MISSING DATA'
        ip_addr = [PEER_ADDRESS]
        data = 'C' * 16
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce, ip_addr)
        self.send_missing_data(self.__sock, tid, ip_addr)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)     
        
    def test_no_allocation_exist(self):
        print '[TEST SEND] NO ALLOCATION EXIST'
        ip_addr = [PEER_ADDRESS]
        data = 'a' * 8
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        self.send_no_allocation_or_permission(self.__sock, tid, ip_addr, data)     
    
    def test_no_permission_exist(self):
        print '[TEST SEND] NO PERMISSION EXIST'
        ip_addr = [PEER_ADDRESS]
        data = 'b' * 8
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_no_allocation_or_permission(self.__sock, tid, ip_addr, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0) 
    
    def test_1k_message(self):
        print '[TEST SEND] MESSAGE IS 1K'
        ip_addr = [PEER_ADDRESS]
        filepath = r"E:\homecloud\test988B.txt"
        data, filesize = self.FileConnect(self, filepath)
        print 'filesizie =',filesize
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce, ip_addr)
        self.send_normal(self.__sock, tid, ip_addr, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)     
    
    def test_time_to_expiry_permission(self):
        print '[TEST SEND] TIME TO EXPIRY '
        ip_addr = [PEER_ADDRESS]
        data = 'A' * 16
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce, ip_addr)
        print 'start the first send:'
        self.send_normal(self.__sock, tid, ip_addr, data)
        print 'Sleep %d(s)'%(stun.TIME_TO_EXPIRY_PERMISSION - 10)
        time.sleep(stun.TIME_TO_EXPIRY_PERMISSION - 10)
        print 'start the second send: '
        data1 = 'B' * 16
        self.send_normal(self.__sock, tid, ip_addr, data1)
        print 'Sleep 15(s)'
        time.sleep(15)
        print 'start the third send'
        data2 = 'ok?'
        self.send_time_to_expiry_permission(self.__sock, tid, ip_addr, data2)
        nonce_new = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce_new, 0)       
    
class TestChannelData(unittest.TestCase):
    def setUp(self):
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind(('', 8402))
        socket.setdefaulttimeout(5)

    def tearDown(self):
        self.__sock.close()
    
    def send_normal(self, sock, channel_number, value):
        print '[SEND] NORMAL CHANNELDATA'
        data = stun.ChannelDataMessage.create_data(channel_number, value)
        print 'datalength :',len(data)
        sock.sendto(data, STUN_SERVER_ADDRESS)
        data, addr = sock.recvfrom(2048)
        msg = stun.ChannelDataMessage(data)
        self.assertTrue(msg.is_valid)
        print 'RECV:', msg.body
        print 'channel_number :',msg.number
        self.assertEqual(msg.number, channel_number)
    
    def send_channeldata_message_is_invalid(self, sock, channel_number, value):
        print '[SEND] CHANNEL NOT BOUND OR CHANNELNUMBER OUT OF RANGE'
        data = stun.ChannelDataMessage.create_data(channel_number, value)
        try:
            sock.sendto(data, STUN_SERVER_ADDRESS)
            data, addr = sock.recvfrom(2048)
            self.assertTrue(False)
        except socket.timeout, e:
            print 'error :',e
    
    def send_time_to_expiry_channel(self, sock, channel_number, value):
        print '[SEND] CHANNEL TIME TO EXPIRY'
        data = stun.ChannelDataMessage.create_data(channel_number, value)
        try:
            sock.sendto(data, STUN_SERVER_ADDRESS)
            data, addr = sock.recvfrom(2048)
            self.assertTrue(False)
        except socket.timeout, e:
            print 'error :',e
           
    def test_send_normal(self):
        print '[TEST CHANNELDATA] SEND NORMAL'
        addrs_list = [PEER_ADDRESS]
        channel_number = 0x4000
        data = 'Data from channel by client.'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestChannelBind.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        self.send_normal(self.__sock, channel_number, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_data_length_is_zero(self):
        print '[TEST CHANNELDATA] DATA LENGTH IS ZERO'
        addrs_list = [PEER_ADDRESS]
        channel_number = 0x4000
        data = ''
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestChannelBind.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        self.send_normal(self.__sock, channel_number, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_data_is_not_multiple_of_4(self):
        print '[TEST CHANNELDATA] DATA IS NOT MULTIPLE OF 4'
        addrs_list = [PEER_ADDRESS]
        channel_number = 0x4000
        data = 'the data is not multiple of 4'
        print len(data)
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestChannelBind.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        self.send_normal(self.__sock, channel_number, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_channel_not_bound(self):
        print '[TEST CHANELLDATA] CHANNEL NOT BOUND'
        channel_number = 0x4000
        data = 'Data from channel by client.'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        self.send_channeldata_message_is_invalid(self.__sock, channel_number, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_channelnumber_out_of_range(self):
        print '[TEST CHANNELDATA] CHANNELNUMBER OUT OF RANGE'
        addrs_list = [PEER_ADDRESS]
        channel_number = 0x4000
        data = 'Data from channel by client.'
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestChannelBind.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        invalid_channel_number = 0x8001
        self.send_channeldata_message_is_invalid(self.__sock, invalid_channel_number, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_1k_message(self):
        print '[TEST CHANNELDATA] MESSAGE IS 1K'
        addrs_list = [PEER_ADDRESS]
        channel_number = 0x4000
        filepath = r"E:\homecloud\test1020B.txt"
        data, filesize = TestSend.FileConnect(self, filepath)
        print 'filesizie =',filesize
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce = TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)
        TestChannelBind.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        self.send_normal(self.__sock, channel_number, data)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce, 0)
    
    def test_time_to_expiry_channel(self):
        print '[TEST CHANNELDATA] TIME TO EXPIRY CHANNEL'
        addrs_list = [PEER_ADDRESS]
        channel_number = 0x4000
        data = 'C' * 20
        tid = str(uuid.uuid1())[:stun.Message.TID_LEN]
        nonce =TestAllocate.send_first(self, self.__sock, tid)
        TestAllocate.send_normal(self, self.__sock, tid, nonce)        
        lifetime = 20 * 60
        TestRefresh.send_include_lifetime_attr(self, self.__sock, tid, nonce, lifetime)
        TestChannelBind.send_normal(self, self.__sock, tid, nonce, channel_number, addrs_list)
        print 'start the first send: '
        self.send_normal(self.__sock, channel_number, data)
        print 'Sleep %d(s)'%(stun.TIME_TO_EXPIRY_CHANNEL - 10)
        time.sleep(stun.TIME_TO_EXPIRY_CHANNEL - 10)
        print 'start the second channeldata'
        nonce_new =TestAllocate.send_first(self, self.__sock, tid)
        data1 = 'D' * 30
        TestCreatePermission.send_normal(self, self.__sock, tid, nonce_new, addrs_list)
        self.send_normal(self.__sock, channel_number, data1)
        print 'Sleep 15(s)'
        time.sleep(15)
        print 'start the third channeldata:'
        data2 = 'test time to expiry channel'
        self.send_time_to_expiry_channel(self.__sock, channel_number, data2)
        TestAllocate.send_refresh(self, self.__sock, tid, nonce_new, 0)
                       
if __name__ == '__main__':
    import sys
    sys.argv = ['',
#                 'TestAttribute',
#                 'TestMessage',
#                 'TestServer',
                'TestAllocate.test_no_MESSAGE_INTEGRITY',
                'TestAllocate.test_missing_the_USERNAME_REALM_NONCE',
                'TestAllocate.test_nonce_is_invalid',
                'TestAllocate.test_username_is_invalid',
                'TestAllocate.test_MESSAGE_INTEGRITY_WrongValue',
                'TestAllocate.test_missing_REQUESTED_TRANSPORT',
                'TestAllocate.test_REQUESTED_TRANSPORT_is_unsupported',
                'TestAllocate.test_with_different_tid',
#                 'TestAllocate.test_with_same_tid',
#                 'TestAllocate.test_include_lifetime', #测试时间较长，建议空闲时候进行测试
#                 'TestAllocate.test_lieftime_is_valid',#测试时间较长，建议空闲时候进行测试
#                 'TestAllocate.test_include_DONT_FRAGMENT',
#                 'TestAllocate.test_CAPCITY_MAX_ALLOCATION',#box server测试用例
#                 'TestRefresh.test_no_MESSAGE_INTEGRITY',
#                 'TestRefresh.test_missing_the_USERNAME_REALM_NONCE',
#                 'TestRefresh.test_nonce_is_invalid',
#                 'TestRefresh.test_username_is_invalid',
#                 'TestRefresh.test_MESSAGE_INTEGRITY_WrongValue',
#                 'TestRefresh.test_include_lifetime_attr', #测试时间较长，建议空闲时候进行测试
#                 'TestRefresh.test_no_lifetime_attr',
#                 'TestRefresh.test_no_allocation_exist',
#                 'TestCreatePermission.test_no_MESSAGE_INTEGRITY',
#                 'TestCreatePermission.test_missing_the_USERNAME_REALM_NONCE',
#                 'TestCreatePermission.test_nonce_is_invalid',
#                 'TestCreatePermission.test_username_is_invalid',
#                 'TestCreatePermission.test_MESSAGE_INTEGRITY_WrongValue',
#                 'TestCreatePermission.test_send_normal',
#                 'TestCreatePermission.test_include_more_xor_peer_address',
#                 'TestCreatePermission.test_xor_peer_address_exceed_max',#box server测试用例
#                 'TestCreatePermission.test_missing_xor_peer_address',
#                 'TestCreatePermission.test_no_allocation_exist',
#                 'TestCreatePermission.test_capcity_max_permission',#box server测试用例
#                 'TestChannelBind.test_no_MESSAGE_INTEGRITY',
#                 'TestChannelBind.test_missing_the_USERNAME_REALM_NONCE',
#                 'TestChannelBind.test_nonce_is_invalid',
#                 'TestChannelBind.test_username_is_invalid',
#                 'TestChannelBind.test_MESSAGE_INTEGRITY_WrongValue',
#                 'TestChannelBind.test_send_normal',
#                 'TestChannelBind.test_missing_channel_number',
#                 'TestChannelBind.test_missing_xor_peer_address',
#                 'TestChannelBind.test_channelnumber_out_of_range',
#                 'TestChannelBind.test_channelnumber_already_bound',
#                 'TestChannelBind.test_ipaddr_already_bound',
#                 'TestChannelBind.test_capcity_max_channelbind',#box server测试用例
#                 'TestChannelBind.test_no_allocation_exist',
#                 'TestSend.test_send_normal',
#                 'TestSend.test_include_dont_fragment_attr',
#                 'TestSend.test_data_is_zero_length',
#                 'TestSend.test_missing_xor_peer_address', #观察服务端打印：no XOR_PEER_ADDRESS or DATA attribute 
#                 'TestSend.test_missing_data', #观察服务端打印：no XOR_PEER_ADDRESS or DATA attribute
#                 'TestSend.test_no_allocation_exist', #观察服务端打印：No allocation exists
#                 'TestSend.test_no_permission_exist',  #观察服务端打印：[PEER] No permission                                               
#                 'TestSend.test_1k_message',
#                 'TestSend.test_time_to_expiry_permission',#测试时间较长，建议空闲时候进行测试
#                 'TestChannelData.test_send_normal',
#                 'TestChannelData.test_data_length_is_zero',
#                 'TestChannelData.test_data_is_not_multiple_of_4',
#                 'TestChannelData.test_channel_not_bound',
#                 'TestChannelData.test_channelnumber_out_of_range',
#                 'TestChannelData.test_1k_message',
#                 'TestChannelData.test_time_to_expiry_channel',#测试时间较长，建议空闲时候进行测试
                ]

    unittest.main(verbosity=3)
