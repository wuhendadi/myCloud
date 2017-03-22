# -*- coding: utf-8 -*-

import os
import wx
#import re
#import json
#import urllib
#import md5
import thread
import time
import UtilFunc
import PopoConfig
#import ProfileFunc
import cherrypy
#import StartFunc
#import HTMLParser
#import uuid
#import unicodedata
import webbrowser
from TPControls import BGPanel
#from wx._core import ITEM_CHECK
from LoginDialog import parent_dir 
from SetPreference import ShowSettings
from LoginDialog import setting 

'''
try:
    from agw import buttonpanel as bp
except ImportError: # if it's not there locally, try the wxPython lib.
    import wx.lib.agw.buttonpanel as bp
'''
# import ButtonPanel as bp
# #import Images
# from TPControls import DCStaticText
# 
# from TPControls import TPStaticBitmap
# from TPControls import TPStaticText
# from TPControls import TPButton
# from TPControls import TPBitmapButton
# from TPControls import ShowOKMessage
# from TPControls import ShowOKCancelMessage
# from TPControls import GetShortString
# from TPControls import _get_hz_string_width
# 
# try:
#     from agw import hyperlink as hl
# except ImportError: # if it's not there locally, try the wxPython lib.
#     import wx.lib.agw.hyperlink as hl
    
