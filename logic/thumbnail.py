# -*- coding: utf-8 -*-
import os
import gc
import md5
import json
import shutil
import UtilFunc
import ProfileFunc
import Log
from PopoConfig import filters,MaxWidth, MaxHeight, MinWidth, MinHeight,MaxLength,Lock_path,BigImage,MinImage,Hardware,CreateThumbNail
from PIL import Image, ExifTags

if Hardware == "1.0":
    NEED_AKJPEG = True
else:
    NEED_AKJPEG = False

if NEED_AKJPEG:
    import akjpeg

_pilInited = False
_imgFormats = None
_imgTypes = None
def _initPIL():
    global _pilInited,_imgFormats,_imgTypes
    if _pilInited:
        return

    if NEED_AKJPEG:
        akjpeg.hw_init()

    Image.preinit()
    _imgFormats = Image.EXTENSION
    Image.register_mime("BMP","image/bmp")
    Image.register_mime("PPM","image/x-portable-pixmap")
    _imgTypes = {}
    for key,val in _imgFormats.iteritems():
        _imgTypes[key] = Image.MIME[val]
    _pilInited = True

def getImageFormats():
    _initPIL()
    global _imgFormats
    return _imgFormats

def getImageTypes():
    _initPIL()
    global _imgTypes
    return _imgTypes

def _formatImageSize(x, y, width, height):
    if cmp(width, height) * cmp(x, y) < 0: x, y = y, x
    return min(float(width)/x, float(height)/y)    

def _getRatioLength(x, y, isLarge):
    if isLarge: 
        size = [MaxWidth, MaxHeight]
    else:
        size = [MinWidth, MinHeight]
    if y > x > size[0]: y = max(y * size[0] / x, 1); x = size[0]
    elif x > y > size[1]: x = max(x * size[1] / y, 1); y = size[1]
    else: x, y = size[0], size[1]
    
    return x, y 
    
def _getOrientation(img):
    try:
        exif=dict((ExifTags.TAGS[k], v) for k, v in img._getexif().iteritems() if k in ExifTags.TAGS)
        if exif and exif.has_key('Orientation'):
            return exif['Orientation']
    except:
        pass

    return 0
        
def _formatOrientation(img, Orientation):
    if Orientation == 3 : 
        img=img.rotate(180, expand=True)
    elif Orientation == 6 : 
        img=img.rotate(270, expand=True)
    elif Orientation == 8 : 
        img=img.rotate(90, expand=True)
    return img

def _getSavePath(savePath, name):
    #Get Thumbnail Temp Path
    try:
        newPath = os.path.join(savePath, 'ThumbImage', name[:2])
        if not os.path.exists(newPath):
            os.makedirs(newPath)
            
        return os.path.join(newPath, name).replace("\\", "/")
    except Exception, e:
        Log.exception("MakeDir Exception: [%s]"%e)
        return None
    
def _makeImageFile(imagepath, tempThumbImage, width, height, isLarge = False):
    new_width, new_height = _getRatioLength(width, height, isLarge)
    flag_file = os.path.join(Lock_path,os.path.basename(imagepath))
    if NEED_AKJPEG and UtilFunc.getFileExt(imagepath) == 'jpg':
        if not os.path.exists(flag_file):
            file(flag_file, "wb").close()
            ret = akjpeg.make_thumbnail(imagepath, os.path.dirname(tempThumbImage),
                        os.path.basename(tempThumbImage), new_width, new_height)
            if ret == 0:
                if os.path.exists(flag_file): os.remove(flag_file)
                return
    if os.path.exists(flag_file): os.remove(flag_file)
    img = Image.open(imagepath)
    x,y = img.size
    Orientation = _getOrientation(img)
    if img.mode != 'RGB': img = img.convert("RGB")
    quality = 100
    if isLarge:
        if isLarge > MinImage: quality = 40
    elif min(x,y) < MinWidth:
        if x < MinWidth: box = (0,(y-MinHeight)/2, x, (y-MinHeight)/2+MinHeight)
        elif y < MinHeight: box = ((x-MinWidth)/2, 0, (x-MinWidth)/2+MinWidth, y)
        img = img.crop(box)
    else:
        img.thumbnail((new_width, new_height), Image.ANTIALIAS)
         
    img = _formatOrientation(img, Orientation)
    img.save(tempThumbImage, getImageFormats()['.jpg'],quality=quality)
        
    del img
    
