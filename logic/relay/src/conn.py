# -*- coding: utf-8 -*-

from log import log
from message import Message

import socket
import datetime
import time
from collections import deque
import errno
from config import config


class TimeoutTracer():
    def __init__(self, timeout):
        """
        :param timeout: timeout for this tracer.
        """
        self.timeout = timeout
        self.reset()

    def reset(self):
        """ Reset to init value.
        """
        self.current = self.last = self.__get_cur_timestamp()

    def update(self):
        """ -> whether exceed timeout value.
        """
        self.current = self.__get_cur_timestamp()
        return self.current - self.last > self.timeout

    def remain(self):
        return self.timeout - (self.current - self.last)

    def __get_cur_timestamp(self):
        return time.mktime(datetime.datetime.now().timetuple())


class Connection():
    """ Base class to wrapper socket.
    """

    __last_uuid = 0

    def __init__(self, s):
        self.s = s # socket
        # self.set_keepalive(self.s) # does not supported in android.
        self.uuid = self.__next_uuid()
        self.data_queue = deque() # queue for datas to client.
        self.send_max_count = 5 # max count of datas when sending from queue.
        self.blocked = False
        self.timeout_tracer = TimeoutTracer(config.TIMEOUT_TCP_NO_DATE_TRANSFER)
        self.ping_tracer = TimeoutTracer(config.TIMEOUT_TCP_PING)

    def __next_uuid(self):
        Connection.__last_uuid += 1
        return Connection.__last_uuid

    def __send_a_data(self, data):
        """ Send a data to client.
        """
        send_data = data
        try:
            while send_data:
                length = self.s.send(send_data)
                send_data = send_data[length:] if length < len(send_data) else None
            self.blocked = False
        except (socket.error, socket.timeout) as e:
            err = e.args[0]
            self.blocked = True
            if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                log.v('Client %d block error %d, need send later.' % (self.uuid, err))
                self.data_queue.appendleft(send_data)
                return
            raise socket.error(e)

    def send(self, data=None):
        """ -> whether blocked state is changed.
        """
        old_blocked = self.blocked
        if data: self.append_data_to_buffer(data)
        count = 0
        while self.data_queue and count <= self.send_max_count:
            changed = self.__send_a_data(self.data_queue.popleft())
            if self.blocked: return not old_blocked
            count += 1
        return old_blocked

    def has_buffered_datas(self):
        """ Is need send in select() operation.
        """
        return bool(self.data_queue)

    def append_data_to_buffer(self, data):
        self.data_queue.append(data)

    def recv(self, length):
        return self.s.recv(length)

    def close(self):
        self.s.close()

    def fileno(self):
        return self.s.fileno()

    def set_keepalive(self, s, after_idle_sec=1, interval_sec=5, max_fails=18):
        """Set TCP keepalive on an open socket.

        It activates after 1 second (after_idle_sec) of idleness,
        then sends a keepalive ping once every 5 seconds (interval_sec),
        and closes the connection after 18 failed ping (max_fails), or 90 seconds
        """
        s.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
        s.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)


class ClientConnection(Connection):
    """ Handle connection came from client.
    """

    def __init__(self, s):
        Connection.__init__(self, s)
        self.s.setblocking(False)


class RelayConnection(Connection):
    """ Handle connection to relay.
    """
    def __init__(self, s):
        Connection.__init__(self, s)

    #override
    def recv(self, length, **kwargs):
        """ For box/client or relay manager.
        length MUST > Message.HEADER_LEN
        """
        assert length > Message.HEADER_LEN
        magic = kwargs.get('magic', Message.MAGIC)
        header = self.__recv(Message.HEADER_LEN)
        if not header: return ''
        body_len = Message.parse_body_length(header, magic=magic)
        if body_len == -1: return header + self.s.recv(length - Message.HEADER_LEN)
        return header + self.__recv(body_len)

    def __recv(self, target_len):
        recv_data = ''
        recv_len = 0
        while recv_len < target_len:
            data = self.s.recv(target_len - recv_len)
            if not data: break
            recv_data += data
            recv_len = len(recv_data)
        return recv_data


class BoxConnection(RelayConnection):
    """ Handle connection came from box.
    """
    def __init__(self, s):
        RelayConnection.__init__(self, s)
        self.is_registered = False  # Unused


class RelayManagerConnection(RelayConnection):
    """ Handle connection to relay manager.
    """
    def __init__(self, s):
        RelayConnection.__init__(self, s)
        self.connect = s.connect


if __name__ == '__main__':
    import time
    to = TimeoutTracer(30)
    for i in range(10):
        print 'Remain:', to.remain()
        time.sleep(5)
        to.update()
