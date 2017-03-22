__author__ = 'Fred'

import socket
import struct
import json
from log import log


class ECode():
    BOX_CLIENT_ERROR = 0x4001
    RELAY_BOX_INVALID_INFO = 0x5001
    RELAY_TOO_MANY_CONNECTIONS = 0x5002
    RELAY_CLIENT_DISCONNECTED = 0x5003
    RELAY_FAILED_CREATE_CLIENT_PORT = 0x5004
    RELAY_CLIENT_TIMEOUT = 0x5005


class Type():
    CONNECT = 0x0001
    ACCEPT = 0x0002
    REFUSE = 0x0004
    DISCONNECT = 0x0005
    CLOSE = 0x0006
    PING = 0x0007
    PING_ACK = 0x0008
    SERVER_DATA = 0x0011
    CLIENT_DATA = 0x0012
    SERVER_ERROR = 0x0013
    CLIENT_ERROR = 0x0014
    PAUSE = 0x0022
    RESUME = 0x0024


class Message():
    """
    Before handle message, MUST make sure the message is valid.
    """
    HEADER_LEN = 8
    UUID_LEN = 8
    ECODE_LEN = 4
    MAGIC = 0x4688

    def __init__(self, data, conn=None):
        if not data:
            raise socket.error('Get the EOF message')
        self.data = data
        self.is_valid = False
        self.type = None
        # Possible value:
        #   json unpacked data.
        #   data stream.
        self.content = None
        # Error code, ing, 4 byte in data.
        self.ecode = -1
        self.message = ''
        # Client UUID, long, long, 8 byte in data
        self.uuid = -1
        if len(data) < Message.HEADER_LEN:
            return
        header, body = data[:Message.HEADER_LEN], data[Message.HEADER_LEN:]
        magic, self.type, length = struct.unpack('!HHi', header)
        if magic != Message.MAGIC or length != len(body):
            return

        # Parse message body.
        # MUST set 'self.is_valid' to True when body is valid.
        if self.type == Type.CONNECT \
                or self.type == Type.ACCEPT:
            self.is_valid = self.content = Message.get_unpacked_json_data(body)
        elif self.type == Type.REFUSE:
            self.content = Message.get_unpacked_json_data(body)
            if isinstance(self.content, dict):
                try:
                    self.ecode = int(self.content['reason'])
                    self.message = str(self.content['message'])
                    self.is_valid = True
                except:
                    log.e('The content of relay REFUSE is invalid, %s.' % str(self.content))
        elif self.type == Type.DISCONNECT \
                or self.type == Type.CLOSE \
                or self.type == Type.PING \
                or self.type == Type.PING_ACK:
            self.is_valid = len(body) == 0
        elif self.type == Type.SERVER_DATA \
                or self.type == Type.CLIENT_DATA:
            if len(body) <= Message.UUID_LEN:
                return
            uuid_data, self.content = body[:Message.UUID_LEN], body[Message.UUID_LEN:]
            self.uuid = struct.unpack('@q', uuid_data)[0]
            self.is_valid = True
        elif self.type == Type.SERVER_ERROR \
                or self.type == Type.CLIENT_ERROR:
            self.content = Message.get_unpacked_json_data(body)
            if isinstance(self.content, dict):
                try:
                    self.uuid = int(self.content['connection'])
                    self.ecode = int(self.content['error'])
                    self.is_valid = True
                except:
                    log.e('The content of relay SERVER_ERROR or CLIENT_ERROR is invalid, %s.' % str(self.content))
        elif self.type == Type.PAUSE \
                or self.type == Type.RESUME:
            self.content = Message.get_unpacked_json_data(body)
            if isinstance(self.content, dict):
                try:
                    self.uuid = int(self.content['connection'])
                    self.is_valid = True
                except:
                    log.e('The content of relay PAUSE or RESUME is invalid, %s.' % str(self.content))
        else:
            log.e('Unknown message type.')

    @staticmethod
    def get_unpacked_json_data(data):
        try:
            return json.loads(data)
        except ValueError:
            return None

    @staticmethod
    def parse_body_length(header, **kwargs):
        target_magic = kwargs.get('magic', Message.MAGIC)
        magic, _, length = struct.unpack('!HHi', header)
        return length if magic == target_magic else -1

    @staticmethod
    def create_data(msg_type, *args, **kwargs):
        """
        Create message data stream for socket transportation.
        -------------------------------------------------
        | magic | type | body_len | arg1, arg2, arg3 ... |
        -------------------------------------------------
        :param msg_type: Message type.
        :param args: The segments of string format in Payload field.
        """
        magic = kwargs.get('magic', Message.MAGIC)
        fromat_header = '!HHi'
        format_body = None
        body_len = 0
        if args:
            format_body = '@'
            for part in args:
                length = len(part)
                body_len += length
                format_body += '%ds' % length
        data = struct.pack(fromat_header, magic, msg_type, body_len)
        if format_body: data += struct.pack(format_body, *args)
        return data

    @staticmethod
    def create_connect_data(content):
        return Message.create_data(Type.CONNECT, json.dumps(content))

    @staticmethod
    def create_accept_data(content):
        return Message.create_data(Type.ACCEPT, json.dumps(content))

    @staticmethod
    def create_refuse_data(ecode, message=''):
        content = json.dumps({'reason': str(ecode), 'message': message})
        return Message.create_data(Type.REFUSE, content)

    @staticmethod
    def create_disconnect_data():
        return Message.create_data(Type.DISCONNECT)

    @staticmethod
    def create_close_data():
        return Message.create_data(Type.CLOSE)

    @staticmethod
    def create_ping_data():
        return Message.create_data(Type.PING)

    @staticmethod
    def create_ping_ack_data():
        return Message.create_data(Type.PING_ACK)

    @staticmethod
    def create_server_data_data(uuid, content):
        """
        Create server data data stream.
        :param uuid: int
        :param content: raw data for client.
        :return: data stream.
        """
        uuid_str = struct.pack('q', uuid)
        return Message.create_data(Type.SERVER_DATA, uuid_str, content)

    @staticmethod
    def create_client_data_data(uuid, content):
        uuid_str = struct.pack('q', uuid)
        return Message.create_data(Type.CLIENT_DATA, uuid_str, content)

    @staticmethod
    def create_server_error_data(uuid, ecode):
        content = json.dumps({'connection': str(uuid), 'error': str(ecode)})
        return Message.create_data(Type.SERVER_ERROR, content)

    @staticmethod
    def create_client_error_data(uuid, ecode):
        content = json.dumps({'connection': str(uuid), 'error': str(ecode)})
        return Message.create_data(Type.CLIENT_ERROR, content)

    @staticmethod
    def create_pause_data(uuid):
        content = json.dumps({'connection': str(uuid)})
        return Message.create_data(Type.PAUSE, content)

    @staticmethod
    def create_resume_data(uuid):
        content = json.dumps({'connection': str(uuid)})
        return Message.create_data(Type.RESUME, content)


