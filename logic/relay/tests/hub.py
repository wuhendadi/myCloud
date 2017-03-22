__author__ = 'Fred'

import socket
import select
import json
import os
import sys

# For run in console.
parent = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(parent)
sys.path.append(os.path.join(parent, 'src'))

from message import HubMessage


class HubServer():
    def __init__(self, address, port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.bind((address, port))
        self.s.listen(5)
        print 'Prepared hub in: %s, %d' % (address, port)

        self.relays = []

    def start(self):
        while True:
            read_list = []
            read_list.append(self.s)
            read_list.extend(self.relays)
            read_result, _, _ = select.select(read_list, [], [])
            for r in read_result:
                if r is self.s:
                    c, addr = self.s.accept()
                    print 'Connected by %s' % repr(addr)
                    self.relays.append(c)
                elif r in self.relays:
                    try:
                        self._handle_relay_connection(r)
                    except socket.error, socket.timeout:
                        print 'Relay has broken.'
                        r.close()
                        self.relays.remove(r)

    def _handle_relay_connection(self, c):
        msg = HubMessage(c.recv(1024))
        if not msg.is_valid:
            return
        print 'RECV: %s' % msg.content
        reply = {'result': 'OK'}
        c.send(HubMessage.create_communicate_data(json.dumps(reply)))


if __name__ == '__main__':
    hub = HubServer('127.0.0.1', 8200)
    hub.start()
