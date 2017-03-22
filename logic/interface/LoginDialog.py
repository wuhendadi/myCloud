# -*- coding: utf-8 -*-

import os
import wx
import json
import md5
import locale
import webbrowser
import requests
import UtilFunc
import StartFunc
import ProfileFunc 
import Log
import cherrypy

from TPControls import TPButton, ShowOKMessage, BGPanel
from PopoConfig import VersionInfo, AuthHost, AuthPort

sys_lang = locale.getdefaultlocale()[0]
if sys_lang == "zh_CN":
    parent_dir = "res/zh_cn"
    use_name = u"用户名/手机号/邮箱" 
    forget_sec = u"忘记密码" 
    register_account = u"注册帐号"
    des_one = u'请输入正确的帐号和密码!'
    des_two = u'帐号或密码错误!' 
    des_three = u'网络连线问题,请检查网路状态后重试!'
    setting = u"设置"
    yi_name = u"亦来云盘"
else:
    parent_dir = "res/zh_tw"
    use_name = u"用戶名/手機號/郵箱"
    forget_sec = u"忘記密碼" 
    register_account = u"註冊帳號"
    des_one = u'請輸入正確的帳號和密碼!'
    des_two = u'帳號或密碼錯誤!' 
    des_three =u'網路連線問題，請檢查網路狀態無虞後重試!' 
    setting = u"設置"
    yi_name = u"亦來雲盤"

#-------------------------------------------------------------
class LoginDialog(wx.Dialog):

    def __init__(self, parent, username=""):
        '''
        Constructor
        '''
        wx.Dialog.__init__(self, None, -1, yi_name, size=(510,434),style=wx.NO_BORDER)

        self.frame = parent
        imgPath = os.path.join(UtilFunc.module_path(), 'res/background.png')
        bgpng = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        size = bgpng.GetSize()
        self.SetClientSize(size)
        bgParent = BGPanel(self, size=size, bmp=bgpng)

        bgParent.Bind(wx.EVT_LEFT_DOWN, self.OnPanelLeftDown)
        bgParent.Bind(wx.EVT_MOTION, self.OnPanelMotion)
        bgParent.Bind(wx.EVT_LEFT_UP, self.OnPanelLeftUp)

        self.user = wx.TextCtrl(bgParent, -1, use_name ,(149,254), size=(250, 28), style=wx.NO_BORDER)
        font = wx.Font(14, wx.SWISS, wx.NORMAL, wx.NORMAL, faceName=u"微软雅黑")
        self.user.SetFont(font)
        self.user.Bind(wx.EVT_LEFT_DOWN, self.OnUserTextDown)

        self.password = wx.TextCtrl(bgParent, -1, u"", (149, 289), size=(250, 28), style=wx.TE_PASSWORD|wx.NO_BORDER)
        self.password.SetMaxLength(16)
        self.password.SetFont(font)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/sign_in.png')
        login_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn = wx.BitmapButton(bgParent, -1, login_png, (104, 359), style = wx.NO_BORDER)

        self.Bind(wx.EVT_BUTTON, self.OnLogin, btn)
        imgPath = os.path.join(UtilFunc.module_path(), 'res/sign_in_hover.png')
        login_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn.SetBitmapSelected(login_png)
        imgPath = os.path.join(UtilFunc.module_path(), 'res/sign_in_down.png')
        login_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn.SetBitmapHover(login_png)

        btn_z = TPButton(bgParent, -1, register_account, pos=(412,293), style = 0)
        btn_z.SetTextForeground((0x00, 0x00, 0x00))
        btn_z.SetBackgroundStyle(wx.BG_STYLE_SYSTEM)
        self.Bind(wx.EVT_BUTTON, self.OnRegister, btn_z)


        btn = TPButton(bgParent, -1, forget_sec , pos=(412, 255), style = 0)
        btn.SetTextForeground((0x00, 0x00, 0x00))
        btn.SetBackgroundStyle(wx.BG_STYLE_SYSTEM)
        self.Bind(wx.EVT_BUTTON, self.OnGetPassword, btn)
        self.Bind(wx.EVT_CLOSE, parent.OnClose)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/closebutton.png')
        close_button= wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn3 = wx.BitmapButton(bgParent, -1, close_button, pos=(470, 7), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.Closebutton ,btn3)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/minibutton.png')
        mini_button = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        btn4 = wx.BitmapButton(bgParent, -1, mini_button, pos=(434, 7), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.Minibutton ,btn4)

    def _checkAuth(self, username, password):
        headers = {
                "Content-type": "application/json", 
                "Accept": "application/json"
                }
    
        try:
            requests.adapters.DEFAULT_RETRIES = 5 
            password = md5.md5(password).hexdigest()
            payloads = json.dumps({"loginId":username,"password":password,"serialNo":UtilFunc.getSN(),"softwareVersion":VersionInfo})
            r = requests.post("http://%s:%s/auth/api/auth/login/popoServer"%(AuthHost, AuthPort), payloads, headers = headers)
        except Exception,e:
            Log.error("login error[%s]"%e)
            return 0
        if r.status_code == 200:
            return 1 
        else:
            return 2 
    def OnUserTextDown(self, evt):
        self.user.Clear()
        self.user.Unbind(wx.EVT_LEFT_DOWN)

    def OnLogin(self, evt):
        #self.Destroy()
        user = self.user.GetValue().strip()
        password = self.password.GetValue().strip()
        if not user or not password :
            ShowOKMessage(self, des_one)
            return

        length = len(password)
        if length < 6 or length >16:
            ShowOKMessage(self, des_two)
            return
        user = user.lower()
        ret_code  = self._checkAuth(user, password)
        if ret_code == 0:
            ShowOKMessage(self, des_three)
        if ret_code == 1:
            self.frame.loginDlg = None
            self.Destroy()
            try:
                StartFunc.action(ProfileFunc._fileService) 
            except Exception,e:
                Log.error("login error[%s]"%e)
            self.frame.ChangeRelayStatus(2,user)         
            self.frame.ShowElastos(user)
        elif ret_code == 2:
            ShowOKMessage(self, des_two)
            
    def OnRegister(self, evt):
        webbrowser.open_new_tab("http://elastos.com")
        #self.Hide()
        #self.frame.registerDlg = RegisterDialog.RegisterDialog(self)
        #self.frame.registerDlg.CenterOnScreen()
        #self.frame.registerDlg.Show()

    def OnGetPassword(self, evt):
        webbrowser.open_new_tab("http://elastos.com")
        #user = self.user.GetValue().strip()
        #if not user :
        #    ShowOKMessage(self, u'请输入正确的帐号!')
        #    return

        #querystring = "/account/resetPasswordMail?email=" + user
        #ret = WebFunc.queryServer(querystring)
        #ShowOKMessage(self, ret['message'])
    def Closebutton(self, evt):
        self.Destroy()
        cherrypy.engine.exit()
        os._exit(0)

    def Minibutton(self, evt):
        self.Iconize(True)

    def OnPanelLeftDown(self, event):
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

