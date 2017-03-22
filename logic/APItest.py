# -*- coding: utf-8 -*-

import os
import types
import time
import urllib
import urllib2
import httplib
import json
import socket
import urlparse
import requests

def postFile(url, file): 
    headers = {}
    r = requests.post(url, open(file, 'rb'),headers=headers)
    print r
    
def postRangeFile(url, file):
    (parent,filename) = os.path.split(file)
    file_data = open(file,'r')
    length = os.stat(file).st_size
    urlparts = urlparse.urlsplit(url)
    h = None
    try:
        h = httplib.HTTPConnection(urlparts[1])
        h.putrequest('PUT', urlparts[2])
        h.putheader('Connection','keep-alive')
        h.putheader('content-type', "application/octet-stream")
        h.putheader('content-range', 'bytes 58-2048/%s'%str(length))
        h.putheader('content-length', str(2048-58))
        h.endheaders()
        file_data.seek(58)
        data = file_data.read(2048-58)
        print data
        h.send(data)
 
    except Exception, e:
        print "PostRelayFile Failed! Reason[%s]"%e
         
    print "send.....respone"
    if h: h.close()


def testWalk(folder):
    ret = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            path = os.path.join(root, file)
            ret.append(file)
   
        for folder in dirs:
            path = os.path.join(root, folder)
            ret.append(folder)
    
    
def testListDir(folder, ret= None):
    if not ret: ret = []
    st = time.time()
    for file in os.listdir(folder):
        path = os.path.join(folder, file)
        if os.path.isdir(path):
            testListDir(path, ret)
        ret.append(path)
        
def testV(folder):
    st = time.time()
    testWalk(folder)
    print time.time() - st
    st = time.time()
    testListDir(folder)
    print time.time() - st         

def postChunked(url, file):
    #download_zipfolder    
    urlparts = urlparse.urlsplit(url)
    file = open(file)
    length = os.stat(file).st_size
    try:
        h = httplib.HTTPConnection(urlparts[1])
        h.putrequest('PUT', urlparts[2])
        h.putheader('content-type', "application/octet-stream")
        h.putheader('Content-Disposition', 'attachment;filename=%s'%data_list[1])
        h.putheader('Transfer-Encoding', 'chunked')
        h.endheaders()
        file.seek(start)
        length = 0
        while True :
            chunk_data = file.read(8192)
            length = len(chunk_data)
            if length > 0:
                send_data = hex(length)[2:] + CRLF + chunk_data + CRLF
            else:
                send_data = "0" + CRLF + CRLF
         
            h.send(send_data)
            if length <= 0:
                break
             
    except Exception, e:
        print "Download ZipStream Failed! Reason:[%s]"%e
  
    print "send.....respone"
    if h: h.close()

def request(url, args=None, method='POST'):
    if args:
        if method.lower() in ['get', 'delete']:
            for key in args.keys():
                if isinstance(args[key],types.ListType) or isinstance(args[key],types.DictType):
                    args[key] = json.dumps(args[key])
            body = urllib.urlencode(args)
            url += '?' + body
        else:
            body = json.dumps(args)
    else: body = ''
    print body
    #token = base64.encodestring('e51db183-effa-40ea-ab17-0284631c7e7c:ba7b1d54-ee67-415a-9d09-b2dfdb913671').replace('\n','')
    headers = {#"Content-type": "application/json", 
               "Content-type": "application/x-www-form-urlencoded",
               'Content-Length':str(len(body)),
               "Accept": "application/json",
               #'Authorization': 'Token %s'%token
               #'Authorization': 'Token ZTUxZGIxODMtZWZmYS00MGVhLWFiMTctMDI4NDYzMWM3ZTdjOjU3ZGJkMmJhLTUwZDEtNGJhZC04ZjdkLTQ0YzJiMWU5Y2MyZA=='
               }
    
    startTime = time.time()
    conn = httplib.HTTPConnection('172.16.20.186',443)
    #conn = httplib.HTTPConnection('192.168.1.100',8880)
    #conn = httplib.HTTPConnection('8862226855110090.boxrelay-test.paopaoyun.com', 25008)
    conn.request(method, url, body, headers)
    r = conn.getresponse()
    print r.status
    print r.msg.headers
    print time.time() - startTime
    print r.read()
    
def sslTest():
    import ssl, socket
    from OpenSSL.crypto import load_pkcs12
    certfile = os.path.join(os.path.dirname(__file__),'csclient.p12')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    p12 = load_pkcs12(file(keyfile, 'rb').read(), 'elastos')
    cert = p12.get_certificate()
    key = p12.get_privatekey()
    try:
        conn = ssl.wrap_socket(sock, certfile=certfile, ssl_version=ssl.PROTOCOL_TLSv1 ,cert_reqs=ssl.CERT_REQUIRED,ca_certs=certfile)
        conn.connect(('192.168.5.37', 18080))
    except Exception, e:
        pass
    