# default_dict = {"picture":'*.png;*.gif;*.bmp;*.jpg',
#                 "music":"*.mv;*.ogg;*.wav;*.mp3",
#                 "video":"*.rm;*.avi;*.mp4;*.mpeg"}
# default_type = ["picture", "music", "video"]
# 
# #--------------------------------------------------------------
# def GetWord(dc, text, width):
#     if not text:
#         return u'', u''
# 
#     lenght = len(text)
#     if lenght < 1:
#         return u'', u''
#     elif lenght == 1:
#         return text[0], u''
# 
#     char = text[0]
#     if char == u' ' or char == u'/' or char == u'\\' or char >= u'\u00ff':
#         return char, text[1:]
# 
#     word = char
#     i = 1
#     char = text[i]
#     while char != u' ' and char != u'/' and char != u'\\' and char < u'\u00ff':
#         textWidth, textHeight = dc.GetTextExtent(word + char)
#         if textWidth >= width or (i + 1) >= lenght:
#             return word, text[i:]
# 
#         word += char
#         i += 1
#         char = text[i]
# 
#     return word, text[i:]
# 
# def GetWrapText(dc, text, width):
# #    text = u" wordword word汉wordwordwordwordwordwordwordwordwordwordwordwordwordwordword wordword wordword wordword "
# #    strlist = str.split('\')
#     textWidth, textHeight = dc.GetTextExtent(text)
#     ret = u''
#     word = u''
#     line = 0
#     while  textWidth > width:
#         i = 0
#         wrap = u''
#         textWidth = 0
#         while textWidth < width:
#             wrap += word
#             word, text = GetWord(dc, text, width)
#             textWidth, textHeight = dc.GetTextExtent(wrap + word)
#         ret += wrap + u"\n"
#         line += 1
#         textWidth, textHeight = dc.GetTextExtent(word + text)
#     ret += word + text
#     line += 1
#     height = line * textHeight + 5
#     return ret, height
# 
# def changeChar(text):
#     ret = u''
#     for char in text:
#         if char == u'&':
#             ret += u'&&'
#         else:
#             ret += char
# 
#     return ret
# 
# def unescape_word(s):
#     html_parser = HTMLParser.HTMLParser()
#     result = html_parser.unescape(s)
#     return result
# 
# 
# def get_mac_address():
#     #get computer MAC_ADDRESS
#     node = uuid.getnode()
#     mac = uuid.UUID(int = node).hex[-12:]
#     return mac
#  
# def getPicFilter(dlg, type = "picture"):
#     pic_filter = []
#     for i in xrange(4):
#         if dlg.check_list[i].IsChecked():
#             pic_filter.append(default_dict[type].split(";")[i])
#     return ";".join(pic_filter)
# 
# #-----------------------------------------------------------
# 
# class ResourceNameEditDialog(wx.Dialog):
#     def __init__(
#             self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition,
#             style=wx.DEFAULT_DIALOG_STYLE,
#             useMetal=False,
#             name="My Floder"
#             ):
# 
#         pre = wx.PreDialog()
#         pre.Create(parent, ID, title, pos, size, style)
# 
#         # This next step is the most important, it turns this Python
#         # object into the real wrapper of the dialog (instead of pre)
#         # as far as the wxPython extension is concerned.
#         self.PostCreate(pre)
# 
#         sizer = wx.BoxSizer(wx.VERTICAL)
#         box = wx.BoxSizer(wx.HORIZONTAL)
# 
#         label = wx.StaticText(self, -1, u"请输入设备名:")
#         box.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         self.txtName = wx.TextCtrl(self, -1, unescape_word(name), size=(130,-1))
#         box.Add(self.txtName, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
#         line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
#         sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)
# 
#         btnsizer = wx.StdDialogButtonSizer()
# 
#         if wx.Platform != "__WXMSW__":
#             btn = wx.ContextHelpButton(self)
#             btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_OK, u"确定")
#         btn.SetDefault()
#         btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_CANCEL, u"取消")
#         btnsizer.AddButton(btn)
#         btnsizer.Realize()
# 
#         sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         self.SetSizer(sizer)
#         sizer.Fit(self)
# 
# class DevicesItemPanel(wx.Window):
#     def __init__(self, parent, dlg, pos, type=1, online = "false", name = "device", id = "deviceId", version="2.0", address="0000000000"):
#         wx.Window.__init__(self, parent, -1, pos, size=(640, 120))
# 
#         self.accountPanel=dlg
#         
#         imgPath =os.path.join(UtilFunc.module_path(), u'res/account_computer_bg.png')
#         bgpng = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         bg = wx.StaticBitmap(self, -1, bgpng, pos=(25, -1))
#         self.name = name
# 
#         if UtilFunc.isWindowsSystem():
#             bgParent = bg
#         else:
#             bgParent = self
#         
#         admin = ""
#         self.type = type
#         self.address = address
#         self.version = version    
#         if type < 10:
#             if online == 'false':
#                 imgPath =os.path.join(UtilFunc.module_path(), u'res/computer_outline.png')
#             else:
#                 if address == get_mac_address():
#                     admin = u"本机"  
#                 imgPath =os.path.join(UtilFunc.module_path(), u'res/computer_online.png')
#         else:
#             if online == 'false':
#                 imgPath =os.path.join(UtilFunc.module_path(), u'res/equment_outline.png')
#             else:
#                 imgPath =os.path.join(UtilFunc.module_path(), u'res/equment_online.png')
#         
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.StaticBitmap(bgParent, -1, img, pos=(24, 23))
# 
#         if isinstance(name, unicode):
#             name = GetShortString(name, 10)
#         else:
#             name = GetShortString(name, 19)
#             
#         label = wx.StaticText(bgParent, -1, unescape_word(name), (80, 40))
#         label.SetForegroundColour(wx.BLACK)
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
#         label.SetBackgroundColour((0xE9, 0xE9, 0xE9))
#         self.lblName = label
#         self.resId = id
# 
#         btn = TPButton(bgParent, -1, u"[编辑]", (221, 37))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         btn.SetTextForeground((0x00, 0x55, 0xF9))
#         self.Bind(wx.EVT_BUTTON, self.onEdit, btn)
# 
#         wx.StaticText(bgParent, -1, u"版本号：" + version, (400, 40)).SetBackgroundColour((0xE9, 0xE9, 0xE9))
# 
#         self.sign = wx.StaticText(bgParent, -1, admin, (530, 40)).SetBackgroundColour((0000, 0xE9, 0000))
# 
#     def onEdit(self, evt):
#         dlg = ResourceNameEditDialog(self, -1, u"修改设备名", size=(350, 200),name = self.name)
#         dlg.CenterOnScreen()
# 
#         curResourceId = self.resId
#         if dlg.ShowModal() == wx.ID_OK:
#             resourceName = dlg.txtName.GetValue()
#             resourceName = resourceName.strip()
#             _resourceName = urllib.quote(resourceName.encode("utf8"))
#             
#             resNameLen = len(_resourceName)
#             if not resourceName :
#                 ShowOKMessage(self, u'请输入设备名')
#                 return
# 
#             unicodeStr = unicode(resourceName)
#             for ch in unicodeStr:
#                 unicodeNum = ord(ch)
#                 if unicodeNum < 0xff1c and unicodeNum > 0xff0f:
#                     continue
#                 if unicodeNum == 0x00b7 or unicodeNum == 0x2014 or unicodeNum == 0x2018 or unicodeNum == 0x2019 or unicodeNum == 0x201c or unicodeNum == 0x201d or unicodeNum == 0x2026 or unicodeNum == 0x3001 or unicodeNum == 0x3002 or unicodeNum == 0x3010 or unicodeNum == 0x300a or unicodeNum == 0x300b or unicodeNum == 0x3011 or unicodeNum == 0xff01 or unicodeNum == 0xff08 or unicodeNum == 0xff09 or unicodeNum == 0xff0c or unicodeNum == 0xff1f or unicodeNum == 0xffe5 or unicodeNum == 0xff0b or unicodeNum == 0xff1d or unicodeNum == 0xff0d or unicodeNum == 0xff3c or unicodeNum == 0xff5e or unicodeNum == 0xff5b or unicodeNum == 0xff5d or unicodeNum == 0xff20 or unicodeNum == 0xff03 or unicodeNum == 0xff05 or unicodeNum == 0x00d7 or unicodeNum == 0xff5c:
#                     continue
#                 if unicodeNum < 0x4e00 and unicodeNum > 0x007f:
#                     ShowOKMessage(self, u'请不要输入特殊符号')
#                     return
#                 if unicodeNum > 0x9fa5 or unicodeNum == 0x0026 or unicodeNum == 0x005c:
#                     ShowOKMessage(self, u'请不要输入特殊符号')
#                     return
# 
#             length = _get_hz_string_width(resourceName)
#             if length < 1 or length >20:
#                 ShowOKMessage(self, u'设备名长度不符合要求，请输入1~20位的设备名!')
#                 return
# 
#             querystring = "/account/renameResource?email=" + ProfileFunc.getUser() + "&password=" + ProfileFunc.getPassword() + "&resourceId=" + str(curResourceId) + "&nickName=" + _resourceName
#             responeData = UtilFunc.QueryServer(querystring)
# 
#             if responeData['result'] != 0 :
#                 if responeData['result'] == 9:
#                      ShowOKMessage(self, u"密码已在别处被修改， 请重新登入！")
#                      self.accountPanel.parent.frame.ShowLoginDlg(ProfileFunc.getUser())
#                      self.accountPanel.parent.Destroy()
#                 else:
#                     ShowOKMessage(self, responeData['message'])
#                 return
#             else:
#                 if isinstance(resourceName, unicode):
#                     if length == resNameLen:
#                         name = GetShortString(resourceName, 19)
#                     else:
#                         name = GetShortString(resourceName, 10)
#                 else:
#                     name = GetShortString(resourceName, 19)
#                 self.lblName.SetLabel(name)
#                 self.name = resourceName
# 
#         dlg.Destroy()
# 
# class AccountInfoPanel(wx.Window):
#     def __init__(self, parent, accountPanel, dlg, pos, nickName='-',):
#         wx.Window.__init__(self, parent, -1, pos, size=(640, 91))
#         self.SetBackgroundColour(wx.WHITE)
# 
#         self.dlg = dlg
#         self.parent = parent
# 
#         self.nickName=nickName
#         self.account = accountPanel
# 
#         label = wx.StaticText(self, -1, u"帐户:", (35, 25))
#         label.SetForegroundColour(wx.BLACK)
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
#         user = ProfileFunc.getUser()
#         user = GetShortString(user, 50)
#         label = wx.StaticText(self, -1, user, (75, 25))
#         label.SetForegroundColour((0x3E, 0x3E, 0x3E))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"Arial")
#         label.SetFont(font)
# 
#         label = wx.StaticText(self, -1, u"昵称:", (35, 61))
#         label.SetForegroundColour(wx.BLACK)
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
#         lblName = wx.StaticText(self, -1, self.nickName, (75, 61))
#         lblName.SetForegroundColour((0x94, 0x94, 0x94))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         lblName.SetFont(font)
#         self.lblName = lblName
# 
#         width, height = self.lblName.GetClientSize()
# 
#         btnModify = TPButton(self, -1, u"[编辑]", pos=(width + 65, 57))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btnModify.SetFont(font)
#         btnModify.SetTextForeground((0x00, 0x55, 0xF9))
#         self.Bind(wx.EVT_BUTTON, self.ModifyNickname, btnModify)
#         self.btnModify=btnModify
# 
# 
#         btn = TPButton(self, -1, u"修改密码", pos=(480, 22))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         btn.SetTextForeground((0x00, 0x55, 0xF9))
#         self.Bind(wx.EVT_BUTTON, self.ModifyPassword, btn)
# 
#         self.showUpdateInfoed = False
#         self.ShowUpdateInfo()
# 
#         btn = TPButton(self, -1, u"注销设备", pos=(541, 21))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         btn.SetTextForeground((0x00, 0x55, 0xF9))
#         self.Bind(wx.EVT_BUTTON, self.OnQuit, btn)
# 
#         line = wx.StaticLine(self, -1, pos=(25, 89), size=(578, -1), style=wx.LI_HORIZONTAL)
# 
#     def ShowUpdateInfo(self):
#         if not self.showUpdateInfoed and self.dlg.frame.hasUpdatePacket:
#             label = wx.StaticText(self, -1, u"检测软件有更新，", (447, 61))
#             label.SetForegroundColour(wx.BLACK)
#             font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#             label.SetFont(font)
# 
#             btn = TPButton(self, -1, u"立即升级", pos=(541, 57))
#             font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#             btn.SetFont(font)
#             btn.SetTextForeground((0x00, 0x55, 0xF9))
#             self.Bind(wx.EVT_BUTTON, self.OnUpdate, btn)
#             self.showUpdateInfo = True
# 
#     def ModifyNickname(self, evt):
#         if not self.account.modifynicknamePanel:
#             self.account.modifynicknamePanel = ModifyNicknamePanel(self.account, nickName=self.nickName)
#         else:
#             self.account.modifynicknamePanel.Show()
# 
#         if self.account.devicePanel:
#             self.account.devicePanel.Hide()
#         if self.account.modifypasswordPanel:
#             self.account.modifypasswordPanel.Hide()
# 
#     def ModifyPassword(self, evt):
#         if not self.account.modifypasswordPanel:
#             self.account.modifypasswordPanel = ModifyPasswordPanel(self.account, nickName=self.nickName)
#         else:
#             self.account.modifypasswordPanel.Show()
# 
#         if self.account.devicePanel:
#             self.account.devicePanel.Hide()
#         if self.account.modifynicknamePanel:
#             self.account.modifynicknamePanel.Hide()
# 
#     def OnUpdate(self, evt):
#         self.dlg.frame.Update(True)
# 
#     def OnQuit(self, evt):
#         if ShowOKCancelMessage(self, u"\r\n此操作将取消帐号与设备的关联，并清除此帐号的所有设置。\r\n\r\n确认要注销吗？\r\n") == wx.ID_CANCEL :
#             return
#         
#         errMsg = StartFunc.UnbindResource(ProfileFunc.getUser(), ProfileFunc.getPassword(), UtilFunc.getSN())
#         if errMsg:
#             ShowOKMessage(self, u"退出帐号失败:" + errMsg)
#             
#         StartFunc.stopConnect()
#         
#         self.dlg.Hide()
#         self.dlg.frame.ShowLoginDlg()
# 
# class ModifyNicknamePanel(wx.Panel):
#     def __init__(self, parent, nickName):
#         wx.Panel.__init__(self, parent, -1, pos=(0, 0), size=(640,320))
#         self.SetBackgroundColour(wx.WHITE)
# 
#         self.accountPanel = parent
# 
#         self.nickName = nickName
# 
#         self.info = AccountInfoPanel(self, parent, parent.parent, pos=(0, 0), nickName=self.nickName)
# 
#         self.nicknameLabel = wx.TextCtrl(self, -1, "", (256, 161), size=(183,28))
# 
#         label = wx.StaticText(self, -1, u"编辑昵称", (323, 123))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"微软官方雅黑字体")
#         label.SetFont(font)
# 
#         label = wx.StaticText(self, -1, u"昵称:", (221, 167))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
# 
#         btn = wx.Button(self, -1, u"确定", pos=(257, 206))
#         btn.SetForegroundColour((0x31, 0x31, 0x31))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         self.Bind(wx.EVT_BUTTON, self.OnModify, btn)
# 
#         btn = wx.Button(self, -1, u"取消", pos=(366, 206))
#         btn.SetForegroundColour((0x31, 0x31, 0x31))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         self.Bind(wx.EVT_BUTTON, self.OnCancel, btn)
# 
#     def OnCancel(self, evt):
#         self.accountPanel.devicePanel.Show()
#         self.Destroy()
# 
#     def OnModify(self, evt):
#         nickname = self.nicknameLabel.GetValue()
#         nickname = nickname.strip()
#         _nickname = urllib.quote(nickname.encode("utf8"))
# 
#         if not nickname :
#             ShowOKMessage(self, u'请输入昵称')
#             return
# 
#         unicodeStr = unicode(nickname)
#         for ch in unicodeStr:
#             unicodeNum = ord(ch)
#             if unicodeNum < 0xff1c and unicodeNum > 0xff0f:
#                 continue
#             if unicodeNum == 0x00b7 or unicodeNum == 0x2014 or unicodeNum == 0x2018 or unicodeNum == 0x2019 or unicodeNum == 0x201c or unicodeNum == 0x201d or unicodeNum == 0x2026 or unicodeNum == 0x3001 or unicodeNum == 0x3002 or unicodeNum == 0x3010 or unicodeNum == 0x300a or unicodeNum == 0x300b or unicodeNum == 0x3011 or unicodeNum == 0xff01 or unicodeNum == 0xff08 or unicodeNum == 0xff09 or unicodeNum == 0xff0c or unicodeNum == 0xff1f or unicodeNum == 0xffe5 or unicodeNum == 0xff0b or unicodeNum == 0xff1d or unicodeNum == 0xff0d or unicodeNum == 0xff3c or unicodeNum == 0xff5e or unicodeNum == 0xff5b or unicodeNum == 0xff5d or unicodeNum == 0xff20 or unicodeNum == 0xff03 or unicodeNum == 0xff05 or unicodeNum == 0x00d7 or unicodeNum == 0xff5c:
#                 continue
#             if unicodeNum < 0x4e00 and unicodeNum > 0x007f:
#                 ShowOKMessage(self, u'请不要输入特殊符号')
#                 return
#             if unicodeNum > 0x9fa5 or unicodeNum == 0x0026 or unicodeNum == 0x005c:
#                 ShowOKMessage(self, u'请不要输入特殊符号')
#                 return
# 
#         length = _get_hz_string_width(nickname)
#         if length < 1 or length >20:
#             ShowOKMessage(self, u'昵称长度不符合要求，请输入1~20位的昵称!')
#             return
# 
#         self.accountPanel.frame.tbIcon.nickName = nickname
#         self.info.lblName.SetLabel(nickname)
#         self.accountPanel.devicePanel.info.nickName = nickname
#         self.accountPanel.devicePanel.info.lblName.SetLabel(nickname)
# 
#         width, height = self.accountPanel.devicePanel.info.lblName.GetClientSize()
# 
#         self.accountPanel.devicePanel.info.btnModify.MoveXY(x=width + 65, y=57)
#         self.info.btnModify.MoveXY(x=width + 65, y=57)
# 
#         querystring = "/account/modifyName?email=" + ProfileFunc.getUser() + "&password=" + ProfileFunc.getPassword() + "&name=" + _nickname
#         responeData = UtilFunc.QueryServer(querystring)
# 
#         if responeData['result'] != 0 :
#             if responeData['result'] == 9:
#                  ShowOKMessage(self, u"密码已在别处被修改， 请重新登入！")
#                  self.accountPanel.parent.frame.ShowLoginDlg(ProfileFunc.getUser())
#                  self.accountPanel.parent.Destroy()
#             else:
#                 ShowOKMessage(self, responeData['message'])
#             return
#         else:
#             ShowOKMessage(self, u"昵称已修改")
# 
#         self.accountPanel.devicePanel.Show()
#         self.accountPanel.devicePanel.Refresh()
#         self.Destroy()
# 
# class ModifyPasswordPanel(wx.Panel):
#     def __init__(self, parent, nickName):
#         wx.Panel.__init__(self, parent, -1, pos=(0, 0), size=(640,320))
#         self.SetBackgroundColour(wx.WHITE)
# 
#         self.accountPanel = parent
# 
#         self.nickName=nickName
# 
#         self.info = AccountInfoPanel(self, parent, parent.parent, pos=(0, 0), nickName=self.nickName)
# 
#         label = wx.StaticText(self, -1, u"修改密码", (322, 124))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"微软官方雅黑字体")
#         label.SetFont(font)
# 
#         label = wx.StaticText(self, -1, u"旧密码:", (213, 159))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
#         self.opassword = wx.TextCtrl(self, -1, "", (259, 152), size=(183,28), style=wx.TE_PASSWORD)
# 
#         label = wx.StaticText(self, -1, u"新密码:", (212, 199))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
#         self.npassword = wx.TextCtrl(self, -1, "", (259, 191), size=(183,28), style=wx.TE_PASSWORD)
# 
#         label = wx.StaticText(self, -1, u"确认密码:", (200, 239))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
#         self.rpassword = wx.TextCtrl(self, -1, "", (259, 230), size=(183,28), style=wx.TE_PASSWORD)
# 
#         btn = wx.Button(self, -1, u"确定", pos=(259, 271))
#         btn.SetForegroundColour((0x31, 0x31, 0x31))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         self.Bind(wx.EVT_BUTTON, self.OnModify, btn)
# 
#         btn = wx.Button(self, -1, u"取消", pos=(367, 271))
#         btn.SetForegroundColour((0x31, 0x31, 0x31))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         self.Bind(wx.EVT_BUTTON, self.OnCancel, btn)
# 
#     def OnCancel(self, evt):
#         self.accountPanel.devicePanel.Show()
#         self.Destroy()
# 
#     def OnModify(self, evt):
#         opassword = self.opassword.GetValue()
#         npassword = self.npassword.GetValue()
#         repassword = self.rpassword.GetValue()
# 
#         if not opassword :
#             ShowOKMessage(self, u'请输入旧密码!')
#             return
# 
#         if not npassword:
#             ShowOKMessage(self, u'请输入新密码!')
#             return
# 
#         if not repassword:
#             ShowOKMessage(self, u'请输入确认密码!')
#             return
# 
#         if npassword != repassword:
#             ShowOKMessage(self, u'请确认输入的密码匹配!')
#             return
# 
#         if opassword == npassword:
#             ShowOKMessage(self, u'新旧密码不能相同!')
#             return
# 
#         length = len(npassword)
#         if length < 6 or length >16:
#             ShowOKMessage(self, u'密码长度不符合要求，请输入6~16位的密码!')
#             return
# 
#         regex = "\W|\_"
#         if re.search(regex, npassword):
#             ShowOKMessage(self, u'密码只能由数字和字母组成， 请重新填写!')
#             return
# 
#         opassword = md5.md5(opassword).hexdigest().lower()
#         npassword = md5.md5(npassword).hexdigest().lower()
# 
#         if opassword != ProfileFunc.getPassword():
#             ShowOKMessage(self, u'旧密码输入错误!')
#             return
# 
#         querystring = "/account/modifyPassword?email=" + ProfileFunc.getUser() + "&password="  + opassword + "&newPassword=" + npassword
#         responeData = UtilFunc.QueryServer(querystring)
#         if responeData['result'] != 0 :
#             if responeData['result'] == 9:
#                  ShowOKMessage(self, u"密码已在别处被修改， 请重新登入！")
#                  self.accountPanel.parent.frame.ShowLoginDlg(ProfileFunc.getUser())
#                  self.accountPanel.parent.Destroy()
#             else:
#                 ShowOKMessage(self, responeData['message'])
#             return
#         else:
#             ret = self.accountPanel.frame.fileservice.CreateUser(ProfileFunc.getUser(), npassword, ProfileFunc.getResource(), ProfileFunc.getResourceId())
#             ret = json.loads(ret)
#             if ret['result'] != 0 :
#                 ShowOKMessage(self, ret['errMsg'])
#                 return
#             ShowOKMessage(self, u"密码已修改")
#             
#         self.accountPanel.devicePanel.Show()
#         self.accountPanel.devicePanel.Refresh()
#         self.Destroy()
# 
# class AccountDevicesPanel(wx.ScrolledWindow):
#     def __init__(self, parent):
#         wx.ScrolledWindow.__init__(self, parent, -1, pos=(0, 0), size=(640,325))
#         self.SetBackgroundColour(wx.WHITE)
#         self.SetScrollbars(1, 1, 1, 306)
#         self.SetVirtualSize((640, 320))
# 
#         self.accountPanel=parent
# 
#         self.info = AccountInfoPanel(self, parent, parent.parent, pos=(0, 0))
# 
#         label = wx.StaticText(self, -1, u"设备:", (35, 100))
#         label.SetForegroundColour(wx.BLACK)
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
#         btn = TPButton(self, -1, u"刷新", pos=(543, 100))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         btn.SetFont(font)
#         btn.SetTextForeground((0x00, 0x55, 0xF9))
#         self.Bind(wx.EVT_BUTTON, self.showList, btn)
# 
#         self.items = []
#         self.count = 0
#         self.retErr = 0
#         self.showList()
# 
#     def showList(self, evt=None):
#         querystring = "/accounts/list?username=" + ProfileFunc.getUser() + "&password=" + ProfileFunc.getPassword() \
#                        + "&resourceName=" + ProfileFunc.getResource()
#         responeData = UtilFunc.QueryServer(querystring)
#         if responeData['result'] != 0 :
#             if responeData['result'] != self.retErr:
#                 self.retErr = responeData['result']
#                 if responeData['result'] == 9:
#                     ShowOKMessage(self, u"密码已在别处被修改， 请重新登入！")
#                     self.accountPanel.parent.frame.ShowLoginDlg(ProfileFunc.getUser())
#                     self.accountPanel.parent.Destroy()
#                 else:
#                     ShowOKMessage(self, responeData['message'])
#             #return
#         
#         self.setAccountPanel(responeData)
# 
# 
#     def setAccountPanel(self, responeData):
#         onLine_flag = True
#         if responeData.has_key('data'):
#             list = responeData['data']
#             for item in self.items:
#                 item.Destroy()
#             self.items = []
#             self.nickName = unescape_word(responeData['name'])
#             if not self.nickName or self.nickName == "":
#                  self.nickName = '-'
#                  self.accountPanel.frame.tbIcon.nickName = ProfileFunc.getUser()
#             else:
#                  self.accountPanel.frame.tbIcon.nickName = self.nickName
#     
#             self.info.nickName = self.nickName
#             self.info.lblName.SetLabel(self.nickName)
#             sortList = []
#             pcOnLineList = []
#             pcOffLineList = []
#             boxOffLineList = []
#             boxOnLineList = []
#             selfMac = get_mac_address()
# 
#             for item in list:
#                 if item['type'] == 1:
#                     if item['name'] == selfMac:
#                         sortList.append(item) #本机
#                     else:
#                         if item['online'] == 'true':
#                             pcOnLineList.append(item) #pc online
#                         else:
#                             pcOffLineList.append(item) #pc offline
#                 else:
#                     if item['online'] == 'true':
#                         boxOnLineList.append(item) #box online
#                     else:
#                         boxOffLineList.append(item) #box offline   
# 
#             list = sortList + pcOnLineList + boxOnLineList + pcOffLineList + boxOffLineList
#             del sortList
#             del pcOnLineList
#             del boxOnLineList
#             del pcOffLineList
#             del boxOffLineList       
#         else:
#             list = self.items
#             if not list:
#                 return 
#             onLine_flag = False
#              
#         width, height = self.info.lblName.GetClientSize()
#         self.info.btnModify.MoveXY(x=width + 65, y=57)
#         
#         self.count = 0
#         self.Scroll(1, 1)
# 
#         for item in list:
#             if onLine_flag:
#                 name = item['nickName']
#                 type = item['type']
#                 online = item['online']
#                 address = item['name']
#                 id = item['id']
#                 version = item['versionCode']
#             else:
#                 name = item.name
#                 type = item.type
#                 online = 'false'
#                 address = item.address
#                 id = item.resId
#                 version = item.version
#                 
# #            if version != PopoConfig.VersionInfo:
# #                if version != PopoConfig.VersionInfo:
# #                    version=PopoConfig.VersionInfo
# #                    querystring = "/account/updateVersionCode?email=" + ProfileFunc.getUser() + "&password=" + ProfileFunc.getPassword() + "&versionCode=" + version
# #                    responeData = UtilFunc.QueryServer(querystring)
# #                    if responeData['result'] != 0 :
# #                        ShowOKMessage(self, responeData['errMsg'])
# #                        return
# 
#             y = self.count * 90 + 130
#             self.SetVirtualSize((605, y + 85))
#             item = DevicesItemPanel(self, self.accountPanel, pos=(0, y), online=online, type=type, name=name, id = id, version=version, address = address)
#             if onLine_flag:
#                 self.items.append(item)
#             self.count = self.count + 1
# 
# 
# class AccountPanel(wx.Panel):
#     def __init__(self, parent):
#         wx.Panel.__init__(self, parent, -1, pos=(0, 66), size=(640,325))
#         self.SetBackgroundColour(wx.WHITE)
# 
#         self.frame = parent.frame
#         self.parent = parent
# 
#         self.devicePanel = AccountDevicesPanel(self)
#         self.modifypasswordPanel = None
#         self.modifynicknamePanel = None
# 
#         self.devicePanel.Show()
# 
#     def ShowUpdateInfo(self):
#         if self.devicePanel:
#             self.devicePanel.info.ShowUpdateInfo()
#         if self.modifypasswordPanel:
#             self.modifypasswordPanel.info.ShowUpdateInfo()
#         if self.modifynicknamePanel:
#             self.modifynicknamePanel.info.ShowUpdateInfo()
# 
#     def OnReLogin(self, evt):
#         errMsg = StartFunc.startConnect(self.frame.fileservice, ProfileFunc.getUser(), ProfileFunc.getPassword())
#         if errMsg:
#             ShowOKMessage(self, errMsg)
#         else:
#             self.btnReLogin.Destroy()
# 
#     def OnCancel(self, evt):
#         self.Hide()
#         self.account = AccountPanel(self.parent)
# 
# #        self.account.Hide()
# #        self.frame.ShowLoginDlg()
# 
#     def OnHideWindow(self, event):
#         self.Hide()
# 
#     def showList(self, evt=None):
#         self.devicePanel.showList()
# 
# class AboutPanel(wx.Panel):
#     def __init__(self, parent):
#         wx.Panel.__init__(self, parent, -1, pos=(0, 66), size=(640,325))
# 
#         self.SetBackgroundColour(wx.WHITE)
# 
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/about_logo.png')
#         title_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         bg = wx.StaticBitmap(self, -1, title_png, (92, 64))
# 
#         label = wx.StaticText(self, -1, u'泡泡云(服务器PC版)', (83, 195))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName='宋体')
#         label.SetFont(font)
# 
#         label = wx.StaticText(self, -1, u"版本  V" + PopoConfig.VersionInfo, (91, 225))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
#         
#         label = wx.StaticText(self, -1, u"感谢使用上海科泰华捷科技有限公司出品的泡泡云产品，此产品" , (259, 45))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
#         
#         label = wx.StaticText(self, -1, u"将会给您带来全新的专属个人云服务的体验，如您在使用过程中" , (259, 65))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
#         
#         label = wx.StaticText(self, -1, u"有任何问题或建议，请联系我们。" , (259, 85))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
# 
#         label = wx.StaticText(self, -1, u"泡泡云官网:", (259, 125))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
#         self._hyper1 = hl.HyperLinkCtrl(self, wx.ID_ANY, 'www.paopaoyun.com',
#                                 URL="http://www.paopaoyun.com" ,pos = (339, 125))  
#         
#         label = wx.StaticText(self, -1, u"产品帮助中心:", (259, 145))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
#         self._hyper1 = hl.HyperLinkCtrl(self, wx.ID_ANY, 'www.paopaoyun.com/help',
#                                 URL="http://www.paopaoyun.com/help" ,pos = (349, 145))  
#         
#         label = wx.StaticText(self, -1, u"客服热线：021-61639169" , (259, 165))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)    
#         
#         label = wx.StaticText(self, -1, u"Email：cs@paopaoyun.com" , (259, 185))
#         label.SetForegroundColour((0x00, 0x00, 0x00))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)        
#         
#         label = wx.StaticText(self, -1, u"copyright ©2012 Kortide Corporation", (259, 225))
#         label.SetForegroundColour((0x58, 0x58, 0x58))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)
#         
#         label = wx.StaticText(self, -1, u"All Rights Reserved.", (259, 245))
#         label.SetForegroundColour((0x58, 0x58, 0x58))
#         font = wx.Font(10, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"宋体")
#         label.SetFont(font)