class HubMessage():
    """
    Message from or to hub.
    """
    HEADER_LEN = 6
    MAGIC = 0x4688

    def __init__(self, data):
        if not data:
            raise socket.error('Get the EOF message from hub.')
        self.data = data
        self.is_valid = False
        self.content = None
        if len(data) < HubMessage.HEADER_LEN:  return
        header, body = data[:HubMessage.HEADER_LEN], data[HubMessage.HEADER_LEN:]
        magic, length = struct.unpack('!Hi', header)
        if magic != HubMessage.MAGIC or length != len(body):  return
        self.content = self._get_unpacked_json_content(body)
        self.is_valid = bool(self.content)

    def _get_unpacked_json_content(self, data):
        try:
            return json.loads(data)
        except ValueError:
            return None

    @staticmethod
    def _create_data(*args):
        """
        Create message data stream for socket transportation.
        -------------------------------------------------
        | magic | body_len | body                        |
        -------------------------------------------------
        :param args: The segments of string format in Payload field.
        """
        format = '!Hi'
        body_len = 0
        for arg in args:
            length = len(arg)
            format += '%ds' % length
            body_len += length
        return struct.pack(format, Message.MAGIC, body_len, *args)

    @staticmethod
    def create_content_data(content):
        return HubMessage._create_data(json.dumps(content))


