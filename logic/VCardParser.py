# -*- coding: utf-8 -*-
import os
import UtilFunc
import re
import Log

TEL         = 'TEL'
SERVER      = 'X-SERVER'
RELATED     = 'X-RELATED'
DATE        = 'DATE'
EMAIL       = 'EMAIL'
URL         = 'URL'
IM          = 'X-IM'
ADR         = 'ADR'

def vcf_parser(filePath=None):
    ''' parser a vcf. '''
    if not filePath or not os.path.exists(filePath):
        return None
    
    #read vcf file
    try:
        fp = open(filePath, 'rb')
        lines = fp.readlines()
    except Exception, e:
        Log.error('Open vcf file failed!!! reason[%s]'%e)
        return None

    vcfList=[]
    for line in lines:
        line = line.strip('\r\n')
        if line.startswith('BEGIN:VCARD'):
            vcf_dict                = {}
            tel_dict                = {}
            email_dict              = {}
            url_dict                = {}
            date_dict               = {}
            server_dict             = {}
            related_dict            = {}
            im_dict                 = {}
            adr_dict                = {}
            tel_dict[TEL]           = []
            email_dict[EMAIL]       = []
            url_dict[URL]           = []
            server_dict[SERVER]     = []
            related_dict[RELATED]   = []
            date_dict[DATE]         = []
            im_dict[IM]             = []
            adr_dict[ADR]           = []
            continue
        elif line.startswith('END:VCARD'):
            if im_dict[IM]:
                vcf_dict.update(im_dict)
            if url_dict[URL]:
                vcf_dict.update(url_dict)
            if email_dict[EMAIL]:
                vcf_dict.update(email_dict)
            if date_dict[DATE]:
                vcf_dict.update(date_dict)
            if server_dict[SERVER]:
                vcf_dict.update(server_dict)
            if related_dict[RELATED]:
                vcf_dict.update(related_dict)
            if tel_dict[TEL]:
                vcf_dict.update(tel_dict)
            if adr_dict[ADR]:
                vcf_dict.update(adr_dict)
            vcfList.append(vcf_dict)
            continue
        elif line.startswith('N:'):
            N_dict = item_parser(line)
            vcf_dict.update(N_dict)
        elif line.startswith('FN:'):
            FN_dict = item_parser(line)
            vcf_dict.update(FN_dict)
        elif line.startswith('NICKNAME:'):
            nickName = item_parser(line)
            vcf_dict.update(nickName)
        elif line.startswith('X-GROUP:'):
            group_dict = item_parser(line)
            vcf_dict.update(group_dict)
        elif line.startswith('ORG:'):
            ORG_Dict = item_parser(line)
            vcf_dict.update(ORG_Dict)
        elif line.startswith('TITLE:'):
            title_dict = item_parser(line)
            vcf_dict.update(title_dict)
        elif line.startswith('X-PHONETIC-FIRST-NAME:'):
            first_dict = item_parser(line)
            vcf_dict.update(first_dict)
        elif line.startswith('X-PHONETIC-LAST-NAME:'):
            last_dict = item_parser(line)
            vcf_dict.update(last_dict)
        elif line.startswith('TEL;'):
            (tel, value) = type_parser(line)
            tel_dict[tel].append(value)
        elif line.startswith('EMAIL;'):
            (email, value) = type_parser(line)
            email_dict[email].append(value)
        elif line.startswith('URL;'):
            (url, value) = type_parser(line)
            url_dict[url].append(value)
        elif line.startswith('ADR;'):
            value = adr_parser(line)
            adr_dict[ADR].append(value)
        elif line.startswith('BDAY:'):
            bday_dict = item_parser(line)
            vcf_dict.update(bday_dict)
        elif line.startswith('DATE;'):
            (server, value) = type_parser(line)
            date_dict[server].append(value)
        elif line.startswith('X-IM;'):
            _dict = IM_parser(line)
            im_dict[IM].append(_dict)
        elif line.startswith('X-SERVER;'):
            (server, value) = type_parser(line)
            server_dict[server].append(value)
        elif line.startswith('X-RELATED;'):
            (related, value) = type_parser(line)
            related_dict[related].append(value)
        elif line.startswith('NOTE:'):
            note_dict = item_parser(line)
            vcf_dict.update(note_dict)
        elif line.startswith('X-ANDROID-CUSTOM:'):
            custom_dict = item_parser(line)
            vcf_dict.update(custom_dict)
        else:
            continue
        
    return vcfList
    
def item_parser(line=None):
    if not line:
        return None
    _dict = {}
    if re.match(r'([A-Z-]*):(.*)', line):
        (key, value) = line.split(':', 1)
        _dict[key] = value
    else:
        return None
    return _dict

def items_parser(line=None, split=None, key_list=[]):
    ''' parser Name. '''
    if not line:
        return None
    (type, str) = line.split(split)
    _list = str.split(';')
    list_len = len(_list)
    _dict = {}
    for index in range(list_len):
        _dict[key_list[index].encode('utf-8')] = _list[index]
    return _dict    

def type_parser(line=None):
    ''' parser TYPE item. '''
    if not line:
        return None, None
    item_dict = {}
    if re.match(r'([A-Z-]*);([A-Z]*)=(.*):(.*)', line):
        (groupName, type_str) = line.split(';', 1)
        (type, name_str) = type_str.split('=', 1)
        (key, value) = name_str.split(':', 1)
        item_dict[key] = value
    else:
        return None, None
    return groupName, item_dict
    
def adr_parser(line=None):
    ''' parser ADR. '''
    if not line:
        return None
    _dict = {}
    if re.match(r'ADR;TYPE=(.*)', line):
        (adr, adr_str) = line.split(';', 1)
        (type, type_str) = adr_str.split('=', 1)
        (key, value) = type_str.split(':', 1)
        _dict[key]= value
    else:
        return None
    return _dict

def IM_parser(line=None):
    ''' parser X-IM. '''
    if not line:
        return None
    _dict = {}
    if re.match(r'X-IM;SERVICE=([A-Z]*);TYPE=([A-Z]*):(\w*)', line):
        (im, srv_str, type_str) = line.split(';', 2)
        (srvKey, srvValue) = srv_str.split('=', 1)
        _dict[srvKey] = srvValue
        (type, home_str) = type_str.split('=', 1)
        (homeKey, homeValue) = home_str.split(':', 1)
        _dict[homeKey] = homeValue
    elif re.match(r'X-IM;SERVICE=([A-Z]*):(\w*)', line):
        (im_name, _dict) = type_parser(line)
    else:
        return None
    return _dict

def getCount(path):
    if not os.path.exists(path):
        return False
    count = 0
    try:
        fp = open(path, 'r')
        while True:
            line = fp.readline()
            if not line:
                break
            if re.match('BEGIN:VCARD', line.strip()):
                count += 1
        fp.close()
        return count
    except Exception,e:
        Log.error("getContactCount Failed! Reason [%s]"%e)
        if fp:
            fp.close()
        return False

if __name__ == '__main__':
#    path = u'D:/vcf/3.vcf'
#    vcflist = vcf_parser(path)
#    print len(vcflist)
#    print vcflist
    pass
        