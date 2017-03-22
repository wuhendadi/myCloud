# -*- coding: utf-8 -*-

""" Stun server.
"""

from config import config
import utils
from log import log

import struct
import socket
import binascii
import uuid
import select
import time
import Queue
import threading


REALM    = 'paopaoyun.com'
USERNAME = 'udprealayuser'
PASSWORD = 'elastos2014'
SOFTWARE = 'Popobox TURN Server 1.0'

TIME_TO_EXPIRY_ALLOCATION_DEFAULT       = 10 * 60
TIME_TO_EXPIRY_ALLOCATION_MAX           = 60 * 60
TIME_TO_EXPIRY_PERMISSION               =  5 * 60
TIME_TO_EXPIRY_CHANNEL                  = 10 * 60
TIME_TO_EXPIRE_ALLOCATION_DATA_TRANS    = 30 * 60

CAPCITY_MAX_ALLOCATION = 20
CAPCITY_MAX_PERMISSION = 20
CAPCITY_MAX_CHANNEL    = 20

MESSAGE_MAGIC_CHANNEL  = 0b01


class VerifyTokenData():
    def __init__(self, sock, addr, msg, method):
        self.sock = sock
        self.addr = addr
        self.msg = msg
        self.method = method


class ExpiredObj():
    def __init__(self, time_to_expiry):
        self.__origin = time_to_expiry
        self.refresh()

    def update(self):
        """ Update time by current timestamp.
        -> is_expired
        """
        self.__remain = self.__origin - (utils.get_current_timestamp() - self.__start)
        return self.is_expired

    def refresh(self):
        """ Refresh time to initialize value. """
        self.__start = utils.get_current_timestamp()
        self.__remain = self.__origin

    def refresh_to(self, value):
        self.__origin = value
        self.refresh()

    @property
    def is_expired(self):
        return self.__remain <= 0

    @property
    def time_to_expiry(self):
        return self.__remain if self.__remain > 0 else 0

    @time_to_expiry.setter
    def time_to_expiry(self, value):
        self.__remain = value


class TurnError(Exception):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


class Protocol:
    UDP = 17  # RFC5766/14.7

    @staticmethod
    def is_supported(protocol):
        return protocol in [Protocol.UDP]


class Family():
    IPV4 = 0x01
    IPV6 = 0x02

    IPV4_LEN = 4
    IPV6_LEN = 16


