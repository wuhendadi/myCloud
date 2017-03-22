import ConfigParser
import os
import sys
import socket
import traceback
from log import log


def exception_hook(ex_type, value, tb):
    log.d(traceback.format_exception(ex_type, value, tb))
    raise value


class _Config():
    CONFIG_NAME = 'relay.conf'
    SOCKET_RECV_LEN = 2048

    IS_TO_HUB = False
    IS_TO_RELAY_MANAGER = False
    HAS_POPOCLOUD = False

    RELAY_MANAGER_ADDRESS = ''
    RELAY_MANAGER_PORT = 0

    TIMEOUT_TCP_NO_DATE_TRANSFER = 300
    TIMEOUT_TCP_PING = 60

    def __init__(self):
        parent = os.path.dirname(os.path.realpath(__file__))
        config = ConfigParser.ConfigParser()
        config.read(os.path.join(parent, _Config.CONFIG_NAME))
        _Config.IS_TO_HUB = config.getboolean('relay', 'is_to_hub')
        _Config.HAS_POPOCLOUD = config.getboolean('relay', 'has_popocloud')
        _Config.IS_TO_RELAY_MANAGER = config.getboolean('relay', 'is_to_relay_manager')
        log.verbose = config.getboolean('relay', 'verbose')
        _Config.RELAY_MANAGER_ADDRESS = config.get('hub', 'relay_manager_address')
        _Config.RELAY_MANAGER_PORT = config.getint('hub', 'relay_manager_port')

        socket.setdefaulttimeout(120)

    def bind_except_hook(self):
        """ To catch unhandled exception in Box Relay.
        """
        sys.excepthook = exception_hook

config = _Config()