def broadcastTest():
    host=''  
    port=10000  
    s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)  
    s.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)  
    s.setsockopt(socket.SOL_SOCKET,socket.SO_BROADCAST,1)  
    s.bind((host,port))  
    while 1:  
        try:  
            data,addr=s.recvfrom(1024)  
            print "got data from",addr  
            s.sendto("8880",addr)  
            print data  
        except KeyboardInterrupt:  
            raise  
        
def printChapter(chapter):
    # The element ID is the unique key for this chapter
    print("== Chapter '%s'" % chapter.element_id)
    # TIT2 sub frame
    print("-- Title:", chapter.title)
    # TIT3 sub frame
    print("-- subtitle:", chapter.subtitle)
    # WXXX sub frame
    print("-- url:", chapter.user_url)
    # Start and end time - tuple
    print("-- Start time: %d; End time: %d" % chapter.times)
    # Start and end offset - tuple. None is used to set to "no offset"
    print("-- Start offset: %s; End offset: %s" %
          tuple((str(o) for o in chapter.offsets)))
    print("-- Sub frames:", str(list(chapter.sub_frames.keys())))

def testmp3():
    import eyed3
    audiofile = eyed3.load(u"d:/Better Together.mp3")
    #audiofile = eyed3.load(u"d:/showme.mp3")
    tag = audiofile.tag
    
    print tag.title.encode('latin1').decode('gbk') 
    print tag.album.encode('latin1').decode('gbk')
    print tag.artist.encode('latin1').decode('gbk')
    print tag.album_artist
    print tag.publisher
    print tag.publisher_url
    print tag.genre.name
    print tag.recording_date   
    
    
#     from tagger import *
#     id3 = ID3v2("d:/showme.mp3")
#     if not id3.tag_exists():
#         return "No ID3 Tag Found"
#          
#     apicfid = 'APIC'
#     if id3.version == 2.2:
#         apicfid = 'PIC'
#          
#     for frame in id3.frames:
#         if frame.strings:
#             print frame.strings[0].decode('gbk')
#         else:
#             print frame.strings
        