#-----------------------------------------------------------------------------
# 
# class FilesAddDialog(wx.Dialog):
#     def __init__(
#             self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition,
#             style=wx.DEFAULT_DIALOG_STYLE,
#             useMetal=False,
#             ):
# 
#         pre = wx.PreDialog()
#         pre.Create(parent, ID, title, pos, size, style)
# 
#         # This next step is the most important, it turns this Python
#         # object into the real wrapper of the dialog (instead of pre)
#         # as far as the wxPython extension is concerned.
#         self.PostCreate(pre)
# 
#         sizer = wx.BoxSizer(wx.VERTICAL)
# 
#         box = wx.BoxSizer(wx.HORIZONTAL)
# 
#         label = wx.StaticText(self, -1, u"路径:")
#         box.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         self.txtPath = wx.TextCtrl(self, -1, u"请点击“浏览”选择文件夹路径-->", size=(200,-1))
#         self.txtPath.Disable()
#         box.Add(self.txtPath, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
#         self.txtPath.Bind(wx.EVT_KILL_FOCUS, self.onGetName)
# 
#         btn = wx.Button(self, -1, u"浏览", size=(80,-1))
#         self.Bind(wx.EVT_BUTTON, self.OnBrowser, btn)
#         box.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         box = wx.BoxSizer(wx.HORIZONTAL)
# 
#         label = wx.StaticText(self, -1, u"名称:")
#         box.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         self.txtName = wx.TextCtrl(self, -1, "", size=(200 ,-1))
#         box.Add(self.txtName, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
#         sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)
# 
#         btnsizer = wx.StdDialogButtonSizer()
# 
#         if wx.Platform != "__WXMSW__":
#             btn = wx.ContextHelpButton(self)
#             btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_OK, u"确定")
#         btn.SetDefault()
#         btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_CANCEL, u"取消")
#         btnsizer.AddButton(btn)
#         btnsizer.Realize()
# 
#         sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         self.SetSizer(sizer)
#         sizer.Fit(self)
# 
#     def OnBrowser(self, evt):
#         # In this case we include a "New directory" button.
#         dlg = wx.DirDialog(self, "Choose a directory:",
#                           style=wx.DD_DEFAULT_STYLE
#                            #| wx.DD_DIR_MUST_EXIST
#                            #| wx.DD_CHANGE_DIR
#                            )
# 
#         # If the user selects OK, then we process the dialog's data.
#         # This is done by getting the path data from the dialog - BEFORE
#         # we destroy it.
#         if dlg.ShowModal() == wx.ID_OK:
#             self.txtPath.SetValue(dlg.GetPath())
#             self.txtName.SetValue(os.path.basename(dlg.GetPath()))
# 
#         # Only destroy a dialog after you're done with it.
#         dlg.Destroy()
# 
#     def onGetName(self, evt):
#         path=self.txtPath.GetValue()
#         if path:
#             self.txtName.SetValue(os.path.basename(path))
# 
# class FilesItemEditDialog(wx.Dialog):
#     def __init__(
#             self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition,
#             style=wx.DEFAULT_DIALOG_STYLE,
#             useMetal=False,
#             name="My Floder"
#             ):
# 
#         pre = wx.PreDialog()
#         pre.Create(parent, ID, title, pos, size, style)
# 
#         # This next step is the most important, it turns this Python
#         # object into the real wrapper of the dialog (instead of pre)
#         # as far as the wxPython extension is concerned.
#         self.PostCreate(pre)
# 
#         sizer = wx.BoxSizer(wx.VERTICAL)
#         box = wx.BoxSizer(wx.HORIZONTAL)
# 
#         label = wx.StaticText(self, -1, u"请输入名称:")
#         box.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         self.txtName = wx.TextCtrl(self, -1, name, size=(100,-1))
#         box.Add(self.txtName, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
#         line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
#         sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)
# 
#         btnsizer = wx.StdDialogButtonSizer()
# 
#         if wx.Platform != "__WXMSW__":
#             btn = wx.ContextHelpButton(self)
#             btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_OK, u"确定")
#         btn.SetDefault()
#         btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_CANCEL, u"取消")
#         btnsizer.AddButton(btn)
#         btnsizer.Realize()
# 
#         sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         self.SetSizer(sizer)
#         sizer.Fit(self)
# 
# class FileTitlePanel(wx.Panel):
#     def __init__(self, parent, pos):
#         wx.Panel.__init__(self, parent, -1, pos, size=(640, 30))
# 
#         color = (0xC9, 0xE0, 0xED)
#         self.SetBackgroundColour(color)
# 
#         wx.StaticText(self, -1, u"文件位置", (70, 8), size=(280, -1)).SetBackgroundColour(color)
#         wx.StaticText(self, -1, u"名称", (326, 8)).SetBackgroundColour(color)
#         wx.StaticText(self, -1, u"编辑", (572, 8)).SetBackgroundColour(color)
# 
# class FileItemPanel(wx.Window):
#     def __init__(self, parent, pos, path = "C:\\Documents and Settings\\kuit\\My Documents\\Settings",
#                  name = "My Floder", _name = "My Floder", no=0, manager = None):
#         self.height = 20
#         self.name = name
#         wx.Window.__init__(self, parent, -1, pos, size=(640,self.height))
#         if no % 2 == 0:
#             color = (0xF4, 0xF4, 0xF4)
#             pic_edit = 'res/edit.png'
#             pic_dele = 'res/delet.png'
#             pic_on_edit = 'res/edit_on.png'
#             pic_on_dele = 'res/delet_on.png'
#         else:
#             color = (0xE5, 0xEE, 0xF4)
#             pic_edit = 'res/edit_blue.png'
#             pic_dele = 'res/delet_blue.png'
#             pic_on_edit = 'res/edit_on_blue.png'
#             pic_on_dele = 'res/delet_on_blue.png'
#         self.SetBackgroundColour(color)
# 
#         self.path = path
#         self.manager = manager
#         self.fileservice = manager.frame.fileservice
# 
# #        path = path + path + path + path + path
#         text, height = GetWrapText(DCStaticText.dc, path, 270)
#         if height > self.height:
#             self.height = height
#         text = changeChar(text)
#         txt = wx.StaticText(self, -1, text, (5, -1), size=(280, self.height))
#         self.SetClientSize((640, self.height))
#         _name = changeChar(_name)
#         self.lblName = wx.StaticText(self, -1, _name, (295, -1))
#         self.lblName.SetBackgroundColour(color)
#         #txt = wx.StaticText(self, -1, "正在检测", (470, -1)).SetBackgroundColour('White')
#         imgPath = os.path.join(UtilFunc.module_path(), pic_edit)
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.BitmapButton(self, -1, img, (561, -1), style = wx.NO_BORDER)
#         self.Bind(wx.EVT_BUTTON, self.onEdit, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), pic_on_edit)
#         login_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapSelected(login_png)
#         btn.SetToolTipString(u"修改文件夹名称")
#         self.Bind(wx.EVT_BUTTON, self.onEdit, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), pic_dele)
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.BitmapButton(self, -1, img, (585, -1), style = wx.NO_BORDER)
#         btn.SetToolTipString(u"取消分享该文件夹")
#         self.Bind(wx.EVT_BUTTON, self.onDelete, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), pic_on_dele)
#         login_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapSelected(login_png)
#         self.Bind(wx.EVT_BUTTON, self.onDelete, btn)
# 
#     def onEdit(self, evt):
#         dlg = FilesItemEditDialog(self, -1, u"修改名称", size=(350, 200),name = self.name
#                      )
#         dlg.CenterOnScreen()
# 
#         # this does not return until the dialog is closed.
#         if dlg.ShowModal() == wx.ID_OK:
#             name = dlg.txtName.GetValue()
#             name = name.strip()
#             _name = GetShortString(name, 21)
# 
#             if not name:
#                 ShowOKMessage(self, u'名称不能为空')
#                 return
# 
#             regex = "\&"
#             if re.search(regex, name):
#                 ShowOKMessage(self, u'名称中不能带有符号  & ')
#                 return
# 
#             ret = self.fileservice.ModifyRootDirInfo(self.path, name)
#             ret = json.loads(ret)
#             if ret['result'] != 0 :
#                 ShowOKMessage(self, ret['errMsg'])
#             else :
#                 self.lblName.SetLabel(_name)
#                 self.name = name
# 
#         dlg.Destroy()
# 
#     def onDelete(self, evt):
#         dlg = wx.MessageDialog(self, u'确定取消分享该文件夹吗？',
#                                u'消息提示',
#                                wx.YES_NO | wx.ICON_INFORMATION
#                                )
#         dlg.CenterOnScreen()
#         if dlg.ShowModal() == wx.ID_YES:
#             path = self.path.encode("utf8")
#             path = urllib.quote(path)
#             ret = UtilFunc.QueryCherry("/DeleteRootDir?path=" + path)
#             if ret['result'] != 0 :
#                 ShowOKMessage(self, ret['errMsg'])
#             else:
#                 self.manager.showList()
#         dlg.Destroy()        
#                 
# class FilesPanel(wx.Panel):
#     def __init__(self, parent):
#         wx.Panel.__init__(self, parent, -1, pos=(0, 66), size=(640,325))
#         self.SetBackgroundColour(wx.WHITE)
# 
#         self.panelBg = wx.ScrolledWindow(self, -1, pos=(8, 40), size=(624,272), style=wx.SIMPLE_BORDER)
#         self.panelBg.SetBackgroundColour(wx.WHITE)
#         self.panelBg.SetScrollbars(1, 1, 1, 268)
#         self.panelBg.SetVirtualSize((605, 272))
# 
#         self.frame = parent.frame
#         self.parent = parent
# 
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/add_normal.png')
#         button_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.BitmapButton(self, -1, button_png, (564, 5), style = wx.NO_BORDER)
#         self.Bind(wx.EVT_BUTTON, self.onAdd, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/add_down.png')
#         btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapSelected(btn_png)
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/add_on.png')
#         btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapHover(btn_png)
# 
# #        imgPath = os.path.join(UtilFunc.module_path(), 'res/refresh_normal.png')
# #        button_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
# #        btn = wx.BitmapButton(self, -1, button_png, (564, 5), style = wx.NO_BORDER)
# #        self.Bind(wx.EVT_BUTTON, self.showList, btn)
# #        imgPath = os.path.join(UtilFunc.module_path(), 'res/refresh_down.png')
# #        btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
# #        btn.SetBitmapSelected(btn_png)
# #        imgPath = os.path.join(UtilFunc.module_path(), 'res/refresh_on.png')
# #        btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
# #        btn.SetBitmapFocus(btn_png)
# 
#         self.items = []
# 
#         self.count = 0
#         FileTitlePanel(self.panelBg, (0,0))
#         self.showList()
# 
#     def showList(self, evt=None):
#         for item in self.items:
#             item.Destroy()
# 
#         self.items = []
#         rootDirs = ProfileFunc.getRootFolderInfo()
#         self.count = 0
#         self.panelBg.Scroll(1, 1)
#         height = 0;
#         for dirInfo in rootDirs:
#             path = ProfileFunc.expandPath(dirInfo['path'])
#             name = dirInfo['name']
#             _name = GetShortString(name, 21)
#             y = height + 30
#             self.panelBg.SetVirtualSize((605, y + 40))
#             item = FileItemPanel(self.panelBg, pos=(0, y), path=path, name=name, _name=_name, no=self.count, manager=self)
#             height = height + item.height
#             self.items.append(item)
#             self.count = self.count + 1
# 
#     def onAdd(self, evt):
#         dlg = FilesAddDialog(self, -1, u"增加文件夹", size=(350, 200)
#                      )
#         dlg.CenterOnScreen()
# 
#         # this does not return until the dialog is closed.
#         if dlg.ShowModal() == wx.ID_OK:
#             path=dlg.txtPath.GetValue()
#             name=dlg.txtName.GetValue()
#             name=name.strip()
# 
#             if not name:
#                 ShowOKMessage(self, u'名称不能为空')
#                 return
# 
#             ret = self.frame.fileservice.AddRootDir(path, name)
#             ret = json.loads(ret)
# 
#             if ret['result'] != 0 :
#                 if ret['errMsg'] == "popoCloud.error.InvalidArgument" :
#                     ShowOKMessage(self, u'您指定的路径、文件名或过滤器无效，请确认后重试')
#                 elif ret['errMsg'] == "popoCloud.error.HasExisted" :
#                     ShowOKMessage(self, u'您指定的路径已经添加')
#                 elif ret['errMsg'] == "popoCloud.error.NotExist" :
#                     ShowOKMessage(self, u'您指定的路径不存在，请确认后重试')
#             else :
#                 self.showList()
# 
#         dlg.Destroy()

