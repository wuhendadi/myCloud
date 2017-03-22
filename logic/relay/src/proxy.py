__author__ = 'Fred'

import socket
import json
import time
from threading import Thread
import threading
import requests
import select
import Queue

from log import log
from config import config
from message import HubMessage, RelayManagerMessage
from conn import RelayManagerConnection
import speedtest
import stun


class UpnpWrapper():
    """ Used to define box relay local ports and upnp ports.
    """
    def __init__(self, relay, upnp):
        self.relay = relay
        self.upnp = upnp
        self.address = self._get_local_address()
        log.d('local address: %s' % self.address)
        self.port = 8100 # May be changed by RelayServer.
        self.client_port = 8120 # May be changed by RelayServer.
        self.quit_port = 8140 # May be changed by RelayServer.
        self.udp_port = 8160 # May be changed by StunServer.
        self.last_ports = None

    def _get_local_address(self):
        if config.HAS_POPOCLOUD:
            import UtilFunc
            return UtilFunc.getLocalIp()
        return '127.0.0.1'

    def get_router_info(self):
        if config.HAS_POPOCLOUD:
            portlist = [{'name':'BoxRelay', 'port':self.port},
                        {'name':'ClientRelay', 'port':self.client_port},
                        {'name':'UDPRelay','port':self.client_port}]
            ports = self.upnp.getUPNPInfo(portlist)
            if not ports or len(ports) < 2:
                self.router_port = None
                self.router_client_port = None
                return self.upnp.natip, None, None, None
            self.last_ports = [ports[0]['natPort'], ports[1]['natPort'], ports[2]['natPort']]
            return self.upnp.natip, ports[0]['natPort'], ports[1]['natPort'], ports[2]['natPort']
        return '127.0.0.1', 38100, 38101, 38102

    def release_upnp_ports(self):
        if config.HAS_POPOCLOUD:
            if self.last_ports:
                self.upnp.removePortMapping(self.last_ports)

    def get_box_serial(self):
        if config.HAS_POPOCLOUD:
            import UtilFunc
            return UtilFunc.getSN()
        return '0000000000000000'


class DeviceToken():
    """ For get-token-ack and access-granted.
    SUPPORT multi-thread op
    """

    TIMEOUT = 3 * 60 * 60

    tokens = {}  # username: DeviceToken
    tokens_lock = threading.Lock()

    @staticmethod
    def add(sn, service, token, expire=None):
        """
        -> token
        """
        token = DeviceToken(sn, service, token, expire)
        DeviceToken.tokens[token.username] = token
        return token

    @staticmethod
    def get(sn, service):
        """
        -> token
        """
        token = DeviceToken(sn, service, '')
        return DeviceToken.tokens.get(token.username, None)

    # For DeviceToken

    def __init__(self, sn, service, token, expire=None):
        self.sn = sn
        self.service = service
        self.token = token
        self.__is_accessed = True
        self.__tracer = stun.ExpiredObj(DeviceToken.TIMEOUT)
        if not expire is None:
            self.__is_accessed = False
            self.__tracer.refresh_to(expire)

    def get_username(self):
        return self.service + '@' + self.sn

    def set_username(self, value):
        pos = value.find('@')
        self.sn = value[pos + 1:]
        self.service = value[:pos]

    username = property(get_username, set_username)


