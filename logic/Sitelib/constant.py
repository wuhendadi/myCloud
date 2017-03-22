# -*- coding: utf-8 -*-
#author:ZJW

import struct

BYTESLEN        = 6         #HUB MessageHead Length
UIDLEN          = 8         #UUID Length
PINGDELAY       = 30        #HeartBeat Schedule
CDELAY          = 60        #Relay CallBack Schedule
MESSAGEBUF      = 1024      #Message Buffer Length
DATABUF         = 8192      #Data Length

FORMAT_H        = '!H'
FORMAT_R        = '!Hi'
FORMAT_I        = '!i'
FORMAT_Q        = 'q'
FORMAT_S        = '%ds'
MAGICLEN        = struct.calcsize(FORMAT_H)
LENGTH_Q        = struct.calcsize(FORMAT_Q)
LENGTH_R        = struct.calcsize(FORMAT_R)
LENGTH_I        = struct.calcsize(FORMAT_I)

#----HUB Message -------------------------------------------------
HMCODE          = 0x4669
ONLINE          = 0x0001
OFFLINE         = 0x0003
STATUS          = 0x0005
MESSAGE         = 0x0006
ACCESSPOINTS    = 0x0007
HPING           = 0x0009
PINGACK         = 0x0010
VERIFYTOKEN     = 0x0021
VERIFYTOKENACK  = 0x0022
ACCESSGRANTED   = 0x0024
ACCESSREVOKED   = 0x0026
RELAYPREPARE    = 0x0032
RELAYREADY      = 0x0033
RELAYDISCONNECT = 0x0035
RELAYERROR      = 0x0037
CREATESHORTURL  = 0x0041
SHORTURLACK     = 0x0042
DELETESHORTURL  = 0x0043
NOTIFIACTOON    = 0x0052

TIMEOUT         = 0x5005

#---Relay Message-------------------------------------------------

RMCODE          = 0x4688    #Relay MagicCode  
CONNECT         = 0x0001    #Send To RelayServer
ACCEPT          = 0x0002    #RelayServer Send
REFUSE          = 0x0004    #RelayServer Send
DISCONNECT      = 0x0005    #Send To RelayServer
CLOSE           = 0x0006    #RelayServer Send
RPING           = 0x0007    #Send To RelayServer
RPINGACK        = 0x0008    #Send To RelayServer
RESPONSE        = 0x0011    #Send To RelayServer
REQUEST         = 0x0012    #RelayServer Send
ERROR           = 0x0013    #SendTo RelayServer
STOP            = 0x0014    #RelayServer Send
PAUSE           = 0x0022    #RelayServer Send
RESUME          = 0x0024    #RelayServer Send
CHERRYERROR     = 0x4001    #Send To RelayServer
PINGDICT        = {'Hub':HPING, 'Relay':RPING}
MAGICCODE       = {'Hub':HMCODE, 'Relay':RMCODE}