#----------------------------------------------------------------
# class PicturesAddDialog(wx.Dialog):
#     def __init__(
#             self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition,
#             style=wx.DEFAULT_DIALOG_STYLE,
#             useMetal=False,
#             ):
# 
#         pre = wx.PreDialog()
#         pre.Create(parent, ID, title, pos, size, style)
# 
#         # This next step is the most important, it turns this Python
#         # object into the real wrapper of the dialog (instead of pre)
#         # as far as the wxPython extension is concerned.
#         self.PostCreate(pre)
#         self.parent = parent
# 
#         sizer = wx.BoxSizer(wx.VERTICAL)
# 
#         box = wx.BoxSizer(wx.HORIZONTAL)
# 
#         label = wx.StaticText(self, -1, u"路径:")
#         box.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         self.txtPath = wx.TextCtrl(self, -1, u"请点击“浏览”选择文件夹路径-->", size=(200,-1))
#         self.txtPath.Disable()
#         box.Add(self.txtPath, 1, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         btn = wx.Button(self, -1, u"浏览", size=(80,-1))
#         self.Bind(wx.EVT_BUTTON, self.OnBrowser, btn)
#         box.Add(btn, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         box = wx.BoxSizer(wx.HORIZONTAL)
# 
#         label = wx.StaticText(self, -1, u"格式:")
#         box.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         self.check_list = []
#         #for filter_type in default_dict[self.parent.type_name].split(";"):
#         for filter_type in default_dict['picture'].split(";"):
#             check_box = wx.CheckBox(self, -1,filter_type,(20,60),(60,-1))
#             check_box.SetValue(True)
#             self.check_list.append(check_box)
#             box.Add(check_box, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
#         sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)
# 
#         btnsizer = wx.StdDialogButtonSizer()
# 
#         if wx.Platform != "__WXMSW__":
#             btn = wx.ContextHelpButton(self)
#             btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_OK, u"确定")
#         btn.SetHelpText("The OK button completes the dialog")
#         btn.SetDefault()
#         btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_CANCEL, u"取消")
#         btn.SetHelpText("The Cancel button cancels the dialog. (Cool, huh?)")
#         btnsizer.AddButton(btn)
#         btnsizer.Realize()
# 
#         sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         self.SetSizer(sizer)
#         sizer.Fit(self)
# 
#     def OnBrowser(self, evt):
#         # In this case we include a "New directory" button.
#         dlg = wx.DirDialog(self, "Choose a directory:",
#                           style=wx.DD_DEFAULT_STYLE
#                            #| wx.DD_DIR_MUST_EXIST
#                            #| wx.DD_CHANGE_DIR
#                            )
# 
#         # If the user selects OK, then we process the dialog's data.
#         # This is done by getting the path data from the dialog - BEFORE
#         # we destroy it.
#         if dlg.ShowModal() == wx.ID_OK:
#             self.txtPath.SetValue(dlg.GetPath())
# 
#         # Only destroy a dialog after you're done with it.
#         dlg.Destroy()