class RelayManagerMessage():
    __HEADER_LEN = Message.HEADER_LEN
    MAGIC = 0x4699

    class Type():
        ACCEPT = 0x0002
        REFUSE = 0x0004

        CONNECT = 0x0001
        DISCONNECT = 0x0005
        HEARTBEAT = 0x0007
        STATUS = 0x0009

        GET_TOKEN = 0x0021
        GET_TOKEN_ACK = 0x0022
        ACCESS_GRANTED = 0x0024

        NONE = 0x0000

    class ECode():
        RELAY_SERVER_INVALID = 0x5001
        RELAY_SERVER_OVERLOAD = 0x5002
        RELAY_SERVER_ERROR_CONNECT_INFO = 0x5003

    def __init__(self, data):
        self.data = data
        self.is_valid = False
        self.msg_type = RelayManagerMessage.Type.NONE
        self.content = None
        self.body = {'data': None}

        if len(data) < RelayManagerMessage.__HEADER_LEN:
            return

        header, body = data[:RelayManagerMessage.__HEADER_LEN], data[RelayManagerMessage.__HEADER_LEN:]
        magic, msg_type, body_len = struct.unpack('!HHi', header)
        if magic != RelayManagerMessage.MAGIC or body_len != len(body):
            return
        self.msg_type = msg_type

        # Parse message body, MUST set 'self.is_valid' to True when body is valid.
        if msg_type == RelayManagerMessage.Type.ACCEPT:
            if body_len == 0:
                self.is_valid = True
        elif msg_type == RelayManagerMessage.Type.REFUSE:
            self.content = Message.get_unpacked_json_data(body)
            if isinstance(self.content, dict):
                try:
                    self.ecode = int(self.content['reason'])
                    self.message = str(self.content['message'])
                    self.is_valid = True
                except:
                    log.e('The content of RM refuse is invalid, %s.' % str(self.content))
        elif msg_type == RelayManagerMessage.Type.GET_TOKEN_ACK:
            self.content = Message.get_unpacked_json_data(body)
            if isinstance(self.content, dict):
                try:
                    self.body['serial_no'] = str(self.content['serialNo'])
                    self.body['service'] = str(self.content['service'])
                    if 'token' in self.content:
                        self.body['token'] = str(self.content['token'])
                    else:
                        self.body['token'] = None
                    self.is_valid = True
                except:
                    log.e('The content of RM get-token-ack is invalid, %s.' % str(self.content))
        elif msg_type == RelayManagerMessage.Type.ACCESS_GRANTED:
            self.content = Message.get_unpacked_json_data(body)
            if isinstance(self.content, dict):
                try:
                    self.body['serial_no'] = str(self.content['serialNo'])
                    self.body['service'] = str(self.content['service'])
                    self.body['token'] = str(self.content['token'])
                    self.body['expire'] = int(self.content['expire']) * 60
                    self.is_valid = True
                except:
                    log.e('The content of RM get-token-ack is invalid, %s.' % str(self.content))
        else:
            log.e('Unknown relay manger message type.')

    @staticmethod
    def __create_data(msg_type, *args):
        return Message.create_data(msg_type, *args, magic=RelayManagerMessage.MAGIC)

    @staticmethod
    def create_connect_data(content):
        """
        :param content: The data is in json format.
        """
        return RelayManagerMessage.__create_data(RelayManagerMessage.Type.CONNECT, json.dumps(content))

    @staticmethod
    def create_disconnect_data():
        return RelayManagerMessage.__create_data(RelayManagerMessage.Type.DISCONNECT)

    @staticmethod
    def create_heartbeat_data():
        return RelayManagerMessage.__create_data(RelayManagerMessage.Type.HEARTBEAT)

    @staticmethod
    def create_load_balance_data(content):
        """
        :param content: The data is in json format.
        """
        return RelayManagerMessage.__create_data(RelayManagerMessage.Type.STATUS, json.dumps(content))

    @staticmethod
    def create_get_token_data(content):
        return RelayManagerMessage.__create_data(RelayManagerMessage.Type.GET_TOKEN, json.dumps(content))
