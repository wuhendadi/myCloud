
__version__ = '1.2'
__author__ = 'Fred'

import sys
import os

# For run in console.
src_dir = os.path.dirname(os.path.realpath(__file__))
relay_dir = os.path.dirname(src_dir)
# sys.path.append(os.path.dirname(src_dir))
sys.path.append(src_dir)

import socket
import select
import json
import datetime
import time
from threading import Thread
import threading
from collections import deque
import errno

from log import log
from config import config
from proxy import UpnpWrapper, HubLinker
from message import Message, ECode, Type
from conn import Connection, BoxConnection, RelayConnection, ClientConnection


class RelayServer():
    MSG_QUIT = 'quit-relay-thread'

    def __init__(self, upnp):
        self.upnp = UpnpWrapper(self, upnp)

        self.s = None  # Waiting socket for box.
        self.box_cache = []  # Used for box or RM-test-tcp-punching.
        self.box = None  # Box connection, none means no box connected-and-authorised.
        # Wait for client and thread-quit notification.
        self.cs = None  # Waiting socket for clients.
        self.clients = []  # Client connections.

        self.__is_quit_thread = False
        self.__qs = None # To quit relay thread.
        self.relay_thread = None
        self.hub_linker = None

        self.__notify_box_close_lock = threading.Lock()

    def start(self):
        if self.is_started():
            log.d('Box relay has already started!!!')
            return

        config.bind_except_hook()

        self.hub_linker = HubLinker(self)

        self.__qs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upnp.quit_port = self.hub_linker.bind_socket_to_port(self.__qs, self.upnp.address, self.upnp.quit_port)
        self.__qs.listen(5)
        log.d('Prepare quit port: %s, %d' % (self.upnp.address, self.upnp.quit_port))
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upnp.port = self.hub_linker.bind_socket_to_port(self.s, self.upnp.address, self.upnp.port)
        self.s.listen(10)
        log.d('Prepare box port: %s, %d' % (self.upnp.address, self.upnp.port))
        self.box = None
        self.cs = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.upnp.client_port = self.hub_linker.bind_socket_to_port(self.cs, self.upnp.address, self.upnp.client_port)
        log.d('Prepare client port: %s, %d' % (self.upnp.address, self.upnp.client_port))
        self.cs.listen(5)
        self.clients = []

        self.relay_thread = Thread(target=RelayServer.__start_main, args=(self,))
        self.relay_thread.start()

        self.hub_linker.start()

    def stop(self):
        if not self.is_started():
            log.d('Box relay has already stopped!!!')
            return

        # TODO: Need notify first.
        self.__clean_cached_boxes()

        if self.box:
            self.__notify_box_close()

        self.hub_linker.stop()
        self.__notify_relay_thread_quit()
        self.relay_thread.join()
        self.relay_thread = None

        self.upnp.release_upnp_ports()

        if self.box:
            self.__close_box()
        self.cs.close()
        self.cs = None
        self.s.close()
        self.s = None

        self.__qs.close()
        self.__qs = None

        log.d('Box relay stopped.')

    def __notify_relay_thread_quit(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self.upnp.address, self.upnp.quit_port))
        s.send(RelayServer.MSG_QUIT)
        s.close()

    @staticmethod
    def __start_main(self):
        self.__is_quit_thread = False
        while not self.__is_quit_thread:
            read_list = [self.__qs]
            write_list = []
            err_list = []

            # Box or box-cache connections.

            read_list.append(self.s)

            if self.box_cache:  # connected without authorized
                read_list.extend(self.box_cache)
                # INFO: If cached-box need read, then it is self.box.
                err_list.extend(self.box_cache)

            if self.box: # The only authorized box.
                read_list.append(self.box)
                if self.box.has_buffered_datas(): write_list.append(self.box)
                err_list.append(self.box)

            # Client connections.

            read_list.append(self.cs)

            if self.clients:
                read_list.extend(self.clients)
                write_list.extend(filter(lambda c: c.has_buffered_datas(), self.clients))
                err_list.extend(self.clients)

            # log.v('READLIST: %s' % str(len(read_list)))
            # log.v('WRITELIST: %s' % str(len(write_list)))
            # log.v('ERRORLIST: %s' % str(len(err_list)))
            # self.dump()

            # Wait.

            read_result, write_result, err_result = select.select(read_list, write_list, err_list, 5)

            # Handle read, write and error connections.

            log.v('Before handle connection or socket')

            for e in err_result:
                self.__handle_connection_error(e)

            for r in read_result:
                self.__handle_connection_read(r)

            for w in write_result:
                self.__handle_connection_write(w)

            self.__handle_connection_timeout()

            log.v('After handle connection or socket')

    def __handle_connection_read(self, r):
        # log.v('Handle connection reading.')

        if r is self.s:
            log.v('Handle box listener reading.')

            c, addr = r.accept()
            conn = BoxConnection(c)
            log.d('Connected by box %d, address, %s' % (conn.uuid, repr(addr)))
            if self.box:
                conn.close()
            else:
                self.box_cache.append(conn)
        elif r in self.box_cache:
            log.v('Handle cached box reading.')

            try:
                self.__handle_cached_box_connection(r)
            except (socket.error, socket.timeout) as e:
                log.e('Cached box %d connection encounter an error: %s' % (r.uuid, str(e)))
                self.__close_cached_box(r)
        elif r is self.box:
            log.v('Handle box reading.')

            try:
                self.__handle_box_connection(r)
            except (socket.error, socket.timeout) as e:
                log.e('Box %d connection encounter an error: %s' % (r.uuid, str(e)))
                self.__close_box()
        elif r is self.cs:
            log.v('Handle client listener reading.')

            c, addr = r.accept()
            conn = ClientConnection(c)
            log.d('Connected by client %d, address, %s' % (conn.uuid, repr(addr)))
            if not self.box:
                log.d('Skip this client because no box connected !!!')
                conn.close()
                return
            self.clients.append(conn)
        elif r in self.clients:
            log.v('Handle client reading.')

            try:
                r.timeout_tracer.reset()
                self.__handle_client_connection(r)
            except (socket.error, socket.timeout) as e:
                log.e('Client %d connection enconter an error: %s.' % (r.uuid, str(e)))
                self.__notify_box_client_broken(r.uuid)
                self.__close_client(r)
        elif r is self.__qs:
            log.v('Handle quit-socket reading.')

            self.__handle_quit_request(r)
        else:
            log.d('The connection does not need handle.')

    def __handle_quit_request(self, r):
        c, addr = r.accept()
        data = c.recv(config.SOCKET_RECV_LEN)
        if data == RelayServer.MSG_QUIT:
            self.__is_quit_thread = True
            log.d('Get a quit request from quit-port.')
        else:
            log.e('Get an unknown message from quit-port.')

    def __handle_cached_box_connection(self, c):
        msg = Message(c.recv(config.SOCKET_RECV_LEN), c)
        if not msg.is_valid:
            raise socket.error('Invalid register message from box')

        if msg.type == Type.CONNECT:
            if not self.__handle_box_register(c, msg):
                raise socket.error('Box failed to register')

            self.box = c
            self.box.ping_tracer.reset()
            self.box.timeout_tracer.reset()
            self.box_cache.remove(c)
            self.__clean_cached_boxes()
        else:
            log.v('Unknown message type %d from cached-box %d' % (msg.type, c.uuid))

    def __handle_box_connection(self, c):
        msg = Message(c.recv(config.SOCKET_RECV_LEN), c)
        if not msg.is_valid:
            raise socket.error('Invalid message from box')

        if msg.type == Type.SERVER_DATA:
            c.timeout_tracer.reset()
            c.ping_tracer.reset()
            self.__handle_box_server_data(c, msg)
        elif msg.type == Type.DISCONNECT:
            socket.error('Box %d notify disconnect' % c.uuid)
        elif msg.type == Type.SERVER_ERROR:
            self.__handle_box_server_error(c, msg)
        elif msg.type == Type.PING:
            log.v('Get box %d PING message.' % c.uuid)
            c.ping_tracer.reset()
            c.append_data_to_buffer(Message.create_ping_ack_data())
        else:
            log.v('Unknown message type %d from box %d' % (msg.type, c.uuid))

    def __handle_box_register(self, c, msg):
        """
        :param c:
        :param msg:
        :return: the box is valid.
        """

        log.d('Get box %d register content: %s' % (c.uuid, msg.content))

        try:
            sn = str(msg.content['deviceId'])
            service = str(msg.content['service'])
            token = str(msg.content['token'])
        except:
            log.e('Box register information format is not correct.')
            c.send(Message.create_refuse_data(ECode.RELAY_BOX_INVALID_INFO))
            return False

        device_token = self.hub_linker.connector.verify_token(sn, service, token)
        if not device_token:
            log.e('Box register information is invalid by hub.')
            c.send(Message.create_refuse_data(ECode.RELAY_BOX_INVALID_INFO))
            return False

        log.d('Box register info is valid, device_id %s, token %s.' % (str(sn), str(token)))

        _, _, cport, udp_port = self.upnp.get_router_info()
        if not cport:
            log.e('Can not set up client upnp port.')
            c.send(Message.create_refuse_data(ECode.RELAY_FAILED_CREATE_CLIENT_PORT))
            return False
        reply = {'port': str(cport)}
        c.send(Message.create_accept_data(reply))
        return True

    def __handle_box_server_data(self, c, msg):
        for cc in self.clients:
            if cc.uuid == msg.uuid:
                log.v('Send data to client %d from box %d.' % (cc.uuid, c.uuid))
                cc.append_data_to_buffer(msg.content)
                return
        log.v('Can not find client %d when box sending data.' % msg.uuid)
        self.__notify_box_client_broken(msg.uuid)

    def __handle_box_server_error(self, c, msg):
        log.d('Get an error message from box %d for client %d.' % (self.box.uuid, c.uuid))
        for cc in self.clients:
            if cc.uuid == msg.uuid:
                self.__close_client(cc)
                return

    def __handle_client_connection(self, c):
        data = c.recv(config.SOCKET_RECV_LEN)
        if not data:
            raise socket.error('Client send EOF.')
        log.v('Send data to box %d from client %d' % (self.box.uuid, c.uuid))
        # MUST check here.
        self.box.timeout_tracer.reset()
        self.box.ping_tracer.reset()
        self.box.append_data_to_buffer(Message.create_client_data_data(c.uuid, data))

    def __handle_connection_write(self, c):
        log.v('Handle connection writing.')

        if c is self.box:
            log.v('Handle box writing.')

            try:
                # Check box timeout without PING from relay.
                # c.timeout_tracer.reset()
                c.send()
                if c.blocked:
                    self.__close_box()
            except (socket.error, socket.timeout) as e:
                log.e('Send buffered datas to box %d failed: %s' % (c.uuid, str(e)))
                self.__close_box()
        elif c in self.clients:
            log.v('Handle client writing.')

            try:
                log.v('Send data to client %d in __handle_connection_write().' % c.uuid)
                c.timeout_tracer.reset()
                changed = c.send()
                if changed:
                    if c.blocked:
                        log.v('Client %d has blocked' % c.uuid)
                        self.box.append_data_to_buffer(Message.create_pause_data(c.uuid))
                    else:
                        log.v('Client %d has not blocked' % c.uuid)
                        self.box.append_data_to_buffer(Message.create_resume_data(c.uuid))
                else:
                    # log.v('Client %d blocked state has not changed.' % c.uuid)
                    pass
            except (socket.error, socket.timeout) as e:
                log.e('Send buffered datas to client failed: %s' % str(e))
                self.__notify_box_client_broken(c.uuid)
                self.__close_client(c)

    def __handle_connection_error(self, c):
        # log.v('Handle connection error.')

        if c in self.box_cache:
            log.e('Cached box %d error from select().' % c.uuid)
            self.__close_cached_box(c)
        elif c is self.box:
            log.e('Box %d error from select().' % c.uuid)
            self.__close_box()
        elif c in self.clients:
            log.e('Client %d error from select().' % c.uuid)
            self.__close_client(c)

    def __handle_connection_timeout(self):
        # log.v('Handle connection in select() timeout.')

        # Clean cached boxes.

        for c in self.box_cache[:]:
            if c.ping_tracer.update():  # Image no ping msg.
                self.__close_cached_box(c)

        # Check client connection timeout.

        for c in self.clients[:]:
            if c.timeout_tracer.update():
                log.d('Client %d connection closed because timeout.' % c.uuid)

                self.box.append_data_to_buffer(
                    Message.create_client_error_data(c.uuid, ECode.RELAY_CLIENT_TIMEOUT))
                self.__close_client(c)

        # Check box connection timeout.

        if self.box:
            is_no_ping = self.box.ping_tracer.update()
            is_timeout = self.box.timeout_tracer.update()
            if is_no_ping or is_timeout:
                log.d('Box %d connection closed because %s.'
                      % (self.box.uuid, 'no ping' if is_no_ping else 'timeout'))

                self.__notify_box_close()
                self.__close_box()

    def __close_cached_box(self, r):
        r.close()
        self.box_cache.remove(r)

    def __clean_cached_boxes(self):
        for c in self.box_cache:
            c.close()
        self.box_cache = []

    def __close_box(self):
        for cc in self.clients:
            cc.close()
        self.clients = []
        self.box.close()
        self.box = None

    def __close_client(self, r):
        r.close()
        self.clients.remove(r)

    def __notify_box_client_broken(self, uuid):
        log.v('Notify box %d that client %d has broken.' % (self.box.uuid, uuid))
        self.box.append_data_to_buffer(Message.create_client_error_data(uuid, ECode.RELAY_CLIENT_DISCONNECTED))

    def __notify_box_close(self):
        with self.__notify_box_close_lock:
            log.v('Notify box %d close.' % self.box.uuid)
            try:
                self.box.send(Message.create_close_data())
            except Exception as e:
                log.e('Send close message failed.')

    def is_busy(self):
        return bool(self.box)

    def is_started(self):
        """ -> Whether box relay is started.
        """
        return bool(self.__qs)

    def dump(self):
        log.v('>>>>>>>>>>>>>> dump tcp relay begin <<<<<<<<<<<<<<')
        log.v('Cached Box: %d' % len(self.box_cache))
        log.v('Box: %s' % str(bool(self.box)))
        if self.box:
            log.v('Box Messages to Send: %d' % len(self.box.data_queue))
        log.v('Clients: %d' % len(self.clients))
        for c in self.clients:
            log.v('Client Messages to Send: %d' % len(c.data_queue))
        log.v('>>>>>>>>>>>>>> dump tcp relay end <<<<<<<<<<<<<<')


if __name__ == '__main__':
    is_test_start_stop = False

    if config.HAS_POPOCLOUD:
        import StartFunc
        upnp = StartFunc.UpupThread(None)
        relay = RelayServer(upnp)
        relay.start()
        upnp.start()
    else:
        relay = RelayServer(None)
        if is_test_start_stop:
            while True:
                relay.start()
                relay.start()
                time.sleep(1)
                relay.stop()
                relay.stop()
                time.sleep(5)
        else:
            relay.start()
            while True:
                time.sleep(5)

    # [TEST] Close message
    # relay = RelayServer(None)
    # relay.start()
    # time.sleep(10)
    # relay.stop()

    print 'After relay.stop()'