# class PictureItemEditDialog(wx.Dialog):
#     def __init__(
#             self, parent, ID, title, size=wx.DefaultSize, pos=wx.DefaultPosition,
#             style=wx.DEFAULT_DIALOG_STYLE,
#             useMetal=False,
#             filter=""
#             ):
# 
#         pre = wx.PreDialog()
#         pre.Create(parent, ID, title, pos, size, style)
# 
#         # This next step is the most important, it turns this Python
#         # object into the real wrapper of the dialog (instead of pre)
#         # as far as the wxPython extension is concerned.
#         self.PostCreate(pre)
# 
#         sizer = wx.BoxSizer(wx.VERTICAL)
#         box = wx.BoxSizer(wx.HORIZONTAL)
# 
#         label = wx.StaticText(self, -1, u"请输入图片过滤类型:")
#         box.Add(label, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
#         
#         self.check_list = []
#         for filter_type in default_dict['picture'].split(";"):
#             check_box = wx.CheckBox(self, -1,filter_type,(20,60),(60,-1))
#             if filter_type in filter:
#                 check_box.SetValue(True)
#             else:
#                 check_box.SetValue(False)
#             self.check_list.append(check_box)
#             box.Add(check_box, 0, wx.ALIGN_CENTRE|wx.ALL, 5)
# 
#         sizer.Add(box, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
#         line = wx.StaticLine(self, -1, size=(20,-1), style=wx.LI_HORIZONTAL)
#         sizer.Add(line, 0, wx.GROW|wx.ALIGN_CENTER_VERTICAL|wx.RIGHT|wx.TOP, 5)
# 
#         btnsizer = wx.StdDialogButtonSizer()
# 
#         if wx.Platform != "__WXMSW__":
#             btn = wx.ContextHelpButton(self)
#             btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_OK, u"确定")
#         btn.SetDefault()
#         btnsizer.AddButton(btn)
# 
#         btn = wx.Button(self, wx.ID_CANCEL, u"取消")
#         btnsizer.AddButton(btn)
#         btnsizer.Realize()
# 
#         sizer.Add(btnsizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
# 
#         self.SetSizer(sizer)
#         sizer.Fit(self)