if __name__ == "__main__":
#    a = [{'cameraId':'000115','factoryinfo':'0','hardware':'1.5.3','version':'2.4'}]
#    a = json.dumps(a)
#    post({'cameras':a},'/Camera/Search')
#    postFile('http://10.0.0.109:8880/api/files/mnt/disk1/part1/Better Together.mp3','d:/Better Together.mp3')
#    postFile('http://127.0.0.1:8880/api/files/DTLite4491-0356.exe','C:\Users\Sunny Zhao\Downloads\BaiduPinyinSetup_2.14.2.14.1420594510.exe')
#    postChunked('http://10.0.0.118:8880/api/files?path=d:/burntool_v5.0.24.zip','d:/burntool_v5.0.24.zip')
#    request('/api/batch',{'action':'delete','files':['/mnt/disk1/part1/TDDOWNLOAD','/mnt/disk1/part1/10_00.jpg']},'POST')
#    request('/api/search',{'term':'3'},'POST')
#    request('/api/search/picture',{'offset':0,'limit':10,'term':'5'},'POST')
#    request('/api/search/1159b219-ecc2-4d05-b885-593ce6748cd8',{},'DELETE')
#    request('/api/files?intent=props',{'path':'C:/Users/Sunny Zhao/Pictures/03.jpg','name':'0433.jpg'},'PUT')
#    request('/api/batch',{'action':'copy','files':['/mnt/disk1/part1/09_59.jpg'],'target':'/mnt/disk1/part1/1'},'POST')
#    request('/api/batch',{'action':'move','files':['/mnt/disk1/part1/mp01.jpg'],'target':'/mnt/disk1/part1/1','onExist':'skip'},'POST')
#    postRangeFile('http://10.0.0.90:8880/api/files/mnt/disk1/part1/burntool_v5.0.24.zip','d:/burntool_v5.0.24.zip')
#    request('/api/version',{},'GET')
#    request('/api/storages',{},'DELETE')
#    request('/api/files/mnt/disk1/part4/哈哈哈',{'intent':'props','name':'source'},'PUT')
#    request('/api/files/mnt/disk1/part1/908898',{'intent':'newFile','size':102400},'POST')
#    request('/api/files/908898.rar',{'intent':'newFile','size':102400},'POST')
#    request('/api/system',{'intent':'relay','value':False},'PUT')
#    request('/api/photos',{'mode':'path','photos':'89uioj9uojlk'},'POST')
#    request('/api/photos/tags',{'photos':["/mnt/disk1/part1/source/07.png","/mnt/disk1/part1/source/08.png"],'tags':[]},'PUT')
#    request('/api/photos/tags?tags=["8jh"]',{},'DELETE')
#    request('/api/photos/tags',{'action':'add', 'photos':["/mnt/disk1/part1/source/07.png","/mnt/disk1/part1/source/08.png"],'tags':['还杀U盾博威合金','8jh']},'PUT')
#    request('/api/photos/tags/mnt/disk1/part1/07.png',{'tags':['合金']},'PUT')
#    request('/api/photos/tags',{'photos':["C:/Users/Sunny Zhao/Pictures/愚人码头.mp3"]},'PUT')
#    request('/api/share/mnt/disk1/part1/06-chiang_ying_jung-wild-tosk.mp3',{'private':True,'validity':10},'POST')
#    request('/api/share',{'shortUrls':['12Ly9kiH32ZFqcr']},'DELETE')
#    request('/api/share',{'path':'/mnt/disk1/part1/20140731_185628.jpg','isPrivate':True},'POST')
#    request('/api/share?shortUrls=["Ty3plkB4fbB0MFN"]',{},'DELETE')
#    request('/api/share',{'path':'d:/mnt/disk1/part1','isPrivate':True},'POST')
#    request('/api/share/131063734a45420f8bb87cb010fbc6aa?extractionCode=2546', {},'GET')
#    request('/api/files',{'path':'d:/popoCloud','intent':'traversal'},'POST')
#    request('/api/files/1c04fbc7-17cc-4943-84fe-f0a369480280?intent=traversal',{},'DELETE')
#    request('/api/files/89797',{'intent':'newFolder'},'POST')
#    request('/api/files/mnt/disk1/part1/1',{},'DELETE')
#    postFile('http://127.0.0.1:8880/api/backup','d:/35.copy')
#    request('/api/files/d/mnt/disk1/part1/sdfsd/456.png',{},'DELETE')
#    request('/api/system',{'paths':['d:/html5'], 'intent':'setScanFolder'},'POST')
#    request('/api/favor',{'imagePaths':['/mnt/disk1/part1/IMG_20131203_135224.jpg'],'intent':'set','name':'独一份'},'POST')
#    request('/api/netsurf',{'intent':'status','value':False},'PUT') 
#    request('/api/shadowsocks',{'intent':'status','value':'False'},'PUT')
#    request('/api/photos',{'intent':'search','key':'qq'},'POST') 
#    request('/api/photos/thumbnail', {'thumbnailIds':['29b5596aa58ebe3b9c2d602b8d5989ad']},'POST')
#    request('/api/photos/thumbnail/29b5596aa58ebe3b9c2d602b8d5989ad', {},'GET')
#    request('/api/photos/date', {'dates':['2015-01','2015-04']},'DELETE')
#    request('/api/photos/date', {},'DELETE')
#    request('/api/app/CameraCtrl',{'intent':'add'},'POST') 
#    request('/api/app/PubCloudStorage',{'intent':'add'},'POST') 
#    request('/api/storages',{},'GET')
#    request('/api/storages/B4FE-5315/mediaFolders',{'folders':[],'except':[u'/mnt/disk1/part4/upgrade','/mnt/disk2/part4/新建文件夹']},'POST')
#    request('/api/storages/B4FE-5315/mediaFolders',{'folders':[{'folder':u'/mnt/disk1/part1','type':'all'}],'except':[]},'POST')
#    request('/api/music/albums/老男孩',{},'GET')
#    request('/api/music/info',{'paths':["D:/mnt/disk1/part1/新建文件夹/Better Together.mp3"]},'POST')
#    request('/api/music/folders/mnt/disk1/part1/source/新建文件夹',{},'GET')
#    request('/api/video/info',{'paths':['D:/mnt/disk1/part1/sdfsd/济公1.rmvb']},'POST')
#    request('/api/camera/add',{'camera':{'deviceId':'000015','type':'1','ip':'10.0.0.104'}},'PUT')
#    request('/api/camera/snapshot/1',{'quality':100},'POST')
#    request('/api/camera/1',{},'DELETE')
#    request('/api/camera/motionDetect/1',{'enable':1,'sensitive':99},'PUT')
#    request('/api/camera/alarminfo',{'alarminfo':['111111111111111']},'PUT')
#    sslTest()
#    broadcastTest()
#    testmp3()
#    testV('d:/')
    cont = {'INPUT_DATA':'<Operation><Details><parameter><name>requesttemplate</name><value>Request a CRM account</value></parameter><parameter><name>technician</name><value>Howard Stern</value></parameter><parameter><name>level</name><value>Tier 3</value></parameter><resources><resource><title>System Requirements</title><parameter><name>Choose the desktop model</name><value>Dell</value></parameter><parameter><name>Choose the devices required</name><value>iPhone</value><value>Blackberry</value></parameter></resource><resource><title>Additional Requirements</title><parameter><name>Choose the additional hardware required</name><value>Optical Mouse</value></parameter></resource></resources><parameter><name>editor</name><value>administrator</value></parameter><parameter><name>serviceapprovers</name><value>administrator</value><value>guest</value></parameter><!--Common Additional Field--><parameter><name>Employee ID</name><value>0217</value></parameter><!--Service Category Specific Additional Field --><parameter><name>RAM Size</name><value>8 GB</value></parameter></Details></Operation>'}
    cont = urllib.urlencode(cont)
    request('/sdpapi/request?OPERATION_NAME=ADD_REQUEST&TECHNICIAN_KEY=D165CD3F-DBE3-4D33-AB8E-A4FA7CF01EAC&' + cont, {}, "POST")



