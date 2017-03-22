__author__ = 'Fred'

# For run in console.
import os
import sys
parent = os.path.dirname(os.path.realpath(__file__))
parent = os.path.dirname(parent)
sys.path.append(os.path.join(parent, 'src'))

import time
from relay import RelayServer

if __name__ == '__main__':
    relay = RelayServer(None)
    relay.start()
    time.sleep(1)
    relay.stop()