# class PictureTitlePanel(wx.Panel):
#     def __init__(self, parent, pos):
#         wx.Panel.__init__(self, parent, -1, pos, size=(640, 30))
# 
#         color = (0xC9, 0xE0, 0xED)
#         self.SetBackgroundColour(color)
# 
#         wx.StaticText(self, -1, u"文件位置", (70, 8), size=(280, -1)).SetBackgroundColour(color)
#         wx.StaticText(self, -1, u"格式", (326, 8)).SetBackgroundColour(color)
#         wx.StaticText(self, -1, u"状态", (480, 8)).SetBackgroundColour(color)
#         wx.StaticText(self, -1, u"编辑", (572, 8)).SetBackgroundColour(color)


# class PictureItemPanel(wx.Window):
#     def __init__(self, parent, pos, path = "C:\\Documents and Settings\\kuit\\My Documents\\Settings",
#                  filter=default_dict['picture'], _filter=default_dict['picture'], folderId=1, scanning = 0, no=0, manager=None):
#         self.folderId = str(folderId)
#         self.manager = manager
#         self.path = path
#         
#         self.filter = filter
# 
#         self.height = 20
#         wx.Window.__init__(self, parent, -1, pos, size=(640,self.height))
# 
#         if no % 2 == 0:
#             color = (0xF4, 0xF4, 0xF4)
#             pic_edit = 'res/edit.png'
#             pic_dele = 'res/delet.png'
#             pic_on_edit = 'res/edit_on.png'
#             pic_on_dele = 'res/delet_on.png'
#         else:
#             color = (0xE5, 0xEE, 0xF4)
#             pic_edit = 'res/edit_blue.png'
#             pic_dele = 'res/delet_blue.png'
#             pic_on_edit = 'res/edit_on_blue.png'
#             pic_on_dele = 'res/delet_on_blue.png'
#         self.SetBackgroundColour(color)
#         #text, height = GetWrapText(DCStaticText.dc, path, 270)
#         text = path
#         height = 50
#         if height > self.height:
#             self.height = height
#         text = changeChar(text)
#         txt = wx.StaticText(self, -1, text, (5, -1), size=(280, self.height))
#         self.SetClientSize((640, self.height))
#         self.lblFilter = wx.StaticText(self, -1, _filter, (295, -1))
#         self.lblFilter.SetBackgroundColour(color)
#         if scanning:
#             txt = wx.StaticText(self, -1, u"正在检测...", (470, -1)).SetBackgroundColour(color)
#         else:
#             txt = wx.StaticText(self, -1, u"检测完成", (470, -1)).SetBackgroundColour(color)
# 
#         imgPath = os.path.join(UtilFunc.module_path(), pic_edit)
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.BitmapButton(self, -1, img, (561, -1), style = wx.NO_BORDER)
#         self.Bind(wx.EVT_BUTTON, self.onEdit, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), pic_on_edit)
#         login_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapSelected(login_png)
#         btn.SetToolTipString(u"修改图片过滤条件")
#         self.Bind(wx.EVT_BUTTON, self.onEdit, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), pic_dele)
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.BitmapButton(self, -1, img, (585, -1), style = wx.NO_BORDER)
#         self.Bind(wx.EVT_BUTTON, self.onDelete, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), pic_on_dele)
#         login_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapSelected(login_png)
#         btn.SetToolTipString(u"取消显示该文件夹图片")
#         self.Bind(wx.EVT_BUTTON, self.onDelete, btn)
# 
#     def onEdit(self, evt):
#         dlg = PictureItemEditDialog(self, -1, u"编辑过滤器", size=(350, 200),filter = self.filter
#                      )
#         dlg.CenterOnScreen()
# 
#         # this does not return until the dialog is closed.
#         if dlg.ShowModal() == wx.ID_OK:
#             filter = getPicFilter(dlg)
#             for ch in filter:
#                 if isinstance(ch, unicode) and unicodedata.east_asian_width(ch) != 'Na':
#                     ShowOKMessage(self, u'过滤器不能输入汉字')
#                     return
#             filter = filter.replace(' ', '')
#             _filter = GetShortString(filter, 27)
#             if not filter:
#                 ShowOKMessage(self, u'过滤器不能为空')
#                 return
# 
#             ret = self.manager.frame.fileservice.ModifyFolderFilter(self.folderId, filter)
#             ret = json.loads(ret)
#             if ret['result'] != 0 :
#                 ShowOKMessage(self, ret['errMsg'])
#             else :
#                 self.lblFilter.SetLabel(_filter)
#                 
#             self.filter = filter
# 
#         dlg.Destroy()
# 
#     def onDelete(self, evt):
#         dlg = wx.MessageDialog(self, u'确定要取消显示该文件夹图片吗？',
#                                u'消息提示',
#                                wx.YES_NO | wx.ICON_INFORMATION
#                                )
#         dlg.CenterOnScreen()
#         
#         if dlg.ShowModal() == wx.ID_YES:
#             ProfileFunc.getMainServer().scanFolderMoniter.setMediaFolder([],[self.path])
#             time.sleep(0.2)
#             self.manager.showList()
#             #ret = self.manager.frame.fileservice.RemoveFromLibrary(self.folderId)
#             #ret = json.loads(ret)
#     
#             #if ret['result'] != 0 :
#             #    ShowOKMessage(self, ret['errMsg'])
#             #else:
#             #    self.manager.showList()
#         dlg.Destroy()

