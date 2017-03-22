# -*- coding: utf-8 -*-
#
# 2014 -- Niu Jingyu
#

import os
import sys
import time
from threading import Thread, Event

from Queue import Queue
from urllib2 import urlopen, Request, HTTPError, URLError
import math
import xml.sax
import socket

class ClientConfig(xml.sax.ContentHandler):
    __URL_CLIENT_CONFIG = 'http://www.speedtest.net/speedtest-config.php'

    __TAG_DOCUMENT = 0
    __TAG_SETTINGS = 1
    __TAG_SETTING_ENTRY = 2
    __TAG_LICENSE_KEY = 3
    __TAG_CUSTOMER = 4
    __TAG_IGNORE = 5

    def __init__(self, quiet=True):
        self.context = []
        self.config = {}
        self.quiet = quiet
        self.context.append(ClientConfig.__TAG_DOCUMENT)

        response = urlopen(ClientConfig.__URL_CLIENT_CONFIG)
        xml.sax.parse(response, self, None)
        response.close

    def __getitem__(self,key):
        return self.config[key]

    def startElement(self, name, attrs):
        ctx = self.context[-1]
        if (ctx == ClientConfig.__TAG_DOCUMENT):
            if (name == 'settings'):
                self.context.append(ClientConfig.__TAG_SETTINGS)
        elif (ctx == ClientConfig.__TAG_SETTINGS):
            if (name == 'client' or name == 'server-config'):
                subconfig = {}
                for attr in attrs.getNames():
                    subconfig[attr] = attrs.getValue(attr)
                self.config[name] = subconfig
                self.context.append(ClientConfig.__TAG_SETTING_ENTRY)
            elif (name == 'licensekey'):
                self.context.append(ClientConfig.__TAG_LICENSE_KEY)
            elif (name == 'customer'):
                self.context.append(ClientConfig.__TAG_CUSTOMER)
            else:
                self.context.append(ClientConfig.__TAG_IGNORE)
        else:
            self.context.append(ClientConfig.__TAG_IGNORE)

        if (not self.quiet and self.context[-1] != ClientConfig.__TAG_IGNORE):
            sys.stdout.write('.')
            sys.stdout.flush()

    def endElement(self, name):
        self.context.pop()

    def characters(self, content):
        ctx = self.context[-1]
        if (ctx == ClientConfig.__TAG_LICENSE_KEY):
            self.config['licensekey'] = content
        elif (ctx == ClientConfig.__TAG_CUSTOMER):
            self.config['costomer'] = content

class TestServers(xml.sax.ContentHandler):
    __URL_SERVER_LIST = 'http://www.speedtest.net/speedtest-servers.php'

    __TAG_DOCUMENT = 0
    __TAG_SETTINGS = 1
    __TAG_SERVERS = 2
    __TAG_SERVER = 3
    __TAG_IGNORE = 4

    __MAX_SERVERS = 8

    def __init__(self, clientConfig, full=False, quiet=True):
        self.context = []
        self.__servers = {}
        self.servers = []
        self.clientConfig = clientConfig
        self.quiet = quiet
        self.context.append(TestServers.__TAG_DOCUMENT)

        self.clientLocation = (float(clientConfig['client']['lat']),
                               float(clientConfig['client']['lon']))

        response = urlopen(TestServers.__URL_SERVER_LIST)
        xml.sax.parse(response, self, None)
        response.close

        for key in sorted(self.__servers.keys()):
            for server in self.__servers[key]:
                self.servers.append(server)
                if len(self.servers) == TestServers.__MAX_SERVERS and not full:
                    break
            else:
                continue
            break

        del self.__servers

    def getBestServer(self):
        """Perform a speedtest.net "ping" to determine which speedtest.net
        server has the lowest latency
        """
        # Workaround for ISP priority in China
        ispKeyword = None
        clientISP = self.clientConfig['client']['isp'].lower()
        if clientISP.startswith('china'):
            words = clientISP.split(' ', 2)
            if len(words) > 1:
                ispKeyword = words[1]

        results = {}
        for server in self.servers:
            latencies = []
            url = os.path.dirname(server['url'])
            for i in range(0, 3):
                try:
                    response = urlopen('%s/latency.txt' % url)
                    start = time.time()
                    text = response.read(9)
                    total = time.time() - start
                except (HTTPError, URLError, socket.error):
                    latencies.append(3600)
                    continue

                if int(response.code) == 200 and text == 'test=test'.encode():
                    latencies.append(total)
                else:
                    latencies.append(3600)
                response.close()

            avg = round((sum(latencies) / 3) * 1000000, 3)
            server['latency'] = avg

            ispMagic = 1
            if ispKeyword and ispKeyword in server['sponsor'].lower():
                ispMagic = 0

            key = '%08d%1d%08d' % (avg * 1000, ispMagic, server['distance'] * 1000)
            results[key] = server

            if not self.quiet:
                sys.stdout.write('.')
                sys.stdout.flush()

        fastest = sorted(results.keys())[0]
        best = results[fastest]

        return best

    def getBestServerByDistance(self):
        best = self.servers[0]
        best['latency'] = 'unknown'
        return best

    def distance(self, origin, destination):
        """Determine distance between 2 sets of [lat,lon] in km"""

        latX, lonX = origin
        latY, lonY = destination
        radius = 6371  # km

        dlat = math.radians(latY - latX)
        dlon = math.radians(lonY - lonX)
        a = (math.sin(dlat / 2) * math.sin(dlat / 2) + math.cos(math.radians(latX))
             * math.cos(math.radians(latY)) * math.sin(dlon / 2)
             * math.sin(dlon / 2))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        d = radius * c

        return d

    def startElement(self, name, attrs):
        ctx = self.context[-1]
        if (ctx == TestServers.__TAG_DOCUMENT):
            if (name == 'settings'):
                self.context.append(TestServers.__TAG_SETTINGS)
        elif (ctx == TestServers.__TAG_SETTINGS):
            if (name == 'servers'):
                self.context.append(TestServers.__TAG_SERVERS)
        elif (ctx == TestServers.__TAG_SERVERS):
            if (name == 'server'):
                server = {}
                for attr in attrs.getNames():
                    server[attr] = attrs.getValue(attr)

                serverLocation = (float(server['lat']), float(server['lon']))
                d = self.distance(self.clientLocation, serverLocation)
                server['distance'] = d
                if d not in self.__servers:
                    self.__servers[d] = [server]
                else:
                    self.__servers[d].append(server)
                self.context.append(TestServers.__TAG_SERVER)

                if (not self.quiet and len(self.__servers) % 120 == 0):
                    sys.stdout.write('.')
                    sys.stdout.flush()
        else:
            self.context.append(TestServers.__TAG_IGNORE)

    def endElement(self, name):
        self.context.pop()