class RelayManagerConnector(Thread):
    __HEARTBEAT_INTERVAL = 30
    __LOAD_BALANCE_INTERVAL = 60
    __SPEED_TEST_INTERVAL = 60 * 5

    class Message(stun.ExpiredObj):
        """ Used to handle tcp relay verify-token request.
        """

        TIMEOUT = 60

        def __init__(self, token):
            stun.ExpiredObj.__init__(self, RelayManagerConnector.Message.TIMEOUT)
            self.token = token  # DeviceToken
            self.return_token = None
            self.event = threading.Event()

        def wait(self):
            self.event.wait()

        def notify(self, token):
            self.return_token = token
            self.event.set()

    class MessageUdp(stun.ExpiredObj):
        """ Used to handle udp relay verify-token request.
        """

        def __init__(self, server, token, udp_data):
            """
            :param server: stun.StunServer
            :param token: DeviceToken
            :param udp_data:
            :return:
            """
            stun.ExpiredObj.__init__(self, RelayManagerConnector.Message.TIMEOUT)
            self.token = token
            self.return_token = None  # DeviceToken, None means the username is invalid.
            self.server = server
            self.udp_data = udp_data

    def __init__(self, hub, udp_server):
        Thread.__init__(self)

        self.hub = hub
        self.upnp = hub.upnp
        self.relay = hub.relay
        self.udp_server = udp_server

        self.address = (config.RELAY_MANAGER_ADDRESS, config.RELAY_MANAGER_PORT)
        self.is_quit = False

        # tracers
        self.heartbeat_tracer = stun.ExpiredObj(self.__HEARTBEAT_INTERVAL)
        self.load_balance_tracer = stun.ExpiredObj(self.__LOAD_BALANCE_INTERVAL)
        self.speed_test_tracer = stun.ExpiredObj(self.__SPEED_TEST_INTERVAL)

        # Network speed test.
        self.is_updating_network_speed = False
        self.download_speed = 0
        self.upload_speed = 0

        # Waiting verify-token-message.
        # Used for multi-threads.
        self.__msg_queue = Queue.Queue()
        self.__msg_queue_udp = Queue.Queue()

        # username: RelayManagerConnector.Message, FIFO
        # Used for this thread, notify when get-token-ack or timeout.
        self.waiting_messages = []
        self.waiting_messages_udp = []

        # Attach to udp server.
        self.udp_server.attach_rm_connector(self)

    def run(self):
        self.is_quit = False

        while not self.is_quit:
            log.v('[RM] Try connect to relay manager.')

            self.conn = RelayManagerConnection(socket.socket(socket.AF_INET, socket.SOCK_STREAM))

            try:
                self.__connect()
            except (socket.error, socket.timeout) as e:
                log.e('[RM] Send connect request to relay manager failed: %s' % str(e))
                self.conn.close()
                time.sleep(30)
                continue

            log.v('[RM] Relay manager connected.')

            self.__update_network_speed()
            self.__send_heartbeat()
            self.__send_status()

            while not self.is_quit:
                try:
                    reads, _, errors = select.select([self.conn], [], [self.conn], 1)
                    self.__update_messages()
                    self.__update_messages_udp()
                    self.__update_tracers()
                    if self.conn in reads:
                        self.__handle_conn()
                    if self.conn in errors:
                        raise socket.error('connection error in select()')
                except (socket.error, socket.timeout) as e:
                    log.e('[RM] Send HEARTBEAT or STATUS failed: %s' % str(e))
                    self.conn.close()
                    time.sleep(1)
                    break

        # Quit the connection.
        try:
            self.__send_disconnect()
            self.conn.close()
        except (socket.error, socket.timeout) as e:
            pass

    def __handle_get_token_ack(self, msg):
        # Add to cache.
        if msg.body['token'] is not None:
            token = DeviceToken.add(msg.body['serial_no'], msg.body['service'], msg.body['token'])

        for m in self.waiting_messages[:]:
            if token.username == m.token.username:
                m.notify(token if m.token.token == token.token else None)
                self.waiting_messages.remove(m)

        for m in self.waiting_messages_udp[:]:
            if token.username == m.token.username:
                msg.server.post_verify_token_ack_msg(msg.udp_data, msg.body['token'])

    def __handle_access_granted(self, msg):
        DeviceToken.add(msg.body['serial_no'], msg.body['service'], msg.body['token'], msg.body['expire'])

    def __handle_conn(self):
        msg = RelayManagerMessage(self.conn.recv(config.SOCKET_RECV_LEN, magic=0x4699))
        if not msg.is_valid:
            return
        if msg.msg_type == RelayManagerMessage.Type.GET_TOKEN_ACK:
            self.__handle_get_token_ack(msg)
        elif msg.msg_type == RelayManagerMessage.Type.ACCESS_GRANTED:
            self.__handle_access_granted(msg)
        else:
            log.e('Invalid msg from RM.')

    def __update_tracers(self):
        if self.heartbeat_tracer.update():
            self.__send_heartbeat()
            self.heartbeat_tracer.refresh()
        if self.load_balance_tracer.update():
            self.__send_status()
            self.load_balance_tracer.refresh()
        if self.speed_test_tracer.update():
            self.__update_network_speed()
            self.speed_test_tracer.refresh()

    def __update_messages(self):
        """ Handle message from other thread with timeout or sending get-token msg to RM.
        """

        # handle rm-connector msg timeout
        for msg in self.waiting_messages[:]:
            if msg.update():
                msg.notify(None)
                self.waiting_messages.remove(msg)

        # send get-token msg to RM and put rm-connector msg to waiting list.
        try:
            while True:
                msg = self.__msg_queue.get_nowait()
                self.waiting_messages.append(msg)
                self.__send_get_token(msg.token.sn, msg.token.service)
        except Queue.Empty:
            pass

    def __update_messages_udp(self):
        """ Handle message from other thread with timeout or sending get-token msg to RM.
        """

        # handle rm-connector msg timeout
        for msg in self.waiting_messages_udp[:]:
            if msg.update():
                msg.server.post_verify_token_ack_msg(msg.udp_data, None)

        # send get-token msg to RM and put rm-connector msg to waiting list.
        try:
            while True:
                msg = self.__msg_queue_udp.get_nowait()
                self.waiting_messages.append(msg)
                self.__send_get_token(msg.sn, msg.service)
        except Queue.Empty:
            pass

    def __connect(self):
        info = {
            'serverId': self.upnp.get_box_serial(),
            'serverType': 'contributed',
        }
        log.v('[RM] CONNECT TO: %s; INFO: %s' % (str(self.address), str(info)))
        # self.conn = RelayManagerConnection(socket.socket(socket.AF_INET, socket.SOCK_STREAM))
        self.conn.connect(self.address)
        self.conn.send(RelayManagerMessage.create_connect_data(info))
        log.v('[RM] After send when connecting.')
        data = self.conn.recv(config.SOCKET_RECV_LEN, magic=RelayManagerMessage.MAGIC)
        log.v('[RM] After recv when connecting.')
        if not data:
            raise socket.error('EOF')
        msg = RelayManagerMessage(data)
        if not msg.is_valid:
            raise socket.error('Invalid message')
        if msg.msg_type != RelayManagerMessage.Type.ACCEPT:
            raise socket.error('Not accepted')

    def __send_status(self):
        addr, port, cport, udp_port = self.upnp.get_router_info()
        info = {
            'cpuRatio': self.__get_cpu_utilization_ratio(),
            'memoryRatio': self.__get_memory_utilization_ratio(),
            'ioRatio': 0.0,
            'bandwidthUpload': str(self.upload_speed),
            'bandwidthDownload': str(self.download_speed),
            'connections': '0',
            'dataRate': '0',
            # 'status': 'busy' if self.relay.is_busy() or self.udp_server.is_busy() else 'free',
            'status': 'busy' if self.relay.is_busy() else 'free',
            'ip': addr,
            'tcpPort': str(port) if port else '',
            # 'udpPort': udp_port,
            'udpPort': '',
        }
        log.d('[RM] STATUS: %s' % str(info))
        self.conn.send(RelayManagerMessage.create_load_balance_data(info))

    def __send_heartbeat(self):
        log.d('[RM] HEARTBEAT')
        self.conn.send(RelayManagerMessage.create_heartbeat_data())

    def __send_disconnect(self):
        self.conn.send(RelayManagerMessage.create_disconnect_data())

    def __send_get_token(self, sn, service):
        self.conn.send(RelayManagerMessage.create_get_token_data({
            'serialNo': sn,
            'service': service
        }))

    def __get_cpu_utilization_ratio(self):
        try:
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                words = ' '.join(line.split()).split(' ')
                if len(words) >= 8:
                    is_all_numbers = True
                    for i in range(1, 8):
                        if not words[i].isdigit():
                            is_all_numbers = False
                            break
                    if is_all_numbers:
                        used = int(words[1]) + int(words[2]) + int(words[3]) \
                               + int(words[5]) + int(words[6]) + int(words[7])
                        idle = int(words[4])
                        usage = (float(used) / (float(used) + float(idle))) * 100.0
                        return '{0:.1f}'.format(usage)
        except IOError, e:
            return 0.0

    def __get_memory_utilization_ratio(self):
        try:
            with open('/proc/meminfo', 'r') as f:
                line1 = f.readline()
                line2 = f.readline()
                words1 = ' '.join(line1.split()).split()
                words2 = ' '.join(line2.split()).split()
                if len(words1) >= 2 and len(words2) >= 2 and words1[1].isdigit() and words2[1].isdigit():
                    total = int(words1[1])
                    free = int(words2[1])
                    usage = ((float(total) - float(free)) / float(total)) * 100.0
                    return '{0:.1f}'.format(usage)
        except IOError, e:
            return 0.0

    def __update_network_speed(self):
        if self.is_updating_network_speed:
            return

        class UpdateThread(Thread):
            def __init__(self, conn):
                Thread.__init__(self)
                self.conn = conn

            def run(self):
                log.v('[RM] Update network speed.')
                d, u = speedtest.get_speeds()
                if d and u:
                    self.conn.download_speed = int(d) * 8
                    self.conn.upload_speed = int(u) * 8
                self.conn.is_updating_network_speed = False

        self.is_updating_network_speed = True
        UpdateThread(self).start()

    def verify_token(self, sn, service, token):
        """
        -> DeviceToken if found else None.
        """
        with DeviceToken.tokens_lock:
            token_obj = DeviceToken.get(sn, service)
            if token_obj:
                if token_obj.token != token:
                    return None
                return token_obj
        msg = RelayManagerConnector.Message(DeviceToken(sn, service, token))
        try:
            self.__msg_queue.put_nowait(msg)
        except Queue.Full:
            return None
        msg.wait()
        return msg.return_token

    # For udp.

    def verify_token_for_udp(self, udp_server, username, udp_data):
        """
        :param msg: MessageUdp
        :return: DeviceToken, None(wait response from rm)
        """
        t = DeviceToken(None, None, None)
        t.set_username(username)
        msg = RelayManagerConnector.MessageUdp(udp_server, t, udp_data)

        with DeviceToken.tokens_lock:
            token_obj = DeviceToken.get(msg.token.sn, msg.token.service)
            if token_obj:
                return token_obj

        try:
            self.__msg_queue.put_nowait(msg)
        except Queue.Full:
            return None

        return None


class HubLinker():
    """ Keep alive with Relay Manager of HUB.
    """
    def __init__(self, relay):
        self.relay = relay
        self.upnp = relay.upnp
        self.udp_server_thread = stun.StunServerThread()
        self.connector = RelayManagerConnector(self, self.udp_server_thread.server)

    def start(self):
        self.connector.start()
        self.udp_server_thread.start()

    def stop(self):
        self.connector.is_quit = True
        self.connector.join()

    def bind_socket_to_port(self, s, ip, port):
        """ Bind a socket with ip and port and return bound port.
        """
        count = 0
        cur_port = port
        while True:
            try:
                cur_port = port + count
                s.bind((ip, cur_port))
                break
            except socket.error as err:
                log.e('Bind port %s, %d failed, error number: %d' % (ip, cur_port, err.errno))
                count += 1
                if count > 15:
                    count = 0
                time.sleep(2)
        return cur_port

if __name__ == '__main__':
    pass