# class PicturesPanel(wx.Panel):
#     def __init__(self, parent, type_name, user):
#         wx.Panel.__init__(self, parent, -1, pos=(0, 66), size=(640,325))
#         self.SetBackgroundColour(wx.WHITE)
#         self.type_name = type_name
#         self.user = user
# 
#         self.panelBg = wx.ScrolledWindow(self, -1, pos=(8, 40), size=(624,272), style=wx.SIMPLE_BORDER)
#         self.panelBg.SetBackgroundColour(wx.WHITE)
#         self.panelBg.SetScrollbars(1, 1, 1, 268)
#         self.panelBg.SetVirtualSize((605, 272))
# 
#         self.frame = parent.frame
#         self.parent = parent
# 
# 
#         wx.StaticText(self, -1, u"用户名", (10, 2), size=(50,-1)).SetBackgroundColour((0xE9, 0xE9, 0xE9))
#         wx.StaticText(self, -1, self.user , (60, 2), size=(150,-1)).SetBackgroundColour((0xE9, 0xE9, 0xE9))
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/add_normal.png')
#         button_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.BitmapButton(self, -1, button_png, (564, 5), style = wx.NO_BORDER)
#         self.Bind(wx.EVT_BUTTON, self.onAdd, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/add_down.png')
#         btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapSelected(btn_png)
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/add_on.png')
#         btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapHover(btn_png)
# 
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/refresh_normal.png')
#         button_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.BitmapButton(self, -1, button_png, (480, 5), style = wx.NO_BORDER)
#         self.Bind(wx.EVT_BUTTON, self.onRefresh, btn)
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/refresh_down.png')
#         btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapSelected(btn_png)
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/refresh_on.png')
#         btn_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn.SetBitmapHover(btn_png)
# 
#         self.items = []
# 
#         self.count = 0
#         PictureTitlePanel(self.panelBg, pos=(0, 0))
#         self.showList()
# 
#     def onRefresh(self, evt=None):
#         data = ProfileFunc.getLibraryFolderInfo()
#         #for info in data:
#         #    if info['scanning'] != 1:      
#         #        self.parent.fileservice.RebuildLibrary('picture', info['folderId'])
#         self.showList()
#         
#     def showList(self, evt=None):
#         for item in self.items:
#             item.Destroy()
#             
#         data = ProfileFunc.getLibraryFolderInfo()
#         self.items = []
#         self.count = 0
#         self.panelBg.Scroll(1, 1)
#         height = 0
#         for info in data:
#             path = info['path']
#             filter = info['filter']
#             _filter = GetShortString(filter, 27)
#             folderId = info['folderId']
#             scanning = info['scanning']
#             y = height + 30
#             self.panelBg.SetVirtualSize((605, y + 40))
#             item = PictureItemPanel(self.panelBg, pos=(0, y), path=path, filter=filter, _filter=_filter, folderId=folderId, scanning = scanning, no=self.count, manager=self)
#             height = height + item.height
#             self.items.append(item)
#             self.count = self.count + 1
#   
#     def onAdd(self, evt):
#         dlg = PicturesAddDialog(self, -1, u"增加文件夹 ", size=(350, 200)
#                      )
#         dlg.CenterOnScreen()
# 
#         # this does not return until the dialog is closed.
#         if dlg.ShowModal() == wx.ID_OK:
# 
#             path = dlg.txtPath.GetValue().replace('\\', '/')
# 
#             filter = getPicFilter(dlg)
#             filter = filter.replace(' ', '')
# 
#             #ret = self.parent.fileservice.AddToLibrary(self.type_name, path)
#             ProfileFunc.addSubLibrary(path)
#             ProfileFunc.addToLibrary(self.type_name, path)
#             ProfileFunc.getMainServer().scanFolderMoniter.setMediaFolder([{'folder':path,'type':'all'}],[])
#             ProfileFunc.execLibrarySql('update folders set scanning=1 where path = ?',(path,))
#             #ret = json.loads(ret)
# 
#             #if ret['result'] != 0 :
#             #    if ret['errMsg'] == "popoCloud.error.InvalidArgument" :
#             #        ShowOKMessage(self, u'您指定的路径、文件名或过滤器无效，请确认后重试')
#             #    elif ret['errMsg'] == "popoCloud.error.HasExisted" :
#             #        ShowOKMessage(self, u'您指定的路径已经添加')
#             #    elif ret['errMsg'] == "popoCloud.error.NotExist" :
#             #        ShowOKMessage(self, u'您指定的路径不存在，请确认后重试')
#             #else :
#             self.showList()
# 
#         dlg.Destroy()