class SpeedTest:
    MAX_TEST_TIME = 10

    def __init__(self, testServer, quiet=True):
        self.testServer = testServer
        self.quiet = quiet
        self.cancelEvent = Event()

    class FileDownloader(Thread):
        """Thread class for retrieving a URL"""

        def __init__(self, baseTime, url, cancelEvent=None, quiet=True):
            self.baseTime = baseTime
            self.url = url
            self.cancelEvent = cancelEvent
            self.quiet = quiet
            self.bytes = 0
            self.startTime = 0
            self.finishTime = 0
            Thread.__init__(self)

        def run(self):
            try:
                self.startTime = time.time()
                if (self.startTime - self.baseTime) > SpeedTest.MAX_TEST_TIME:
                    if not self.quiet and not self.cancelEvent.isSet():
                        sys.stdout.write('x')
                        sys.stdout.flush()
                    return

                f = urlopen(self.url)
                while True and not self.cancelEvent.isSet():
                    l = len(f.read(8192))
                    if l == 0:
                        break
                    self.bytes += l
                f.close()
                self.finishTime = time.time()

                if not self.quiet and not self.cancelEvent.isSet():
                    sys.stdout.write('.')
                    sys.stdout.flush()
            except IOError:
                self.bytes = 0
                self.startTime = 0
                self.finishTime = 0

    class FileUploader(Thread):
        """Thread class for putting a URL"""

        class DummyFile(object):
            CHARS = 'content1=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'

            def __init__(self, size):
                self.length = size
                self.pos = 0;

            def read(self, n):
                if self.pos >= self.length:
                    return None

                if n is None or n < 0 or self.pos + n > self.length:
                    n = self.length - self.pos

                chars = SpeedTest.FileUploader.DummyFile.CHARS
                result = bytearray()
                while n > 0:
                    if self.pos < 45:
                        start = self.pos
                        l = n if (n <= (45 - start)) else (45 - start)
                        result.extend(chars[start:start+l])
                        self.pos += l
                        n -= l
                    else:
                        start = (self.pos - 45) % 36
                        l = n if (n <= (36 - start)) else (36 - start)
                        result.extend(chars[start+9:start+9+l])
                        self.pos += l
                        n -= l

                return result

        def __init__(self, baseTime, case, cancelEvent=None, quiet=True):
            self.baseTime = baseTime
            self.url = case[0]
            self.cancelEvent = cancelEvent
            self.quiet = quiet
            self.bytes = 0
            self.startTime = 0
            self.finishTime = 0

            size = case[1]
            self.data = SpeedTest.FileUploader.DummyFile(size)

            Thread.__init__(self)

        def run(self):
            try:
                headers = {'Content-length':'%d' % self.data.length}
                request = Request(self.url, self.data, headers)

                self.startTime = time.time()
                if (self.startTime - self.baseTime) > SpeedTest.MAX_TEST_TIME:
                    if not self.quiet and not self.cancelEvent.isSet():
                        sys.stdout.write('x')
                        sys.stdout.flush()
                    return

                if not self.cancelEvent.isSet():
                    f = urlopen(request, self.data)
                    f.read(11)
                    f.close()
                    self.bytes = self.data.length

                self.finishTime = time.time()

                if not self.quiet and not self.cancelEvent.isSet():
                    sys.stdout.write('.')
                    sys.stdout.flush()
            except IOError:
                self.bytes = 0
                self.startTime = 0
                self.finishTime = 0

    def testSpeed(self, testThread, cases):
        """Function to launch test threads and calculate upload/download speeds"""
        totalCases = len(cases)
        finishedBytes = []
        startTime = []
        finishTime = []
        jobs = Queue(6) # Job queue, max 6 concurrent jobs

        baseTime = time.time()

        def testLauncher(q, cases):
            for case in cases:
                thread = testThread(baseTime, case, self.cancelEvent, self.quiet)
                thread.start()
                q.put(thread, True)

        def resultConsumer(q, totalCases):
            while len(finishedBytes) < totalCases:
                thread = q.get(True)
                while thread.isAlive():
                    thread.join(timeout=0.1)
                finishedBytes.append(thread.bytes)
                if thread.finishTime != 0:
                    startTime.append(thread.startTime)
                    finishTime.append(thread.finishTime)
                del thread

        launcher = Thread(target=testLauncher, args=(jobs, cases))
        consumer = Thread(target=resultConsumer, args=(jobs, len(cases)))
        launcher.start()
        consumer.start()

        while launcher.isAlive():
            launcher.join(timeout=0.1)
        while consumer.isAlive():
            consumer.join(timeout=0.1)

        del launcher
        del consumer

        if self.cancelEvent.isSet():
            return 0

        return (sum(finishedBytes) / (max(finishTime)-min(startTime)))

    def downloadSpeed(self):
        if self.cancelEvent.isSet():
            return 0

        sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
        cases = []
        for size in sizes:
            for i in range(0, 4):
                cases.append('%s/random%sx%s.jpg' %
                             (os.path.dirname(self.testServer['url']), size, size))

        return self.testSpeed(SpeedTest.FileDownloader, cases)

    def uploadSpeed(self):
        if self.cancelEvent.isSet():
            return 0

        sizesizes = [int(.25 * 1000 * 1000), int(.5 * 1000 * 1000)]
        cases = []
        for size in sizesizes:
            for i in range(0, 25):
                cases.append((self.testServer['url'], size))

        return self.testSpeed(SpeedTest.FileUploader, cases)

    def cancel(self):
        self.cancelEvent.set()