class Attribute():
    MAPPED_ADDRESS = 0x0001
    USERNAME = 0x0006
    MESSAGE_INTEGRITY = 0x0008
    ERROR_CODE = 0x0009
    UNKNOWN_ATTRIBUTES = 0x000A  # Only for error response.
    REALM = 0x0014
    NONCE = 0x0015
    XOR_MAPPED_ADDRESS = 0x0020
    SOFTWARE = 0x8022
    ALTERNATE_SERVER = 0x8023
    FINGERPRINT = 0x8028

    # INFO: For TURN
    CHANNEL_NUMBER = 0x000C
    LIFETIME = 0x000D
    BANDWIDTH = 0x0010  # reserved.
    XOR_PEER_ADDRESS = 0x0012
    DATA = 0x0013
    XOR_RELAYED_ADDRESS = 0x0016
    EVEN_PORT = 0x0018
    REQUESTED_TRANSPORT = 0x0019
    DONT_FRAGMENT = 0x001A
    TIMER_VAL = 0x0021  # reserved.
    RESERVATION_TOKEN = 0x0022

    __HEADER_LEN = 4
    __FINGERPRINT_XOR = 0x5354554e

    def __init__(self, msg, remain_data):
        """ data is Msg data un-parsed.
        """

        assert remain_data

        self.is_valid = False
        self.is_required = False
        self.is_supported = True
        self.body = {}
        self.__other = []

        remain_data_len = len(remain_data)
        if remain_data_len < Attribute.__HEADER_LEN:
            log.e('ATTR: Remained data length is less then header length.')
            return

        t, l = struct.unpack('!HH', remain_data[:Attribute.__HEADER_LEN])

        if l > remain_data_len - Attribute.__HEADER_LEN:
            log.e('ATTR: Invalid length value in header.')
            return

        r = l & 0b11
        p_l = (4 - r) if r else 0

        self.type = t
        self.body_len = l
        self.body['data'] = remain_data[Attribute.__HEADER_LEN: Attribute.__HEADER_LEN + self.body_len]
        self.length = l + Attribute.__HEADER_LEN
        self.length_with_padding = self.length + p_l
        self.is_required = 0x0000 <= t <= 0x7FFF

        # TODO: Support ALTERNATE-SERVER
        if self.type == Attribute.MAPPED_ADDRESS:
            if self.body_len < 4 + Family.IPV4_LEN:
                log.e('ATTR: MAPPED_ADDRESS: Body length is less than 8.')
                return
            family, port = struct.unpack('!HH', self.body['data'][:4])
            if family == Family.IPV4:
                if self.body_len != 4 + Family.IPV4_LEN:
                    log.e('ATTR: MAPPED_ADDRESS: Body length is not 8.')
                    return
                left = Attribute.__HEADER_LEN + 4
                val = struct.unpack('!I', self.body['data'][4:])[0]
                self.body['ip'] = val
            elif family == Family.IPV6:
                if self.body_len != 4 + Family.IPV6_LEN:
                    log.e('ATTR: MAPPED_ADDRESS: Body length is not 20.')
                    return
                ip, ip2 = struct.unpack('!QQ', self.bodyself.body[4:])
                self.body['ip'] = (ip << 64) + ip2
            else:
                log.e('ATTR: MAPPED_ADDRESS: Invalid family value.')
                return
            self.body['family'] = family
            self.body['port'] = port
            self.body['addr'] = (self.body['ip'], port)
            self.is_valid = True
        elif self.type == Attribute.ERROR_CODE:
            if self.body_len < 4:
                log.e('ATTR: ERROR_CODE: Body length is less than 4.')
                return
            _, cls, number = struct.unpack('!HBB', self.body['data'][:4])
            ecode = cls * 100 + number
            if ecode == Message.ECode.UNKNOWN_ATTRIBUTES:
                remain_attrs_data = self.body['data'][4:]
                self.body['attrs'] = []
                while remain_attrs_data:
                    self.body['attrs'].append(struct.unpack('!I', remain_attrs_data[:4]))
                    remain_attrs_data = remain_attrs_data[4:]
            elif ecode == Message.ECode.BAD_REQUEST \
                    or ecode == Message.ECode.UNAUTHORIZED \
                    or ecode == Message.ECode.FORBIDDEN \
                    or ecode == Message.ECode.ALLOCATION_MISMATCH \
                    or ecode == Message.ECode.STALE_NONCE \
                    or ecode == Message.ECode.ALLOCATION_QUOTA_REACHED \
                    or ecode == Message.ECode.UNSUPPORTED_TRANSPORT_PROTOCOL \
                    or ecode == Message.ECode.INSUFFICIENT_CAPACITY:
                pass
            else:
                log.e('ATTR: ERROR_CODE: Not implemented.')
                return
            self.body['ecode'] = ecode
            self.is_valid = True
        elif self.type == Attribute.REALM:
            if self.body_len == 0:
                log.e('ATTR: REALM: Body length is 0.')
                return
            self.body['realm'] = self.body['data']
            self.is_valid = True
        elif self.type == Attribute.NONCE:
            if self.body_len == 0:
                log.e('ATTR: NONCE: Body length is 0.')
                return
            self.body['nonce'] = self.body['data']
            self.is_valid = True
        elif self.type == Attribute.USERNAME:
            if self.body_len == 0:
                log.e('ATTR: USERNAME: Body length is 0.')
                return
            self.body['username'] = self.body['data']
            self.is_valid = True
        elif self.type == Attribute.XOR_MAPPED_ADDRESS \
                or self.type == Attribute.XOR_PEER_ADDRESS\
                or self.type == Attribute.XOR_RELAYED_ADDRESS:
            self.__parse_xor_address()
        elif self.type == Attribute.FINGERPRINT:
            if self.body_len != 4:
                log.e('ATTR: FINGERPRINT: Body length is not 4.')
                return
            crc_val = struct.unpack('!i', self.body['data'])[0] ^ Attribute.__FINGERPRINT_XOR
            crc = binascii.crc32(msg.data[: len(msg.data) - len(remain_data)])
            if crc_val != crc:
                log.e('ATTR: FINGERPRINT: CRC32 is unequal.')
                return
            self.is_valid = True
        elif self.type == Attribute.MESSAGE_INTEGRITY:
            if self.body_len == 0:
                log.e('ATTR: MESSAGE_INTEGRITY: Body length is 0.')
                return
            self.body['hash-data'] = msg.data[: len(msg.data) - len(remain_data)]
            self.is_valid = True
        elif self.type == Attribute.CHANNEL_NUMBER:
            if self.body_len != 4:
                log.e('ATTR: CHANNEL_NUMBER: Body length is not 4.')
                return
            self.body['number'], _ = struct.unpack('!HH', self.body['data'])
            self.is_valid = True
        elif self.type == Attribute.LIFETIME:
            if self.body_len != 4:
                log.e('ATTR: LIFETIME: Body length is not 4.')
                return
            self.body['lifetime'] = struct.unpack('!I', self.body['data'])[0]
            self.is_valid = True
        elif self.type == Attribute.DATA:
            # INFO: Body length may be zero.
            self.body['value'] = self.body['data']
            self.is_valid = True
        elif self.type == Attribute.EVEN_PORT:
            if self.body_len != 1:
                log.e('ATTR: EVEN_PORT: Body length is not 1.')
                return
            value = struct.unpack('!B', self.body['data'])[0]
            if value & 0x7F:
                log.e('ATTR: EVEN_PORT: RFFU is not 0.')
                return
            self.body['is_reserved'] = value == 0x80
            self.is_valid = True
        elif self.type == Attribute.REQUESTED_TRANSPORT:
            if self.body_len != 4:
                log.e('ATTR: REQUESTED_TRANSPORT: Body length is not 4.')
                return
            protocol, part2, part3 = struct.unpack('!BBH', self.body['data'])
            if part2 or part3:
                log.e('ATTR: REQUESTED_TRANSPORT: RFFU is not 0.')
                return
            self.body['protocol'] = protocol
            self.is_valid = True
        elif self.type == Attribute.DONT_FRAGMENT:
            if self.body_len != 0:
                log.e('ATTR: DONT_FRAGMENT: Body length is not 0.')
                return
            self.is_valid = True
        elif self.type == Attribute.RESERVATION_TOKEN:
            if self.body_len != 8:
                log.e('ATTR: RESERVATION_TOKEN: Body length is not 8.')
                return
            self.body['token'] = self.body['data']
            self.is_valid = True
        elif self.type == Attribute.SOFTWARE:
            if self.body_len == 0:
                log.e('ATTR: SOFTWARE: Body length is 0.')
                return
            self.body['software'] = self.body['data']
            self.is_valid = True
        else:
            self.is_supported = False
            self.is_valid = True

    def __parse_xor_address(self):
        """ Set self.body: 'family', 'port', 'ip'(int), and self.is_invalid
        """
        if self.body_len < 4 + Family.IPV4_LEN:
            log.e('ATTR: %d(type): Body length is less then 8.' % self.type)
            return
        family, port = struct.unpack('!HH', self.body['data'][:4])
        if family == Family.IPV4:
            if self.body_len != 4 + Family.IPV4_LEN:
                log.e('ATTR: %d(type): Body length is not 8.' % self.type)
                return
            left = Attribute.__HEADER_LEN + 4
            val = struct.unpack('!I', self.body['data'][4:])[0]
            self.body['ip'] = val ^ Message.MAGIC
        elif family == Family.IPV6:
            if self.body_len != 4 + Family.IPV6_LEN:
                log.e('ATTR: %d(type): Body length is not 20.' % self.type)
                return
            ip, ip2 = struct.unpack('!QQ', self.bodyself.body[4:])
            val = struct.pack('!I%ds' % Message.TID_LEN, Message.MAGIC, msg.tid)
            val1, val2 = struct.unpack('!QQ', val)
            self.body['ip'] = (ip ^ val1) << 64 + (ip2 ^ val2)
        else:
            log.e('ATTR: %d(type): Invalid family value.' % self.type)
            return
        self.body['family'] = family
        self.body['port'] = port ^ (Message.MAGIC >> 16)
        self.body['addr'] = (self.body['ip'], self.body['port'])
        self.is_valid = True

    def append(self, attr):
        assert attr.type == self.type
        self.__other.append(attr)

    def get_all(self):
        attrs = [self]
        attrs.extend(self.__other)
        return attrs

    @staticmethod
    def __create_attr_data(att_type, value=''):
        """ Create attribute data.
        -------------------------------------------------
        | type (16) | length (16)                        |
        -------------------------------------------------
        | value (variable)                               |
        -------------------------------------------------
        """
        pdata = utils.get_padding_data(value)
        fmt = '!HH%ds%ds' % (len(value), len(pdata))
        return struct.pack(fmt, att_type, len(value), value, pdata)

    @staticmethod
    def create_unknown_attributes_data(attrs):
        """ Just return value without attribute header.
        :param attrs: Message.unknown_required_attribute {}
        """
        attrs_values = attrs.keys()
        if len(attrs_values) % 2:
            # Padding by last attribute.
            attrs_values.append(attrs_values[-1])
        fmt = '!' + 'H' * len(attrs_values)
        return struct.pack(fmt, *attrs_values)

    @staticmethod
    def create_error_code_data(ecode, **kwargs):
        """ ERROR_CODE
        -------------------------------------------------
        | 0 (21) | class (3) | number (8)                |
        -------------------------------------------------
        """
        data = ''
        suffix = ((ecode // 100) << 8) + (ecode % 100)
        # TODO: Support other error code.
        if ecode == Message.ECode.UNKNOWN_ATTRIBUTES:
            attrs_data = kwargs.get('attrs_data', None)
            assert attrs_data
            data = struct.pack('!I%ds' % len(attrs_data), suffix, attrs_data)
        elif ecode == Message.ECode.BAD_REQUEST \
                or ecode == Message.ECode.UNAUTHORIZED \
                or ecode == Message.ECode.FORBIDDEN \
                or ecode == Message.ECode.ALLOCATION_MISMATCH \
                or ecode == Message.ECode.STALE_NONCE \
                or ecode == Message.ECode.ALLOCATION_QUOTA_REACHED \
                or ecode == Message.ECode.UNSUPPORTED_TRANSPORT_PROTOCOL \
                or ecode == Message.ECode.INSUFFICIENT_CAPACITY:
            data = struct.pack('!I', suffix)
        else:
            assert False
        return Attribute.__create_attr_data(Attribute.ERROR_CODE, data)

    @staticmethod
    def create_mapped_address(family, port, ip):
        """ MAPPED_ADDRESS
        ----------------------------------
        |  0 (8) | Family (8) | Port (16) |
        ----------------------------------
        | Address (32 bits or 128 bits)   |
        ----------------------------------
        :param ip: integer.
        """
        assert family & 0b11
        if family == Family.IPV6:
            ip_data = struct.pack('!QQ', ip >> 64, ip & 0xFFFFFFFF)
        else:
            ip_data = struct.pack('!I', ip)
        data = struct.pack('!BBH%ds' % len(ip_data), 0, family, port, ip_data)
        return Attribute.__create_attr_data(Attribute.MAPPED_ADDRESS, data)

    @staticmethod
    def __create_xor_address_data(tid, family, port, ip):
        """
        :param ip: integer.
        """
        port_val = port ^ (Message.MAGIC >> 16)
        assert family & 0b11
        if family == Family.IPV6:
            val = struct.pack('!I%ds' % Message.TID_LEN, Message.MAGIC, tid)
            val1, val2 = struct.unpack('!QQ', val)
            ip ^= (val1 << 64 + val2)
            ip_data = struct.pack('!QQ', ip >> 64, ip & 0xFFFFFFFF)
        else:
            ip_data = struct.pack('!I', ip ^ Message.MAGIC)
        return struct.pack('!BBH%ds' % len(ip_data), 0, family, port_val, ip_data)

    @staticmethod
    def create_xor_mapped_address_data(tid, family, port, ip):
        """ XOR_MAPPED_ADDRESS
        :param ip: integer.
        """
        d = Attribute.__create_xor_address_data(tid, family, port, ip)
        return Attribute.__create_attr_data(Attribute.XOR_MAPPED_ADDRESS, d)

    @staticmethod
    def create_realm_data(realm):
        return Attribute.__create_attr_data(Attribute.REALM, realm)

    @staticmethod
    def create_nonce_data(nonce):
        return Attribute.__create_attr_data(Attribute.NONCE, nonce)

    @staticmethod
    def create_username_data(username):
        return Attribute.__create_attr_data(Attribute.USERNAME, username)

    @staticmethod
    def create_fingerprint_data(crc_data):
        crc = binascii.crc32(crc_data) ^ Attribute.__FINGERPRINT_XOR
        d = struct.pack('!i', crc)
        return Attribute.__create_attr_data(Attribute.FINGERPRINT, d)

    @staticmethod
    def get_hmac_sha1(hash_data, is_short_term=False, username=None, password=None, realm=None):
        import passlib.utils
        import hmac
        import hashlib
        if is_short_term:
            key = passlib.utils.saslprep(unicode(PASSWORD))
        else:
            if username is None:
                username = USERNAME
            if password is None:
                password = PASSWORD
            if not realm:
                realm = REALM
            # password <- passlib.utils.saslprep(unicode(PASSWORD))).hexdigest()
            key = hashlib.md5(username + ':' + realm + ':' + password).digest()
        return hmac.new(key, hash_data, hashlib.sha1).digest()

    @staticmethod
    def create_message_integrity_data(hash_data, is_short_term=False):
        return Attribute.__create_attr_data(Attribute.MESSAGE_INTEGRITY,
                                            Attribute.get_hmac_sha1(hash_data, is_short_term))

    @staticmethod
    def create_channel_number_data(number):
        d = struct.pack('!HH', number, 0)
        return Attribute.__create_attr_data(Attribute.CHANNEL_NUMBER, d)

    @staticmethod
    def create_lifetime_data(lifetime):
        d = struct.pack('!I', lifetime)
        return Attribute.__create_attr_data(Attribute.LIFETIME, d)

    @staticmethod
    def create_xor_peer_address_data(tid, family, port, ip):
        """
        :param ip: integer.
        """
        d = Attribute.__create_xor_address_data(tid, family, port, ip)
        return Attribute.__create_attr_data(Attribute.XOR_PEER_ADDRESS, d)

    @staticmethod
    def create_data_data(value):
        return Attribute.__create_attr_data(Attribute.DATA, value)

    @staticmethod
    def create_xor_relayed_address_data(tid, family, port, ip):
        """
        :param ip: integer.
        """
        d = Attribute.__create_xor_address_data(tid, family, port, ip)
        return Attribute.__create_attr_data(Attribute.XOR_RELAYED_ADDRESS, d)

    @staticmethod
    def create_even_port_data(is_reserved):
        d = struct.pack('!B', (int(is_reserved) & 0b1) << 7)
        return Attribute.__create_attr_data(Attribute.EVEN_PORT, d)

    @staticmethod
    def create_requested_transport_data(protocol):
        d = struct.pack('!BBH', protocol, 0, 0)
        return Attribute.__create_attr_data(Attribute.REQUESTED_TRANSPORT, d)

    @staticmethod
    def create_dont_fragment_data():
        return Attribute.__create_attr_data(Attribute.DONT_FRAGMENT)

    @staticmethod
    def create_reservation_token_data(token):
        assert len(token) == 8
        return Attribute.__create_attr_data(Attribute.RESERVATION_TOKEN, token)

    @staticmethod
    def create_software_data(software):
        return Attribute.__create_attr_data(Attribute.SOFTWARE, software)


class Message():
    __HEADER_LEN = 20
    MAGIC = 0x2112A442  # 32bit
    TID_LEN = 12

    __ATTR_HEADER_LEN = 4

    class Cls():
        REQUEST = 0
        INDICATION = 1
        RESPONSE_SUCCESS = 2
        RESPONSE_ERROR = 3

    class Method():
        BINDING = 0x0001

        # INFO: TURN methods.
        ALLOCATE = 0x0003
        REFRESH = 0x0004
        SEND = 0x0006
        DATA = 0x0007
        CREATE_PERMISSION = 0x0008
        CHANNEL_BIND = 0x0009

        @staticmethod
        def int2str(method):
            return {
                Message.Method.BINDING: 'BINDING',
                Message.Method.ALLOCATE: 'ALLOCATE',
                Message.Method.REFRESH: 'REFRESH',
                Message.Method.SEND: 'SEND',
                Message.Method.DATA: 'DATA',
                Message.Method.CREATE_PERMISSION: 'CREATE_PERMISSION',
                Message.Method.CHANNEL_BIND: 'CHANNEL_BIND',
            }.get(method, 'UNKNOWN_METHOD')

    class ECode():
        TRY_ALTERNATE = 300
        BAD_REQUEST = 400
        UNAUTHORIZED = 401
        UNKNOWN_ATTRIBUTES = 420
        STALE_NONCE = 438
        SERVER_ERROR = 500

        # INFO: For TURN.
        FORBIDDEN = 403
        ALLOCATION_MISMATCH = 437
        WRONG_CREDENTIALS = 441
        UNSUPPORTED_TRANSPORT_PROTOCOL = 442
        ALLOCATION_QUOTA_REACHED = 486
        INSUFFICIENT_CAPACITY = 508

    def __init__(self, data):
        self.data = data
        # Make sure message is valid format and has not unknown-required-attributes.
        self.is_valid = False
        self.cls = Message.Cls.INDICATION

        data_len = len(data)
        if data_len < Message.__HEADER_LEN or data_len & 0b11:  # MUST 4-bytes-alignment.
            log.e('MSG: Data length is invalid: %X.' % data_len)
            return

        # Parse header.
        suffix, length, magic, tid = struct.unpack('!HHI%ds' % Message.TID_LEN, data[:Message.__HEADER_LEN])
        left, cls, method = self.__parse_suffix(suffix)
        if left != 0:
            log.e('MSG: Suffix is invalid: %X.' % suffix)
            return
        if length + Message.__HEADER_LEN != data_len:
            log.e('MSG: length is invalid: %d, %d' % (length + Message.__HEADER_LEN, data_len))
            return
        if magic != Message.MAGIC:
            log.e('MSG: magic is invalid: %d, %d' % (magic, Message.MAGIC))
            return

        # # This agent is STUN server.
        # if cls != Message.Cls.REQUEST \
        #         and cls != Message.Cls.INDICATION:
        #     return

        self.cls = cls
        self.method = method
        self.tid = tid

        # Parse properties.
        self.attributes = {}
        self.unknown_required_attribute = {}
        if data_len > Message.__HEADER_LEN:
            succeeded, self.attributes, self.unknown_required_attribute \
                = self.__parse_attributes(self.tid, data[Message.__HEADER_LEN:])
            if not succeeded:
                return

        if Attribute.FINGERPRINT in self.attributes.keys() \
            and Attribute.MESSAGE_INTEGRITY in self.attributes.keys():
            hash_data = self.attributes[Attribute.MESSAGE_INTEGRITY].body['hash-data']
            hash_data_len = self.__get_length(hash_data)
            hash_data_len -= 8
            self.attributes[Attribute.MESSAGE_INTEGRITY].body['hash-data'] = self.__set_length(hash_data, hash_data_len)

        self.is_valid = True

    def __parse_suffix(self, value):
        """ unsigned int (2 bytes) -> left, cls, method
        """
        left = value >> 14
        cls = ((value & 0x100) >> 7) + ((value & 0x10) >> 4)
        method = ((value & 0x3E00) >> 2) + ((value & 0xE0) >> 1) + (value & 0xF)
        return left, cls, method

    def __parse_attributes(self, tid, attr_data):
        """ attr_data -> attributes, None means failed.
        """
        remain = attr_data
        attributes = {}
        unknown_required_attributes = {}
        while remain:
            attr = Attribute(self, remain)
            if not attr.is_valid:
                return False, attributes, unknown_required_attributes

            temp_attrs = attributes
            if not attr.is_supported:
                if attr.is_required:
                    log.e('MSG: Attr is not supported but required: %X.' % attr.type)
                    return False, attributes, unknown_required_attributes
                else:
                    temp_attrs = unknown_required_attributes

            # INFO: Some attributes may be many.
            if attr.type == Attribute.XOR_PEER_ADDRESS \
                    and attr.type in temp_attrs.keys():
                temp_attrs[attr.type].append(attr)
            else:
                if not attr.type in temp_attrs.keys():
                    temp_attrs[attr.type] = attr

            remain = remain[attr.length_with_padding:]
        return True, attributes, unknown_required_attributes

    @staticmethod
    def __create_msg(cls, tid, method=Method.BINDING, attr_datas=None):
        """ Create STUN message data for communication.
        :param cls: Message.Cls
        :param method, Message.Method
        :attr_datas: attribute data list
        """
        cls_value = cls & 0b11
        method_value = method & 0xFFF
        suffix = ((cls_value & 0b10) << 7) + ((cls_value & 0b1) << 4) \
            + ((method_value & 0b111110000000) << 2) \
            + ((method_value & 0b000001110000) << 1) \
            + (method_value & 0b000000001111)
        fmt = '!HHI%ds' % Message.TID_LEN
        length = 0
        if not attr_datas:
            return struct.pack(fmt, suffix, length, Message.MAGIC, tid)

        for a in attr_datas:
            l = len(a)
            fmt += '%ds' % l
            length += l
        return struct.pack(fmt, suffix, length, Message.MAGIC, tid, *attr_datas)

    @staticmethod
    def create_error_response(tid, err_attr, additional_attrs=None):
        """
        :param err_attr: ERROR-CODE attribute data.
        :additional_attrs: list for other attribute datas.
        """
        if additional_attrs is None:
            additional_attrs = []
        attr_datas = [err_attr]
        attr_datas.extend(additional_attrs)
        return Message.__create_msg(Message.Cls.RESPONSE_ERROR, tid, attr_datas=attr_datas)

    @staticmethod
    def create_success_response(tid, attrs=None):
        if attrs is None:
            attrs = []
        return Message.__create_msg(Message.Cls.RESPONSE_SUCCESS, tid, attr_datas=attrs)

    @staticmethod
    def create_request_binding(tid):
        return Message.__create_msg(Message.Cls.REQUEST, tid)

    # For TURN

    @staticmethod
    def __get_length(msg_data):
        _, length = struct.unpack('!HH', msg_data[:4])
        return length

    @staticmethod
    def __set_length(msg_data, length):
        return msg_data[:2] + struct.pack('!H', length) + msg_data[4:]

    @staticmethod
    def __create_turn_msg(cls, method, tid, attr_datas, **kwargs):
        """ Add the MESSAGE-INTEGRITY and the FINGERPRINT attributes at the end.
        """
        has_software = kwargs.get('has_software', True)
        has_message_integrity = kwargs.get('has_message_integrity', True)
        if has_software:
            attr_datas.append(Attribute.create_software_data(SOFTWARE))
        data = Message.__create_msg(cls, tid, method, attr_datas=attr_datas)
        length = Message.__get_length(data)
        if has_message_integrity:
            length += 24
        data = Message.__set_length(data, length)
        if has_message_integrity:
            data += Attribute.create_message_integrity_data(data)
        length += 8
        data = Message.__set_length(data, length)
        data += Attribute.create_fingerprint_data(data)
        return data

    @staticmethod
    def create_error_response_turn(method, tid, err_attr,
                                   additional_attrs=None,
                                   has_message_integrity=True):
        # default is for normal error response.
        if additional_attrs is None:
            additional_attrs = []
        attr_datas = [err_attr]
        attr_datas.extend(additional_attrs)
        return Message.__create_turn_msg(
            Message.Cls.RESPONSE_ERROR, method, tid, attr_datas,
            has_message_integrity=has_message_integrity)

    @staticmethod
    def create_success_response_allocate(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.RESPONSE_SUCCESS, Message.Method.ALLOCATE, tid, attr_datas)

    @staticmethod
    def create_success_response_refresh(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.RESPONSE_SUCCESS, Message.Method.REFRESH, tid, attr_datas)

    @staticmethod
    def create_success_response_create_permission(tid):
        return Message.__create_turn_msg(
            Message.Cls.RESPONSE_SUCCESS, Message.Method.CREATE_PERMISSION, tid, [])

    @staticmethod
    def create_success_response_channel_bind(tid):
        return Message.__create_turn_msg(
            Message.Cls.RESPONSE_SUCCESS, Message.Method.CHANNEL_BIND, tid, [])

    @staticmethod
    def create_indication_data(tid, attr_datas):
        return Message.__create_msg(
            Message.Cls.INDICATION, tid, method=Message.Method.DATA, attr_datas=attr_datas)

    # For client.

    @staticmethod
    def create_request(tid, attr_datas=None):
        if attr_datas is None:
            attr_datas = []
        return Message.__create_msg(Message.Cls.REQUEST, tid, Message.Method.ALLOCATE, attr_datas)

    @staticmethod
    def create_request_allocate(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.ALLOCATE, tid, attr_datas,
            has_software=False)

    @staticmethod
    def create_request_allocate_without_message_integrity(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.ALLOCATE, tid, attr_datas,
            has_message_integrity=False, has_software=False)

    @staticmethod
    def create_request_refresh(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.REFRESH, tid, attr_datas,
            has_software=False)

    @staticmethod
    def create_request_refresh_without_message_integrity(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.REFRESH, tid, attr_datas,
            has_message_integrity=False, has_software=False)

    @staticmethod
    def create_indication_send(tid, attr_datas):
        return Message.__create_msg(
            Message.Cls.INDICATION, tid, method=Message.Method.SEND, attr_datas=attr_datas)

    @staticmethod
    def create_request_create_permission(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.CREATE_PERMISSION, tid, attr_datas,
            has_software=False)

    @staticmethod
    def create_request_create_permission_without_message_integrity(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.CREATE_PERMISSION, tid, attr_datas,
            has_message_integrity=False, has_software=False)

    @staticmethod
    def create_request_channel_bind(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.CHANNEL_BIND, tid, attr_datas,
            has_software=False)

    @staticmethod
    def create_request_channel_bind_without_message_integrity(tid, attr_datas):
        return Message.__create_turn_msg(
            Message.Cls.REQUEST, Message.Method.CHANNEL_BIND, tid, attr_datas,
            has_message_integrity=False, has_software=False)


class ChannelDataMessage():
    __HEADER_LEN = 4

    def __init__(self, data):
        self.data = data
        self.is_valid = False

        if not ChannelDataMessage.is_could_be(data):
            log.e('CMSG: Not a channel message.')
            return

        data_len = len(data)
        # INFO: Zero body length is valid.
        if data_len < ChannelDataMessage.__HEADER_LEN:
            log.e('CMSG: Data length is less than %d.' % ChannelDataMessage.__HEADER_LEN)
            return

        remain = data[ChannelDataMessage.__HEADER_LEN:]

        number, body_len = struct.unpack('!HH', data[:ChannelDataMessage.__HEADER_LEN])
        # INFO: Body may be with padding bytes.
        if body_len != len(remain):
            body_len_with_padding = body_len if body_len & 0b11 == 0 else (body_len + 4) & 0xFFFC
            if body_len_with_padding != len(remain):
                log.e('CMSG: Body length is not equal real lenght, %d, %d.'
                      % (body_len, len(self.body)))
                return

        self.number = number
        self.body_len = body_len
        self.body = data[ChannelDataMessage.__HEADER_LEN: ChannelDataMessage.__HEADER_LEN + body_len]
        self.is_valid = True

    @staticmethod
    def is_could_be(data):
        if len(data) > 1:
            suffix = struct.unpack('B', data[0])[0]
            return (suffix & 0xC0) >> 6 == MESSAGE_MAGIC_CHANNEL
        return False

    @staticmethod
    def create_data(number, data):
        pdata = utils.get_padding_data(data)
        fmt = '!HH%ds%ds' % (len(data), len(pdata))
        return struct.pack(fmt, number, len(data), data, pdata)


class FiveTuple():
    def __init__(self, client_addr, protocol, server_addr):
        self.client_addr = client_addr
        self.protocal = protocol
        self.server_addr = server_addr

    def __eq__(self, other):
        return other.client_addr == self.client_addr \
            and other.protocal == self.protocal \
            and other.server_addr == self.server_addr


class Allocation(ExpiredObj):
    def __init__(self, server, tid, five_tuple, nonce, is_dont_fragment, time_to_expiry):
        ExpiredObj.__init__(self, time_to_expiry)
        self.server = server
        # TODO: Invalid after 30 seconds.
        self.tid = tid  # For repeated allocate.
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.relayed_transport_address = server.bind_next(self.sock)
        if not self.relayed_transport_address:
            self.sock.close()
            raise TurnError('Socket binding failed.')
        self.five_tuple = five_tuple
        self.nonce = nonce
        self.is_dont_fragment = is_dont_fragment
        self.__permissions = []
        self.__channels = []
        # To test if no data transport between client and peer.
        self.data_trans_tracer = ExpiredObj(TIME_TO_EXPIRE_ALLOCATION_DATA_TRANS)

    @property
    def permissions(self):
        return self.__permissions

    def add_permission(self, ip):
        """ Add permission by int ip, refresh if exists.
        :param ip: int
        """
        new_p = Permission(ip, TIME_TO_EXPIRY_PERMISSION)
        for p in self.__permissions:
            if p == new_p:
                p.refresh()
                return
        self.__permissions.append(new_p)

    def has_permission(self, ip):
        return Permission(ip, TIME_TO_EXPIRY_PERMISSION) in self.__permissions

    @property
    def channels(self):
        return self.__channels

    def get_channel(self, number, addr):
        for ch in self.__channels:
            if ch.number == number and ch.peer_addr == addr:
                return ch
        return None

    def get_channel_by_number(self, number):
        for ch in self.__channels:
            if ch.number == number:
                return ch
        return None

    def get_channel_by_addr(self, addr):
        for ch in self.__channels:
            if ch.peer_addr == addr:
                return ch
        return None

    def add_channel(self, number, addr):
        """ number and addr MUST be valid.
        """
        self.add_permission(addr[0])
        new_ch = Channel(number, addr, TIME_TO_EXPIRY_CHANNEL)
        for ch in self.__channels:
            if ch == new_ch:
                ch.refresh()
                return
        self.__channels.append(new_ch)


class Permission(ExpiredObj):
    def __init__(self, ip, time_to_expiry):
        ExpiredObj.__init__(self, time_to_expiry)
        self.ip = ip

    def __eq__(self, other):
        return other.ip == self.ip


class Channel(ExpiredObj):
    def __init__(self, number, peer_addr, time_to_expiry):
        ExpiredObj.__init__(self, time_to_expiry)
        self.number = number
        self.peer_addr = peer_addr

    def __eq__(self, other):
        return other.number == self.number and other.peer_addr == self.peer_addr


class AllocationManager(object):
    __allocations = []

    __instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super(AllocationManager, cls).__new__(cls, *args, **kwargs)
        return cls.__instance

    def get(self, five_tuple):
        for allocation in self.__allocations:
            if allocation.five_tuple == five_tuple:
                return allocation
        return None

    @property
    def allocations(self):
        return self.__allocations

    def get_by_sock(self, sock):
        for allocation in self.__allocations:
            if sock is allocation.sock:
                return allocation
        return None

    def get_all_socks(self):
        return map(lambda x: x.sock, self.__allocations)

    def remove(self, five_tuple):
        """ Return False means allocation does not exist.
        """
        for allocation in self.__allocations[:]:
            if allocation.five_tuple == five_tuple:
                self.__allocations.remove(allocation)
                return True
        return False

    def add(self, allocation):
        self.__allocations.append(allocation)

    def refresh(self):
        for a in self.__allocations[:]:
            a.update()
            if a.is_expired:
                self.__allocations.remove(a)
                continue
            # No data transport between peer and client.
            if a.data_trans_tracer.update():
                self.__allocations.remove(a)
                continue
            for p in a.permissions[:]:
                p.update()
                if p.is_expired:
                    a.permissions.remove(p)
            for c in a.channels[:]:
                c.update()
                if c.is_expired:
                    a.channels.remove(c)


# singleton
class MessageHandler():
    __instance = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = MessageHandler.__new__(cls, *args, **kwargs)
        return cls.__instance

    def __init__(self, server):
        self.server = server
        self.trans = {}

    def process(self, sock, addr, msg):
        # TODO: Skip first indication message.
        if msg.cls == Message.Cls.REQUEST:
            self.__process_request(sock, addr, msg)
        elif msg.cls == Message.Cls.INDICATION:
            self.__process_indication(sock, addr, msg)

    def __process_request(self, sock, addr, msg):
        log.v('[MSG HANDLER] Process request with method: %s' % Message.Method.int2str(msg.method))
        if msg.method == Message.Method.BINDING:
            self.__process_request_binding(sock, addr, msg)
        elif msg.method == Message.Method.ALLOCATE:
            self.__process_request_allocate(sock, addr, msg)
        elif msg.method == Message.Method.REFRESH:
            self.__process_request_refresh(sock, addr, msg)
        elif msg.method == Message.Method.CREATE_PERMISSION:
            self.__process_request_create_permission(sock, addr, msg)
        elif msg.method == Message.Method.CHANNEL_BIND:
            self.__process_request_channel_bind(sock, addr, msg)
        else:
            log.v('Unsupported method while process STUN request message.')

    def __process_indication(self, sock, addr, msg):
        log.v('[MSG HANDLER] Process indication with method: %s' % Message.Method.int2str(msg.method))
        if msg.method == Message.Method.SEND:
            self.__process_indication_send(sock, addr, msg)
        else:
            log.v('Unsupported method while process STUN indication message.')

    def __process_request_binding(self, sock, addr, msg):
        ip, port = addr
        if utils.is_valid_ipv6(ip):
            family = Family.IPV6
        else:
            family = Family.IPV4
        xor_attr = Attribute.create_xor_mapped_address_data(msg.tid, family, port, ip)
        log.v('Send response with xor-mapped-address to client.')
        sock.sendto(Message.create_success_response(msg.tid, [xor_attr]), utils.addr2str(addr))
        log.v('[BINDING] OK.')

    def __verify_auth(self, sock, addr, msg, method):
        """ If failed, return False.
        -> True, False, None(waiting rm_connector ack)
        """
        attrs = msg.attributes.keys()
        if not Attribute.MESSAGE_INTEGRITY in attrs:
            # INFO: RFC 5389/10.2.2
            log.e('[%s] Not found MESSAGE_INTEGRITY attribute.' % Message.Method.int2str(method))
            self.__send_error_response(sock, addr, msg, method, Message.ECode.UNAUTHORIZED,
                                       has_realm_nonce=True, has_message_integrity=False)
            return False
        if not set([Attribute.USERNAME, Attribute.NONCE, Attribute.REALM]).issubset(attrs):
            log.e('[%s] Not found USERNAME, NONCE and REALM attribute.' % Message.Method.int2str(method))
            self.__send_error_response(sock, addr, msg, method, Message.ECode.BAD_REQUEST,
                                       has_message_integrity=False)
            return False
        if msg.attributes[Attribute.NONCE].body['nonce'] != self.server.nonce:
            nonce_attr = Attribute.create_nonce_data(self.server.nonce)
            realm_attr = Attribute.create_realm_data(REALM)
            self.__send_error_response(sock, addr, msg, method,
                Message.ECode.STALE_NONCE, additional_attr_datas=[nonce_attr, realm_attr],
                has_realm_nonce=True, has_message_integrity=False)
            log.e('[%s] Nonce is invalid.' % Message.Method.int2str(method))
            return False
        if msg.attributes[Attribute.USERNAME].body['username'] != USERNAME:
            log.e('[%s] Username is invalid.' % Message.Method.int2str(method))
            self.__send_error_response(sock, addr, msg, method, Message.ECode.UNAUTHORIZED,
                                       has_realm_nonce=True, has_message_integrity=False)
            return False

        username = msg.attributes[Attribute.USERNAME].body['username']
        udp_data = VerifyTokenData(sock, addr, msg, method)
        device_token = self.server.rm_connector.\
            verify_token_for_udp(self.server, username, udp_data)
        if device_token is None:
            return None

        if not self.__verify_auth_by_device_token(msg, device_token):
            log.e('[%s] Token for %s username is invalid in __verify_auth().'
                  % (Message.Method.int2str(method), str(username)))
            self.__send_error_response(sock, addr, msg, method, Message.ECode.UNAUTHORIZED,
                                       has_realm_nonce=True, has_message_integrity=False)
            return False

        return True

    def __verify_auth_by_device_token(self, msg, device_token):
        """
        :param msg: VerifyTokenData
        :param device_token: DeviceToken from rm connector.
        :return: is_authed.
        """
        hmac = Attribute.get_hmac_sha1(msg.attributes[Attribute.MESSAGE_INTEGRITY].body['hash-data'],
                                       username=msg.attributes[Attribute.USERNAME].body['username'],
                                       password=device_token.token,
                                       realm=msg.attributes[Attribute.REALM].body['realm'])
        return hmac == msg.attributes[Attribute.MESSAGE_INTEGRITY].body['data']

    def __send_error_response(self, sock, addr, msg, method, ecode,
                              additional_attr_datas=None,
                              has_realm_nonce=False,
                              has_message_integrity=True):
        # Default is for normal response.
        if additional_attr_datas is None:
            additional_attr_datas = []
        err_attr = Attribute.create_error_code_data(ecode)
        if has_realm_nonce:
            additional_attr_datas.append(Attribute.create_realm_data(REALM))
            additional_attr_datas.append(Attribute.create_nonce_data(self.server.nonce))
        sock.sendto(Message.create_error_response_turn(method, msg.tid, err_attr, additional_attr_datas,
                                                       has_message_integrity=has_message_integrity),
                    utils.addr2str(addr))

    def __process_request_allocate(self, sock, addr, msg, is_skip_auth=False):
        attrs = msg.attributes.keys()
        if not is_skip_auth:
            res = self.__verify_auth(sock, addr, msg, Message.Method.ALLOCATE)
            if res is None:  # Handle next time.
                return
        allocation = self.__get_allocation(addr)
        # INFO: Allocate may be retransmitted.
        if allocation and allocation.tid != msg.tid:
            log.e('[ALLOCATE] Allocation exists with different tid.')
            self.__send_error_response(
                sock, addr, msg, Message.Method.ALLOCATE, Message.ECode.ALLOCATION_MISMATCH)
            return
        if not allocation:
            if not Attribute.REQUESTED_TRANSPORT in attrs:
                log.e('[ALLOCATE] No REQUESTED_TRANSPORT.')
                self.__send_error_response(
                    sock, addr, msg, Message.Method.ALLOCATE, Message.ECode.BAD_REQUEST)
                return
            if msg.attributes[Attribute.REQUESTED_TRANSPORT].body['protocol'] != Protocol.UDP:
                log.e('[ALLOCATE] Only support UDP protocol.')
                self.__send_error_response(
                    sock, addr, msg, Message.Method.ALLOCATE, Message.ECode.UNSUPPORTED_TRANSPORT_PROTOCOL)
                return
            is_dont_fragment = False
            if Attribute.RESERVATION_TOKEN in attrs:
                if Attribute.EVEN_PORT in attrs:
                    self.__send_error_response(
                        sock, addr, msg, Message.Method.ALLOCATE, Message.ECode.BAD_REQUEST)
                    log.e('[ALLOCATE] EVEN_PORT can not with RESERVATION_TOKEN.')
                    return
                # TODO: token.
            if Attribute.EVEN_PORT in attrs:
                log.e('[ALLOCATE] EVEN_PORT is not supported.')
                self.__send_error_response(
                    sock, addr, msg, Message.Method.ALLOCATE, Message.ECode.INSUFFICIENT_CAPACITY)
                return
            if len(AllocationManager().allocations) >= CAPCITY_MAX_ALLOCATION:
                log.e('[ALLOCATE] Can not make more allocations.')
                self.__send_error_response(
                    sock, addr, msg, Message.Method.ALLOCATE, Message.ECode.ALLOCATION_QUOTA_REACHED)
                return
            if Attribute.DONT_FRAGMENT in attrs:
                is_dont_fragment = True
            try:
                time_to_expiry = TIME_TO_EXPIRY_ALLOCATION_DEFAULT
                if Attribute.LIFETIME in attrs:
                    if TIME_TO_EXPIRY_ALLOCATION_MAX \
                            >= msg.attributes[Attribute.LIFETIME].body['lifetime'] \
                            > TIME_TO_EXPIRY_ALLOCATION_DEFAULT:
                        time_to_expiry = msg.attributes[Attribute.LIFETIME].body['lifetime']
                nonce = msg.attributes[Attribute.NONCE].body['nonce']
                five_tuple = FiveTuple(addr, Protocol.UDP, self.server.address)
                allocation = Allocation(self.server, msg.tid, five_tuple, nonce,
                                        is_dont_fragment, time_to_expiry)
                AllocationManager().add(allocation)
            except TurnError as e:
                log.e('[ALLOCATE] Create allocation failed: %s' % str(e))
                self.__send_error_response(
                    sock, addr, msg, Message.Method.ALLOCATE, Message.ECode.INSUFFICIENT_CAPACITY)
                return
        else:
            allocation.update()
        # TODO: RESERVATION-TOKEN.
        attr_datas = []
        attr_datas.append(Attribute.create_xor_relayed_address_data(
            msg.tid, Family.IPV4, allocation.relayed_transport_address[1],
            utils.ip2int(allocation.relayed_transport_address[0])))
        attr_datas.append(Attribute.create_lifetime_data(allocation.time_to_expiry))
        attr_datas.append(Attribute.create_xor_mapped_address_data(
            msg.tid, Family.IPV4, addr[1], addr[0]))
        data = Message.create_success_response_allocate(msg.tid, attr_datas)
        sock.sendto(data, utils.addr2str(addr))
        log.v('[ALLOCATE] OK.')

    def __process_request_refresh(self, sock, addr, msg, is_skip_auth=False):
        if not is_skip_auth:
            res = self.__verify_auth(sock, addr, msg, Message.Method.REFRESH)
            if res is None:  # Handle next time.
                return
        desired_lifetime = TIME_TO_EXPIRY_ALLOCATION_DEFAULT
        if Attribute.LIFETIME in msg.attributes.keys():
            lifetime = msg.attributes[Attribute.LIFETIME].body['lifetime']
            if lifetime == 0:
                desired_lifetime = 0
            elif TIME_TO_EXPIRY_ALLOCATION_DEFAULT < lifetime <= TIME_TO_EXPIRY_ALLOCATION_MAX:
                desired_lifetime = lifetime
        allocation = self.__get_allocation(addr)
        if not allocation:
            log.e('[REFRESH] No allocation exists.')
            self.__send_error_response(
                sock, addr, msg, Message.Method.REFRESH, Message.ECode.ALLOCATION_MISMATCH)
            return
        if desired_lifetime == 0:
            five_tuple = FiveTuple(addr, Protocol.UDP, self.server.address)
            AllocationManager().remove(five_tuple)
        else:
            allocation.time_to_expiry = desired_lifetime
        allocation.refresh_to(desired_lifetime)
        attr_datas = [Attribute.create_lifetime_data(desired_lifetime)]
        sock.sendto(Message.create_success_response_refresh(msg.tid, attr_datas), utils.addr2str(addr))
        log.v('[REFRESH] OK.')

    def __process_request_create_permission(self, sock, addr, msg, is_skip_auth=False):
        if not is_skip_auth:
            res = self.__verify_auth(sock, addr, msg, Message.Method.CREATE_PERMISSION)
            if res is None:  # Handle next time.
                return
        if not Attribute.XOR_PEER_ADDRESS in msg.attributes.keys():
            log.e('[CREATE_PERMISSION] No XOR_PEER_ADDRESS.')
            self.__send_error_response(
                sock, addr, msg, Message.Method.CREATE_PERMISSION, Message.ECode.BAD_REQUEST)
            return
        # TODO: 403 ( restrictions on ip )
        allocation = self.__get_allocation(addr)
        if not allocation:
            log.e('[CREATE_PERMISSION] No allocation.')
            # INFO: RFC5766/4
            self.__send_error_response(
                sock, addr, msg, Message.Method.CREATE_PERMISSION, Message.ECode.ALLOCATION_MISMATCH)
            return
        count = 0
        peer_attrs = msg.attributes[Attribute.XOR_PEER_ADDRESS].get_all()
        for attr in peer_attrs:
            if not allocation.has_permission(attr.body['ip']):
                count += 1
        if len(allocation.permissions) + count > CAPCITY_MAX_PERMISSION:
            log.e('[CREATE_PERMISSION] To many permissions.')
            self.__send_error_response(
                sock, addr, msg, Message.Method.CREATE_PERMISSION, Message.ECode.INSUFFICIENT_CAPACITY)
            return
        for attr in peer_attrs:
            allocation.add_permission(attr.body['ip'])
        sock.sendto(Message.create_success_response_create_permission(msg.tid), utils.addr2str(addr))
        log.v('[CREATE_PERMISSION] OK.')

    def __process_request_channel_bind(self, sock, addr, msg, is_skip_auth=False):
        if not is_skip_auth:
            res = self.__verify_auth(sock, addr, msg, Message.Method.CHANNEL_BIND)
            if res is None:  # Handle next time.
                return
        if not set([Attribute.XOR_PEER_ADDRESS, Attribute.CHANNEL_NUMBER]).issubset(msg.attributes.keys()):
            log.e('[CHANNEL_BIND] No XOR_PEER_ADDRESS or CHANNEL_NUMBER.')
            self.__send_error_response(
                sock, addr, msg, Message.Method.CHANNEL_BIND, Message.ECode.BAD_REQUEST)
            return
        if not 0x4000 <= msg.attributes[Attribute.CHANNEL_NUMBER].body['number'] <= 0x7FFE:
            log.e('[CHANNEL_BIND] Invalid CHANNEL_NUMBER.')
            self.__send_error_response(
                sock, addr, msg, Message.Method.CHANNEL_BIND, Message.ECode.BAD_REQUEST)
            return
        allocation = self.__get_allocation(addr)
        if not allocation:
            log.e('[CHANNEL_BIND] No allocation.')
            # INFO: RFC5766/4
            self.__send_error_response(
                sock, addr, msg, Message.Method.CHANNEL_BIND, Message.ECode.ALLOCATION_MISMATCH)
            return
        number = msg.attributes[Attribute.CHANNEL_NUMBER].body['number']
        peer_addr = msg.attributes[Attribute.XOR_PEER_ADDRESS].body['addr']
        channel = allocation.get_channel(number, peer_addr)
        if not channel:
            ch_by_n = allocation.get_channel_by_number(number)
            ch_by_a = allocation.get_channel_by_addr(peer_addr)
            if ch_by_n or ch_by_a:
                log.e('[CHANNEL_BIND] Channel by number exists with different peer address.')
                self.__send_error_response(
                    sock, addr, msg, Message.Method.CHANNEL_BIND, Message.ECode.BAD_REQUEST)
                return
        # TODO: Impose restriction on the ip. ( 403 )
        if (not allocation.has_permission(peer_addr[0]) \
                and len(allocation.permissions) >= CAPCITY_MAX_PERMISSION)\
                or (not channel and len(allocation.channels) >= CAPCITY_MAX_ALLOCATION):
            log.e('[CHANNEL_BIND] To many permissions or channels.')
            self.__send_error_response(
                sock, addr, msg, Message.Method.CHANNEL_BIND, Message.ECode.INSUFFICIENT_CAPACITY)
            return
        allocation.add_channel(msg.attributes[Attribute.CHANNEL_NUMBER].body['number'], peer_addr)
        sock.sendto(Message.create_success_response_channel_bind(msg.tid), utils.addr2str(addr))
        log.v('[CHANNEL_BIND] OK.')

    def __sendto_peer(self, allocation, addr, data, is_df=False):
        IP_MTU_DISCOVER   = 10
        IP_PMTUDISC_DONT  =  0  # Never send DF frames.
        IP_PMTUDISC_WANT  =  1  # Use per route hints.
        IP_PMTUDISC_DO    =  2  # Always DF.
        IP_PMTUDISC_PROBE =  3  # Ignore dst pmtu.
        allocation.sock.setsockopt(socket.SOL_IP, IP_MTU_DISCOVER,
                                   IP_PMTUDISC_DONT if is_df else IP_PMTUDISC_DO)
        allocation.sock.sendto(data, utils.addr2str(addr))

    def __process_indication_send(self, sock, addr, msg):
        if not set([Attribute.XOR_PEER_ADDRESS, Attribute.DATA]).issubset(msg.attributes.keys()):
            log.e('[SEND] no XOR_PEER_ADDRESS or DATA attribute.')
            return
        is_df = False
        if Attribute.DONT_FRAGMENT in msg.attributes.keys():
            is_df = True
        allocation = self.__get_allocation(addr)
        if not allocation:
            log.e('[SEND] no allocation exists.')
            return
        allocation.data_trans_tracer.refresh()
        self.__sendto_peer(allocation,
                           utils.addr2str(msg.attributes[Attribute.XOR_PEER_ADDRESS].body['addr']),
                           msg.attributes[Attribute.DATA].body['data'],
                           is_df)
        log.v('[SEND] OK.')

    def __get_allocation(self, addr):
        five_tuple = FiveTuple(addr, Protocol.UDP, self.server.address)
        return AllocationManager().get(five_tuple)

    def process_channel_msg(self, sock, addr, msg):
        log.v('[MSG HANDLER] Process channel data message from client.')
        allocation = self.__get_allocation(addr)
        if not allocation:
            log.e('[CHANNEL MSG] No allocation.')
            return
        channel = allocation.get_channel_by_number(msg.number)
        if not channel:
            log.e('[CHANNEL MSG] No channel.')
            return
        if not allocation.has_permission(channel.peer_addr[0]):
            log.e('[CHANNEL MSG] No permission.')
            return
        allocation.data_trans_tracer.refresh()
        allocation.sock.sendto(msg.body, utils.addr2str(channel.peer_addr))
        log.v('[CHANNEL MSG] OK.')

    def process_verify_token_ack(self, sock, addr, msg, method, device_token):
        if not self.__verify_auth_by_device_token(msg, device_token):
            log.e('[CHANNEL MSG] Token is invalid in process_verify_token_ack().')
            self.__send_error_response(sock, addr, msg, method, Message.ECode.UNAUTHORIZED,
                                       has_realm_nonce=True, has_message_integrity=False)
            return

        if method == Message.Method.ALLOCATE:
            self.__process_request_allocate(sock, addr, msg, True)
        elif method == Message.Method.REFRESH:
            self.__process_request_refresh(sock, addr, msg, True)
        elif method == Message.Method.CREATE_PERMISSION:
            self.__process_request_create_permission(sock, addr, msg, True)
        elif method == Message.Method.CHANNEL_BIND:
            self.__process_request_channel_bind(sock, addr, msg, True)
        else:
            log.e('[CHANNEL MSG] Unknown method in process_verify_token_ack.')


class StunServer():
    BASE_PEER_PORT = 50000
    MAX_PEER_PORT = 60000

    class Message():
        def __init__(self, udp_data, device_token):
            self.udp_data = udp_data
            self.device_token = device_token

    def __init__(self):
        """
        :param addr: The ip is string.
        """
        self.__s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__next_port = StunServer.BASE_PEER_PORT
        self.__nonce_timer = ExpiredObj(2 * 60 * 60)
        self.__nonce = str(uuid.uuid1())

        # Support verify-token.

        self.__msg_queue = Queue.Queue()

        self.is_quit = False

    def attach_rm_connector(self, rm_connector):
        """ Attach rm connector when add to rm connector.
        MUST call before self.start().
        """
        self.rm_connector = rm_connector
        self.upnp = rm_connector.upnp
        self.hub = rm_connector.hub
        self.upnp.udp_port = self.hub.bind_socket_to_port(self.__s, self.upnp.address, self.upnp.udp_port)
        self.address = utils.addr2int((self.upnp.address, self.upnp.udp_port))

    def start(self):
        log.d('STUN server started: %s' % str(utils.addr2str(self.address)))
        while not self.is_quit:
            reads = [self.__s]
            reads.extend(AllocationManager().get_all_socks())
            reads_res, _, _ = select.select(reads, [], [], 1)
            self.__refresh()
            self.__handle_ack_msg()
            peers = AllocationManager().get_all_socks()
            for s in reads_res:
                try:
                    if s is self.__s:
                        self.__handle_server_sock(s)
                    elif s in peers:
                        self.__handle_peer_sock(s)
                    else:
                        log.v('Skip socket.')
                except socket.error as e:
                    log.e('%s socket error: %s' % ('Client' if s is self.__s else 'Peer', str(e)))

    def stop(self):
        self.is_quit = True

    def __refresh(self):
        self.__update_nonce()
        AllocationManager().refresh()

    def __handle_server_sock(self, s):
        data, addr = s.recvfrom(config.SOCKET_RECV_LEN)
        log.v('Get a message.')
        if ChannelDataMessage.is_could_be(data):
            msg = ChannelDataMessage(data)
            if not msg.is_valid:
                log.e('Message from peer is invalid.')
                return
            MessageHandler(self).process_channel_msg(s, utils.addr2int(addr), msg)
            return
        msg = Message(data)
        if not msg.is_valid:
            if msg.cls == Message.Cls.REQUEST:
                err_data = Attribute.create_error_code_data(Message.ECode.BAD_REQUEST)
                s.sendto(Message.create_error_response(msg.tid, err_data), addr)
            log.e('Message is invalid.')
            return
        if msg.unknown_required_attribute:
            attrs_data = Attribute.create_unknown_attributes_data(
                msg.unknown_required_attribute)
            err_data = Attribute.create_error_code_data(Message.ECode.UNKNOWN_ATTRIBUTES, attrs_data=attrs_data)
            s.sendto(Message.create_error_response(msg.tid, err_data), addr)
            log.e('Message has unknown-required-attributes.')
            return
        log.v('Process a message by message handler.')
        MessageHandler(self).process(s, utils.addr2int(addr), msg)

    def __handle_peer_sock(self, s):
        data, addr = s.recvfrom(config.SOCKET_RECV_LEN)
        # TODO: Empty data is valid.
        if not data:
            return
        log.v('Handle peer message.')
        allocation = AllocationManager().get_by_sock(s)
        if not allocation:
            log.e('[PEER] No allocation.')
            # INFO: Allocation has been deleted.
            return
        if not allocation.has_permission(utils.ip2int(addr[0])):
            log.e('[PEER] No permission.')
            return
        allocation.data_trans_tracer.refresh()
        client_addr = utils.addr2str(allocation.five_tuple.client_addr)
        channel = allocation.get_channel_by_addr(utils.addr2int(addr))
        if channel:
            s.sendto(ChannelDataMessage.create_data(channel.number, data),
                     utils.addr2str(client_addr))
            log.v('[PEER] Relay by channel.')
            return
        xor_attr = Attribute.create_xor_peer_address_data(
            allocation.tid, Family.IPV4, addr[1], utils.ip2int(addr[0]))
        data_attr = Attribute.create_data_data(data)
        s.sendto(Message.create_indication_data(
            allocation.tid, [xor_attr, data_attr]), utils.addr2str(client_addr))
        log.v('[PEER] Relay by indication.')

    def bind_next(self, sock):
        port = 0
        count = 5
        while count > 0:
            self.__next_port += 1
            if self.__next_port >= StunServer.MAX_PEER_PORT:
                self.__next_port = StunServer.BASE_PEER_PORT
            try:
                log.v('Bind to %s' % str((utils.ip2str(self.address[0]), self.__next_port)))
                sock.bind((utils.ip2str(self.address[0]), self.__next_port))
                port = self.__next_port
                break
            except socket.error:
                log.d('Failed to bind %d, try later.' % self.__next_port)
                time.sleep(2)
                count -= 1
        if count <= 0:
            return None
        return self.address[0], port

    def post_verify_token_ack_msg(self, udp_data, return_token):
        """
        :param udp_data: VerifyTokenData
        :param return_token: proxy.DeviceToken
        :return:
        """
        msg = StunServer.Message(udp_data, return_token)
        self.__msg_queue.put_nowait(msg)

    def __handle_ack_msg(self):
        try:
            while True:
                msg = self.__msg_queue.get_nowait()
                MessageHandler(self).process_verify_token_ack(msg.udp_data.sock,
                                                              msg.udp_data.addr,
                                                              msg.udp_data.msg,
                                                              msg.udp_data.method,
                                                              msg.device_token)
        except (Queue.Empty, socket.error, socket.timeout):
            pass

    @property
    def nonce(self):
        return self.__nonce

    def __update_nonce(self):
        self.__nonce_timer.update()
        if self.__nonce_timer.is_expired:
            self.__nonce = str(uuid.uuid1())
            self.__nonce_timer.refresh()

    def is_busy(self):
        return bool(AllocationManager().allocations)


class StunServerThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.server = StunServer()

    def run(self):
        self.server.start()

    def stop(self):
        self.server.stop()

if __name__ == '__main__':
    # Can not run independently.
    # ip = socket.gethostbyname(socket.gethostname())
    ip = '127.0.0.1'
    work_thread = StunServerThread(None)
    work_thread.start()
    while True:
        print 'After start.'
        time.sleep(2)
