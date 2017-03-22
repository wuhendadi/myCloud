
import urlparse
import httplib
import cherrypy

__all__ = ["proxyPass"]

class ReverseProxy(object):
    class Request(object):
        __slots__ = ['headers', 'method', 'scheme', 'netloc', 'path',
                     'query', 'url', 'contentLength', 'contentType', 'data']

        def __init__(self):
            self.headers = {}
            self.method = None
            self.scheme = None
            self.netloc = None
            self.path = None
            self.query = None
            self.url = None
            self.contentLength = 0
            self.contentType = None
            self.data = None      

    class Response(object):
        __slots__ = ['connection', 'realResponse', 'status', 'headers']
        
        def __init__(self, connection):
            self.connection = connection
            self.realResponse = connection.getresponse()
            self.status = str(self.realResponse.status)
            self.headers = self.realResponse.getheaders()
            
        def close(self):
            if self.realResponse:
                self.realResponse.close()
                self.realResponse = None

            if self.connection:
                self.connection.close()
                self.connection = None
                
        def __iter__(self):
            return self
        
        def next(self):
            data = self.realResponse.read(4096)
            if data == '':
                raise StopIteration
            else:
                return data
                    
    def __init__(self, script, serverURL, rewriteHost = False):
        self.mountPoint = script
        
        s = urlparse.urlparse(serverURL)
        self.serverSchema = s.scheme
        self.serverNetloc = s.netloc
        self.serverPath = s.path
        
        self.rewriteHost = rewriteHost
        
    def parseRequest(self, environ):
        request = ReverseProxy.Request()

        # Parse headers
        for h in environ:
            if h.startswith('HTTP_'):
                # Just for special case
                if (h == 'HTTP_CONTENT_MD5'):
                    request.headers['Content-MD5'] = environ['HTTP_CONTENT_MD5']
                elif (h == 'HTTP_ETAG'):
                    request.headers['ETag'] = environ['HTTP_ETAG']
                elif (h == 'HTTP_TE'):
                    request.headers['TE'] = environ['HTTP_TE']
                elif (h == 'HTTP_WWW_AUTHENTICATE'):
                    request.headers['WWW-Authenticate'] = environ['HTTP_WWW_AUTHENTICATE']
                else:
                    # Here is the common case   
                    hparts = h[5:].split('_') 
                    hparts = [p.capitalize() for p in hparts]
                    hname = '-'.join(hparts)
                    request.headers[hname] = environ[h]

        # Remote-Addr is stored without "HTTP_" prefix
        #request.headers['Remote-Addr'] = environ['REMOTE_ADDR']
 
        # Content-Type and Content-Length are stored differently, without "HTTP_"
        # (cf. CherryPy WSGIServer source code or WSGI specs)
        request.contentType = environ.get('CONTENT_TYPE', None)
        if request.contentType:
            request.headers['Content-Type'] = request.contentType
        request.contentLength = environ.get('CONTENT_LENGTH', None)
        if request.contentLength:
            request.headers['Content-Length'] = request.contentLength 
            request.data = environ['wsgi.input']

        request.method = environ['REQUEST_METHOD']     # GET, POST, HEAD, etc
        request.scheme = environ['wsgi.url_scheme']    # http/https
        request.netloc = environ['SERVER_NAME']        # www.server.com[:80]
        request.path   = environ['PATH_INFO']          # /folder/index.html
        request.query  = environ['QUERY_STRING']
        # URL=/path?query used when forwarding directly to the server
        request.url = urlparse.urlunsplit(('', '', request.path, request.query, ''))
        
        if self.rewriteHost:
            request.headers["Host"] = self.serverNetloc
    
        return request

    def doRequest(self, request):
        connection = httplib.HTTPConnection(self.serverNetloc)
        connection.request(request.method, request.url, request.data, request.headers)
        return ReverseProxy.Response(connection)

    def __call__(self, environ, start_response):
        request = self.parseRequest(environ)
        response = self.doRequest(request)        
        start_response(response.status, response.headers)
        return response

def proxyPass(path, serverURL, rewriteHost = False):
    proxy = ReverseProxy(path, serverURL, rewriteHost)
    cherrypy.tree.graft(proxy, path)