def get_speeds():
    """ -> download, upload """
    try:
        cc = ClientConfig(quiet=True)
        servers = TestServers(cc, quiet=True)
        testServer = servers.getBestServer()
        speedtest = SpeedTest(testServer, quiet=True)
        dlspeed = speedtest.downloadSpeed()
        ulspeed = speedtest.uploadSpeed()
        return dlspeed, ulspeed
    except Exception:
        return 0, 0


'''
Command line interface for testing bandwidth using speedtest.net.
'''
if __name__ == '__main__':

    import signal

    sys.stdout.write('Retrieving speedtest.net client configuration ')
    sys.stdout.flush()

    cc = ClientConfig(quiet=False)

    sys.stdout.write(' Ok\n')
    sys.stdout.flush()

    sys.stdout.write('Retrieving speedtest.net server list ')
    sys.stdout.flush()

    servers = TestServers(cc, quiet=False)

    sys.stdout.write(' Ok\n')
    sys.stdout.flush()

    sys.stdout.write('Getting best server by latency ')
    sys.stdout.flush()

    testServer = servers.getBestServer()
    #testServer = servers.getBestServerByDistance()

    sys.stdout.write(' Ok\n')
    sys.stdout.flush()

    sys.stdout.write('Testing from %(isp)s (%(ip)s)\n' % cc['client'])
    sys.stdout.flush()

    sys.stdout.write(('Test server hosted by %(sponsor)s (%(name)s) [%(distance)0.2f km] : '
                     '%(latency)s ms\n' % testServer).encode('utf-8', 'ignore'))
    sys.stdout.flush()

    speedtest = SpeedTest(testServer, quiet=False)

    def ctrl_c(signum, frame):
        """Catch Ctrl-C key sequence"""
        speedtest.cancel()
        raise SystemExit('\nCancelling...')

    signal.signal(signal.SIGINT, ctrl_c)

    sys.stdout.write('Testing download speed ')
    sys.stdout.flush()

    dlspeed = speedtest.downloadSpeed()

    sys.stdout.write(' %0.2f Mbits/s\n' % ((dlspeed / 1000 / 1000) * 8))
    sys.stdout.flush()

    sys.stdout.write('Testing upload speed ')
    sys.stdout.flush()

    ulspeed = speedtest.uploadSpeed()

    sys.stdout.write(' %0.2f Mbits/s\n' % ((ulspeed / 1000 / 1000) * 8))
    sys.stdout.flush()