def getThumbNailImage(filePath, size=MinWidth):
    filePath = unicode(filePath.replace('\\','/'))
    if not os.path.exists(filePath):return (None,None)
    savePath = os.path.join(UtilFunc.getDiskPath(filePath,True),'.popoCloud')
    if UtilFunc.matchFilter(os.path.basename(filePath), filters['picture']):
        fileType = 'picture'
        name = UtilFunc.getMd5Name(filePath, size, size)
    elif UtilFunc.matchFilter(os.path.basename(filePath), filters['video']):
        fileType = 'video'
        (folder, filename) = os.path.split(filePath)
        name = UtilFunc.getMd5Name(filePath, size, size)
    else:
        return (None,None)
        
    ext = os.path.splitext(filePath)[1].lower()
    folder = os.path.join(savePath, 'ThumbImage', name[:2]).replace("\\", "/")
    tempThumbImage = os.path.join(folder, name).replace("\\", "/")

    if not os.path.exists(tempThumbImage) and CreateThumbNail:
        if not os.path.exists(folder): os.mkdir(folder)
        _makeImageFile(filePath, tempThumbImage, size, size, size > MinWidth)
    return (tempThumbImage, ext)      
    
def getOrCreateThumb(filePath, savePath, fileType):
    if not filePath or not savePath or not os.path.exists(filePath): return None
    if fileType == 'video' and CreateThumbNail:
        (folder, filename) = os.path.split(filePath)
        image_path = os.path.join(folder, '.tmp_' + md5.md5(repr(filename)).hexdigest() + '.bmp')
        if UtilFunc.isLinuxSystem() and Hardware != '1.0':
            try:
                from Sitelib import libandroidmod
                if not os.path.exists(image_path):
                    libandroidmod.create_video_thumbnails(filePath, image_path, 1)
            except Exception, e:
                Log.exception("Create VideoThumbNail Failed! Reason[%s]"%e)
    else:
        image_path = filePath.replace('\\', '/')
        
    minImage = _getSavePath(savePath, UtilFunc.getMd5Name(filePath.replace('\\', '/'), MinWidth, MinHeight))
    maxImage = _getSavePath(savePath, UtilFunc.getMd5Name(filePath.replace('\\', '/'), MaxWidth, MaxHeight))
    minhash, maxhash = os.path.basename(minImage), os.path.basename(maxImage)

    if not os.path.exists(minImage) and CreateThumbNail:
        if os.path.exists(image_path):    
            try:
                _initPIL()
                statInfo = os.stat(filePath)
                img = Image.open(image_path)
                x, y = img.size
                if ((x > MaxLength or y > MaxLength) or statInfo.st_size >= BigImage) and Hardware == "1.0":
                    minhash, maxhash = 0, 0
                else:
                    if x > MinWidth or y > MinHeight:
                        createThumbNailImage(image_path, minImage, img, maxImage, statInfo.st_size)
                    else:
                        shutil.copy(image_path,minImage)
                        shutil.copy(image_path,maxImage)
                        del img
                    
            except Exception, e:
                Log.error('GreateThumbNail Failed [%s]. Reason[%s]'%(filePath, e))
                if os.path.exists(minImage): os.remove(minImage)
                elif os.path.exists(maxImage): os.remove(maxImage)
                minhash, maxhash = 0, 0
            if fileType == 'video': os.remove(image_path)
        else:
            minhash, maxhash = 0, 0
        
    gc.collect()
    #if not ProfileFunc.isMediaFolder(filePath): return
    remarks = {'thumbnail-small':minhash,'thumbnail-large':maxhash}
    if fileType == 'video':
        for (k,v) in UtilFunc.getVideoInfo(filePath).iteritems():
            remarks[k] = v
    ProfileFunc.insertToSubLibrary(savePath, fileType, filePath, json.dumps(remarks))       

def createThumbNailImage(src_path, minImage, img, maxImage, st_size):
    nametemp = None
    if img.mode != 'RGB' and img.mode != 'RGBA':
        img = img.convert("RGB")
    if UtilFunc.getFileExt(src_path) != 'jpg':
        nametemp = minImage + "_tempfile.jpg"
        img.save(nametemp, getImageFormats()['.jpg'], quality=100)
        imagepath = nametemp
    else:
        imagepath = src_path
    x, y = img.size
    del img
    _makeImageFile(imagepath, minImage, x, y)
    ratio = _formatImageSize(x, y, MaxWidth, MaxHeight)
    if ratio < 1:
        _makeImageFile(imagepath, maxImage, x, y, st_size)
    else: 
        shutil.copy(imagepath,maxImage)
        
    if nametemp and os.path.exists(nametemp):
        os.remove(nametemp)