#------------------------------------------------------------------------------
# 
# from Icon import getAppIcon
# 
# class PreferencesDialog(wx.Dialog):
#     '''
#     popoCloud preference dialog
#     '''
# 
#     def __init__(self, parent):
#         '''
#         Constructor
#         '''
#         wx.Dialog.__init__(self, None, -1, u"泡泡云")
# 
#         self.frame = parent
# 
#         self.SetIcon(getAppIcon())
# 
# 
#         DCStaticText(self, -1, "", pos=(0, 100), size=(1, 1)).SetBackgroundColour(wx.WHITE)
# #        wx.StaticText(self, -1, "", pos=(355, 0), size=(285, 71)).SetBackgroundColour(wx.WHITE)
# 
#         sizer = wx.BoxSizer(wx.VERTICAL)
# 
#         btnPanel = bp.ButtonPanel(self)
#         self.btnPanel = btnPanel
#         self.SetBackgroundColour((0xC9, 0xE0, 0xED))
# 
#         self.SetClientSize((640, 390))
# 
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/pictures.png')
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btnPictures = bp.ButtonInfo(btnPanel, 1, img, "Normal", u"图片", kind=wx.ITEM_CHECK)
#         self.Bind(wx.EVT_BUTTON, self.OnButtons, btnPictures)
#         
# #        imgPath = os.path.join(UtilFunc.module_path(), 'res/pictures.png')
# #        img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
# #        btnMusic = bp.ButtonInfo(btnPanel, 1, img, "Normal", u"音乐", kind=wx.ITEM_CHECK)
# #        self.Bind(wx.EVT_BUTTON, self.OnButtons, btnMusic)
# #        
# #        imgPath = os.path.join(UtilFunc.module_path(), 'res/pictures.png')
# #        img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
# #        btnVideos = bp.ButtonInfo(btnPanel, 1, img, "Normal", u"视频", kind=wx.ITEM_CHECK)
# #        self.Bind(wx.EVT_BUTTON, self.OnButtons, btnVideos)
# 
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/files.png')
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btnFiles = bp.ButtonInfo(btnPanel, 1, img, "Normal", u"文件", kind=wx.ITEM_CHECK)
#         self.Bind(wx.EVT_BUTTON, self.OnButtons, btnFiles)
# 
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/account.png')
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btnAccount = bp.ButtonInfo(btnPanel, 1, img, "Toggled", u"设置", wx.ITEM_CHECK)
#         self.Bind(wx.EVT_BUTTON, self.OnButtons, btnAccount)
# 
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/about.png')
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btnAbout = bp.ButtonInfo(btnPanel, 1, img, "Normal", u"关于", kind=wx.ITEM_CHECK)
#         self.Bind(wx.EVT_BUTTON, self.OnButtons, btnAbout)
# 
#         btnPanel.AddButton(btnAccount)
#         btnPanel.AddButton(btnPictures)
# #        btnPanel.AddButton(btnMusic)
# #        btnPanel.AddButton(btnVideos)
#         btnPanel.AddButton(btnFiles)
#         btnPanel.AddButton(btnAbout)
# 
#         btnAccount.SetToggled(True)
#         btnAccount.SetStatus("Toggled")
#         self._current_btn = btnAccount
# 
#         art = bp.BPArt(bp.BP_DEFAULT_STYLE)
#         art.SetMetric(bp.BP_SEPARATOR_SIZE, 0)
#         art.SetMetric(bp.BP_MARGINS_SIZE, wx.Size(6, 0))
#         art.SetMetric(bp.BP_BORDER_SIZE, 0)
#         art.SetMetric(bp.BP_PADDING_SIZE, wx.Size(20, 6))
# 
#         art.SetColor(bp.BP_BACKGROUND_COLOUR, (0xC9, 0xE0, 0xED))
#         art.SetColor(bp.BP_BORDER_COLOUR, (0xC9, 0xE0, 0xED));
#         art.SetColor(bp.BP_SELECTION_BRUSH_COLOUR, wx.WHITE)
#         art.SetColor(bp.BP_SELECTION_PEN_COLOUR, wx.WHITE)
#         art.SetColor(bp.BP_HOVER_BRUSH_COLOUR, (0x9D, 0xBF, 0xD2))
#         art.SetColor(bp.BP_HOVER_PEN_COLOUR, wx.Colour(50,100,255))
#         btnPanel.SetBPArt(art)
#         btnPanel.DoLayout()
#         sizer.Add(btnPanel)
# 
#         btnSizer = wx.StdDialogButtonSizer()
# 
#         btnSizer.Realize()
#         sizer.Add(btnSizer, 0, wx.ALIGN_CENTER_VERTICAL|wx.ALL, 5)
#         self.SetSizer(sizer)
# #        sizer.Fit(self)
# 
#         self.Bind(wx.EVT_CLOSE, self.OnHideWindow)
#         
#         self.panel_list = [AccountPanel(self), None, None, AboutPanel(self)]
#         self.panel_list[3].Hide()
#         
# #        self.panel_list = [AccountPanel(self), None, None, None, None, AboutPanel(self)]
# #        self.panel_list[5].Hide()
# 
#     def HideAllPanel(self):
#         for Panel in self.panel_list:
#             if Panel: Panel.Hide()
# 
#     def OnButtons(self, event=None):
#         self._current_btn.SetToggled(False)
#         self._current_btn.SetStatus("Normal")
# 
#         event.EventObject.SetToggled(True)
#         event.EventObject.SetStatus("Toggled")
#         self._current_btn = event.EventObject
# 
#         self.HideAllPanel()
#         if self.btnPanel._currentButton in [1]:
#             select_type = default_type[self.btnPanel._currentButton - 1]
#             self.panel_list[self.btnPanel._currentButton] = PicturesPanel(self, select_type)
#         elif self.btnPanel._currentButton == 2:
#             self.panel_list[self.btnPanel._currentButton] = FilesPanel(self)
#         self.panel_list[self.btnPanel._currentButton].Show()
# 
#     def OnHideWindow(self, event):
#         self.Hide()
# 
#     def RefresDevieceshList(self, status=0):
#         if self.panel_list[0]:
#             self.panel_list[0].showList()
#             self.panel_list[0].Refresh()
# 
#     def RefreshPicturesList(self, type_name = None):
#         if self.panel_list[1]:
#             self.panel_list[1].showList()
#             self.panel_list[1].Refresh()


class ElastosDialog(wx.Dialog):
    '''
    popoCloud preference dialog
    '''
    def __init__(self, parent, user):

        wx.Dialog.__init__(self, None, -1, u"ElastosServer", size=(907,463),style=wx.NO_BORDER)

        self.frame = parent
        self.user = user
        self.preferences = None

        imgPath = os.path.join(UtilFunc.module_path(), 'res/background_2.png')
        bgpng = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        size = bgpng.GetSize()
        self.SetClientSize(size)
        self.bgParent = BGPanel(self, size=size, bmp=bgpng)

        self.bgParent.Bind(wx.EVT_LEFT_DOWN, self.OnPanelLeftDown)
        self.bgParent.Bind(wx.EVT_MOTION, self.OnPanelMotion)
        self.bgParent.Bind(wx.EVT_LEFT_UP, self.OnPanelLeftUp)
        
        imgPath = os.path.join(UtilFunc.module_path(), 'res/closebutton.png')
        close_button= wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn4 = wx.BitmapButton(self.bgParent, -1, close_button, pos=(670, 7), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.Closebutton ,btn4)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/minibutton.png')
        mini_button = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn5 = wx.BitmapButton(self.bgParent, -1, mini_button, pos=(630, 7), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.Minibutton ,btn5)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/yilai_pc.png')
        self.add = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.backgroud = wx.StaticBitmap(self.bgParent, -1, self.add, pos=(32, 73), style = wx.NO_BORDER)
        
        imgPath6 = os.path.join(UtilFunc.module_path(), '%s/add_sixth.png'%parent_dir)
        self.add6 = wx.Image(imgPath6, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        imgPath1 = os.path.join(UtilFunc.module_path(), '%s/add_first.png'%parent_dir)
        self.add1 = wx.Image(imgPath1, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        imgPath2 = os.path.join(UtilFunc.module_path(), '%s/add_second.png'%parent_dir)
        self.add2 = wx.Image(imgPath2, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        imgPath3 = os.path.join(UtilFunc.module_path(), '%s/add_third.png'%parent_dir)
        self.add3 = wx.Image(imgPath3, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        imgPath4 = os.path.join(UtilFunc.module_path(), '%s/add_forth.png'%parent_dir)
        self.add4 = wx.Image(imgPath4, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        imgPath5 = os.path.join(UtilFunc.module_path(), '%s/add_fifth.png'%parent_dir)
        self.add5 = wx.Image(imgPath5, wx.BITMAP_TYPE_PNG).ConvertToBitmap()

        self.backgroud = wx.StaticBitmap(self.bgParent, -1, self.add6, pos=(257, 172), style = wx.NO_BORDER)
        thread.start_new_thread(self._loop,())

        imgPath = os.path.join(UtilFunc.module_path(), 'res/appmaker.png')
        app_make = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn1 = wx.BitmapButton(self.bgParent, -1, app_make, pos=(46, 172), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.button1Click,btn1)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/sitemaker.png')
        app_make = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn2 = wx.BitmapButton(self.bgParent, -1, app_make, pos=(46, 244), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.button2Click,btn2)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/elastos.png')
        elasos_make = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn2 = wx.BitmapButton(self.bgParent, -1, elasos_make, pos=(46, 316), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.button3Click,btn2)
        self.Bind(wx.EVT_CLOSE, parent.OnClose)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/settings.png')
        elasos_set = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn3 = wx.BitmapButton(self.bgParent, -1, elasos_set, pos=(660, 49), style = wx.NO_BORDER)
        btn3.SetToolTipString(setting)
        self.Bind(wx.EVT_BUTTON, self.button_setting ,btn3)
        
    def _loop(self):
        while True:
            if self.backgroud.GetBitmap() == self.add6:
                self.backgroud.SetBitmap(self.add1)
            elif self.backgroud.GetBitmap() == self.add1:
                self.backgroud.SetBitmap(self.add2)
            elif self.backgroud.GetBitmap() == self.add2:
                self.backgroud.SetBitmap(self.add3)
            elif self.backgroud.GetBitmap() == self.add3:
                self.backgroud.SetBitmap(self.add4)
            elif self.backgroud.GetBitmap() == self.add4:
                self.backgroud.SetBitmap(self.add5)
            else:
                self.backgroud.SetBitmap(self.add6)
            time.sleep(2)
        
    def button1Click(self,evt):
        webbrowser.open_new_tab("http://appmaker.elastos.com")

    def button2Click(self,event):
        webbrowser.open_new_tab("http://sitemaker.elastos.com")

    def button3Click(self,event):
        webbrowser.open_new_tab("http://elastos.com")

    def button_setting(self,event):
        if self.preferences:
            self.preferences.Destroy()
        self.preferences = ShowSettings(self.frame ,self.user)
        self.preferences.CenterOnScreen()
        self.preferences.Show()

    def Closebutton(self, event):
        self.Destroy()
        cherrypy.engine.exit()
        os._exit(0)

    def Minibutton(self, evt):
        self.Iconize(True)

    def OnPanelLeftDown(self, event):
        pos = event.GetPosition()
        x, y = self.ClientToScreen(event.GetPosition())
        ox, oy = self.GetPosition()
        dx = x - ox
        dy = y - oy
        self.delta = ((dx, dy))

    def OnPanelMotion(self, event):
        if event.Dragging() and event.LeftIsDown():
            mouse=wx.GetMousePosition()
            self.Move((mouse.x-self.delta[0],mouse.y-self.delta[1]))

    def OnPanelLeftUp(self, event):
        if self.frame.HasCapture():
            self.frame.ReleaseMouse()

    def RefreshPicturesList(self):
        self.preferences.cloud_set_panel.file_panels.showList()

