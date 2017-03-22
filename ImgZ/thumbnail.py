# -*- coding: utf-8 -*-
import os
import gc
from PIL import Image, ExifTags

MinWidth = MinHeight = 130
MaxWidth = MaxHeight = 1024


_pilInited = False
_imgFormats = None
_imgTypes = None

def _initPIL():
    global _pilInited,_imgFormats,_imgTypes
    if _pilInited:
        return

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
        exif=dict((ExifTags.TAGS[k], v) for k, v in img._getexif().items() if k in ExifTags.TAGS)
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
    img = Image.open(imagepath)
    x,y = img.size
    Orientation = _getOrientation(img)
    if min(x,y) < MinWidth:
        if x < MinWidth: box = (0,(y-MinHeight)/2, x, (y-MinHeight)/2+MinHeight)
        elif y < MinHeight: box = ((x-MinWidth)/2, 0, (x-MinWidth)/2+MinWidth, y)
        img = img.crop(box)
    else:
        img.thumbnail((new_width, new_height), Image.ANTIALIAS)
         
    img = _formatOrientation(img, Orientation)
    img.save(tempThumbImage, getImageFormats()['.jpg'])
        
    del img      
    
def getOrCreateThumb(filePath, savePath, fileType=None):
    if not filePath or not savePath or not os.path.exists(filePath): return None
    image_path = filePath.replace('\\', '/')
        
    minImage = savePath

    if not os.path.exists(minImage):
        if os.path.exists(image_path):    
            try:
                _initPIL()
                statInfo = os.stat(filePath)
                img = Image.open(image_path)
                createThumbNailImage(image_path, minImage, img, statInfo.st_size)
                    
            except Exception, e:
                print 'GreateThumbNail Failed [%s]. Reason[%s]'%(filePath, e)
                if os.path.exists(minImage): os.remove(minImage)
            if fileType == 'video': os.remove(image_path)
        
    gc.collect() 

def createThumbNailImage(src_path, minImage, img, st_size):
    nametemp = None
    imagepath = src_path
    x, y = img.size
    del img
    _makeImageFile(imagepath, minImage, x, y)

if __name__ == '__main__':
    #getOrCreateThumb('D:/filebase/static/img/arrow.png','D:/filebase/static/img/001.png')
	tmp_path = "D:/filebase/static/img"
	for file in os.listdir(tmp_path):
		getOrCreateThumb(os.path.join(tmp_path, file),os.path.join(tmp_path, 'tmp_' + file))
