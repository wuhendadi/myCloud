
import cherrypy
from cherrypy.lib import static
import os
import PopoConfig

class WebServer:
    def contentType(self, suffix):
        if suffix == "html":
             return "text/html"
        elif suffix == "htm":
             return "text/html"
        elif suffix == "xml":
             return "text/xml"
        elif suffix == "css":
            return "text/css"
        elif suffix == "js":
            return "text/javascript"
        elif suffix == "gif":
            return "image/gif"
        elif suffix == "jpg":
            return "image/jpeg"
        elif suffix == "jpeg":
            return "image/jpeg"
        elif suffix == "jpe":
            return "image/jpeg"
        elif suffix == "bmp":
            return "image/x-ms-bmp"
        elif suffix == "png":
            return "image/x-png"
        elif suffix == "ico":
            return "image/x-icon"
        elif suffix == "mp3":
            return "audio/mpeg"
        elif suffix == "mp4":
            return "video/mpeg4"
        elif suffix == "webm":
            return "video/webm"
        elif suffix == "flv":
            return "video/x-flv"
        elif suffix == "avi":
            return "video/avi"
        else:
            return "application/x-download"

    def my_crazy_app(self, environ, start_response):
        path = environ['PATH_INFO']
        port = environ['SERVER_PORT']

        status = '200 OK'
        if port == "1984" :
            fullpath = PopoConfig.Popocloud_path + "/.Elastos/private/"
        else :
            fullpath = PopoConfig.Popocloud_path + "/.Elastos/public/"


        if len(path) == 0 or path == "/" :
            fullpath += "index.html"
            suffix = "html"
            status = '302'
            response_headers = [('Location', './index.html')]
            start_response(status, response_headers)
            return ['']

        index = path.rfind('.')
        if index == -1:
            status = '403 forbidden'
            response_headers = [('Content-type','text/plain')]
            start_response(status, response_headers)
            return ['']
        suffix = path[index+1:]
        fullpath += path

        if os.path.isdir(fullpath):
            status = '403 forbidden'
            response_headers = [('Content-type','text/plain')]
            start_response(status, response_headers)
            return ['']
        elif os.path.exists(fullpath):
            response_headers = [('Content-type', self.contentType(suffix))]
            start_response(status, response_headers)
            return static.serve_file(fullpath, self.contentType(suffix), "inline")
        else:
            status = '404 NotFounds'
            response_headers = [('Content-type','text/plain')]
            start_response(status, response_headers)
            return ['']

