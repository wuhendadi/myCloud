# -*- coding: utf-8 -*-

import struct
import uuid
import socket
import binascii

# ip = socket.gethostbyname(socket.gethostname())
ip = '127.0.0.1'
ADDRESS = (ip, 8500)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(ADDRESS)
print 'TURN peer started in', ADDRESS
while True:
    data, addr = sock.recvfrom(2048)
    print 'RECV:', data, addr
    data = 'Data from peer'
    sock.sendto(data, addr)
    print 'SEND:', data, addr
