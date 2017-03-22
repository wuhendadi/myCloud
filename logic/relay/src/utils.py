# -*- coding: utf-8 -*-

import netaddr
import time
import datetime


def is_valid_ipv4(ip):
    """ ip is int or str """
    return netaddr.IPAddress(ip).version == 4


def is_valid_ipv6(ip):
    """ ip is int or str """
    return netaddr.IPAddress(ip).version == 6


def ip2int(ip_str):
    """ str -> int """
    return netaddr.IPAddress(ip_str).value


def ip2str(ip):
    """ int -> str """
    return str(netaddr.IPAddress(ip))


def addr2str(addr):
    """ The ip of addr is int. """
    return ip2str(addr[0]), addr[1]


def addr2int(addr):
    """ The ip of addr is string. """
    return ip2int(addr[0]), addr[1]


def get_current_timestamp():
    """ -> float timestamp
    """
    return time.mktime(datetime.datetime.now().timetuple())


def get_padding_data(data):
    data_len = len(data)
    if data_len & 0b11:
        return '\x00' * (4 - (data_len & 0b11))
    return ''

if __name__ == '__main__':
    print '-' * 20, 'IPV4 by str'
    ip = netaddr.IPNetwork('192.168.0.0')
    print 'src: ', '192.168.0.0'
    print 'instance str: ', str(ip)
    int_value = ip.value
    print 'int', int_value, type(int_value)
    str_value = str(ip.ip)
    print 'str', str_value, type(str_value)
    print 'int(ip.ip) in hex:', '0x%X' % int(ip.ip), 'length:', len('%x' % int(ip.ip))
    print 'ip.version', ip.version, type(ip.version)

    print '-' * 20, 'IPV4 by int'
    ip = netaddr.IPAddress(0xC0A80000)
    print 'instance str: ', str(ip)
    print 'str', str(ip)
    print 'int', ip.value

    print '-' * 20, 'IPV6 by str'
    ip = netaddr.IPNetwork('2001:0db8:0000:0000:0000:ff00:0042:8329')
    print 'int', ip.value, type(ip.value)

    print '-' * 20, 'IPV6 by int'
    ip = netaddr.IPAddress(42540766411282592856904265327123268393)
    print 'str', str(ip)

    print get_current_timestamp()
