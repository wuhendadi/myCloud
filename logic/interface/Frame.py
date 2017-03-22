# -*- coding: utf-8 -*-

#http://www.codecho.com/wxpython-create-task-bar-icon/

import wx
import os
from Icon import getTBIcon
import threading
import cherrypy
import webbrowser
import PopoConfig
import ProfileFunc
import popoUpdate as Update
import UpdateUI
import PreferencesDialog
import LoginDialog
from TPControls import ShowOKMessage
from multiprocessing.connection import Listener


class pipeThread(threading.Thread):
    def __init__(self, frameWork):
        threading.Thread.__init__(self)
        self.frame = frameWork

    def OnShow(self):
        ser = Listener(r'\\.\pipe\pipename')
        while True:
            conn = ser.accept()
            buff = conn.recv()
            if buff == '1':
                self.frame.OnShowConfig(1)
                conn.close()

    def run(self):
        self.OnShow()

########################################################################
class TBIcon(wx.TaskBarIcon):
    TBMENU_RESTORE = wx.NewId()
    TBMENU_CLOSE   = wx.NewId()
    TBMENU_PREFERENCES  = wx.NewId()
    TBMENU_WEBSERVICE  = wx.NewId()
    TBMENU_SETTING  = wx.NewId()
    TBMENU_HELPCENTRE  = wx.NewId()
    TBMENU_UNLOGIN  = wx.NewId()
    TBMENU_PRODUCTVERSION  = wx.NewId()
    TBMENU_REMOVE  = wx.NewId()
    TBMENU_BROWN  = wx.NewId()

    #----------------------------------------------------------------------
    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        self.frame = frame

        # Set the image
        self.tbIcon = getTBIcon(self, 0)

        self.SetIcon(self.tbIcon, u"亦来云盘")

        self.nickName = "-"

        # bind some events
        self.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_CLOSE)
        self.Bind(wx.EVT_MENU, frame.OnShowConfig, id=self.TBMENU_PREFERENCES)
        self.Bind(wx.EVT_MENU, self.OnTaskWebService, id=self.TBMENU_WEBSERVICE)
        self.Bind(wx.EVT_MENU, frame.OnShowConfig, id=self.TBMENU_SETTING)
        self.Bind(wx.EVT_MENU, self.OnTaskHelpCentre, id=self.TBMENU_HELPCENTRE)
        self.Bind(wx.EVT_MENU, self.OnTaskUpdate, id=self.TBMENU_PRODUCTVERSION)
#        self.Bind(wx.EVT_TASKBAR_RIGHT_DOWN, self.OnTaskBarRightClick)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, frame.OnShowConfig)

    #----------------------------------------------------------------------
    def CreatePopupMenu(self, evt=None):
        """
        This method is called by the base class when it needs to popup
        the menu for the default EVT_RIGHT_DOWN event.  Just create
        the menu how you want it and return it from this function,
        the base class takes care of the rest.
        """

        menu = wx.Menu()
        #menu.Append(self.TBMENU_WEBSERVICE, u"网页客户端")
        menu.Append(self.TBMENU_PREFERENCES, u"设置")
        #menu.Append(self.TBMENU_HELPCENTRE, u"帮助中心")
        menu.AppendSeparator()

#         profile = ProfileFunc.getUser()
#         if profile:
#             menu.Append(self.TBMENU_UNLOGIN, self.nickName)
#         else:
#             menu.Append(self.TBMENU_UNLOGIN, u"帐号未登入")
        if self.frame.hasUpdatePacket:
            menu.Append(self.TBMENU_PRODUCTVERSION, u"V" + PopoConfig.VersionInfo + u" (有新版本可更新)")
            menu.Enable(self.TBMENU_PRODUCTVERSION, True)
        else:
            menu.Append(self.TBMENU_PRODUCTVERSION, u"V" + PopoConfig.VersionInfo)
            menu.Enable(self.TBMENU_PRODUCTVERSION, False)
        menu.AppendSeparator()
        menu.Append(self.TBMENU_CLOSE,   u"关闭")
        #menu.Enable(self.TBMENU_UNLOGIN, False)
        #menu.Enable(self.TBMENU_PRODUCTVERSION, False)

#        if not profile:
#            menu.Enable(self.TBMENU_UNLOGIN, False)
#            menu.Enable(self.TBMENU_PREFERENCES, False)
#        else:
#            menu.Enable(self.TBMENU_SETTING, False)
        return menu

    #----------------------------------------------------------------------
    def OnTaskBarActivate(self, evt):
        """"""
        pass

    #----------------------------------------------------------------------

    def OnTaskUpdate(self, evt):
        if self.frame.hasUpdatePacket:
            self.frame.Update(True)

    def OnTaskHelpCentre(self, evt):
        webbrowser.open_new_tab("http://www.paopaoyun.com/help")

    def OnTaskWebService(self, evt):
        webbrowser.open_new_tab("http://my.paopaoyun.com")

    def OnTaskBarClose(self, evt=None):
        """
        Destroy the taskbar icon and frame from the taskbar icon itself
        """
        self.frame.OnClose(evt)

    #----------------------------------------------------------------------
    def OnTaskBarleftClick(self, evt):
        pass
#        print 'OnTaskBarleftClick'

    def OnTaskBarRightClick(self, evt):
        """
        Create the right-click menu
        """
        profile = ProfileFunc.getUser()

        if not profile:
            menu = self.CreatePopupMenu(status=0)
        else:
            menu = self.CreatePopupMenu(status=1)
        self.PopupMenu(menu, name=u"泡泡云")
        menu.Destroy()

########################################################################

wxEVT_INVOKE = wx.NewEventType()
class InvokeEvent(wx.PyEvent):
    def __init__(self, func, args, kwargs):
        wx.PyEvent.__init__(self)
        self.SetEventType(wxEVT_INVOKE)
        self.__func = func
        self.__args = args
        self.__kwargs = kwargs
    def invoke(self):
        self.__func(*self.__args, **self.__kwargs)

class MainForm(wx.Frame):

    frame = None

    def __init__(self):
        wx.Frame.__init__(self, None, wx.ID_ANY, "ElastosServer", size=(640, 400), style=wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX)

        #self.SetIcon(getAppIcon())
        self.Connect(-1, -1, wxEVT_INVOKE, self.onInvoke)

        self.preferencesDlg = None
        self.registerDlg = None
        self.loginDlg = None
        
        self.tbIcon = TBIcon(self)

        self.RefreshRelayStatus(0, u'亦来云盘')

#         self.hasUpdatePacket = False
#         self.hasUpdateFrame = False
        
        #self.onUpdateInfo('', '', '')
        updateObj = Update.CUpdate()
        ver, url, hash =  updateObj.check('com.popocloud.server', PopoConfig.VersionInfo, PopoConfig.PlatformInfo)
        #ver, url, hash =  updateObj.check('com.popocloud.server', '1.0', PopoConfig.PlatformInfo)
        if ver and url:
            self.onUpdateInfo(ver, url, updateObj.fileSize)
        else:
            self.ShowLoginDlg()

        #user = ProfileFunc.getUser()

        #if not user:
#            self.panelLogin = LoginPanel(self)
        #else:
        #    ProfileFunc.setProfileDefault(user)
        #    errMsg = StartFunc.startConnect(self.fileservice, ProfileFunc.getUser(), ProfileFunc.getPassword(), ProfileFunc.getResource(), None, self)
        #    if errMsg:
        #        ShowOKMessage(self, errMsg)
        #        self.ShowLoginDlg()
        #    else:
        #        self.ShowPreferencesDlg()


        #self.Bind(wx.EVT_CLOSE, self.OnClose)

        #self.CenterOnScreen()

        #MainForm.frame = self

        #WakeUpThread = pipeThread(self)
        #WakeUpThread.start()

    #----------------------------------------------------------------------
    def onInvoke(self, evt):
        evt.invoke()

    def invokeLater(self, func, *args, **kwargs):
        self.GetEventHandler().AddPendingEvent(InvokeEvent(func, args, kwargs))

    def ChangeRelayStatus(self, status, user):
        self.invokeLater(self.RefreshRelayStatus, status, user)

    def ChangePicturesStatus(self):
        self.invokeLater(self.RefreshPicturesList)

    def RefreshRelayStatus(self, status, user=''):
        self.status = status
        if status == 0:
            icon = getTBIcon(self, status=status)
        elif status == 1:
            icon = getTBIcon(self, status=status)
        elif status == 2:
            icon = getTBIcon(self, status=status)
        elif status == 3:
            icon = getTBIcon(self, status=status)
        self.tbIcon.SetIcon(icon, user)
            
    def RefreshPicturesList(self):
        if self.preferencesDlg:
            self.preferencesDlg.RefreshPicturesList()

#     def ShowPreferencesDlg(self):
#         if not self.preferencesDlg:
#             self.preferencesDlg = PreferencesDialog.PreferencesDialog(self)
#             self.preferencesDlg.CenterOnScreen()
#         self.preferencesDlg.Show()
#         self.preferencesDlg.Raise()

    def ShowElastos(self, user):
        if not self.preferencesDlg:
            self.preferencesDlg = PreferencesDialog.ElastosDialog(self,user)
            self.preferencesDlg.CenterOnScreen()
        self.preferencesDlg.Show()
        self.preferencesDlg.Raise()

    def ShowLoginDlg(self, user=""):
        if self.preferencesDlg:
            self.preferencesDlg.Destroy()
            self.preferencesDlg = None
        self.loginDlg = LoginDialog.LoginDialog(self, user)
        self.loginDlg.CenterOnScreen()
        self.loginDlg.Show()
        self.loginDlg.Raise()

    def OnShowConfig(self, evt):
        #TODO
        webbrowser.open("http://elastos.com")
        return
        if self.registerDlg:
            self.registerDlg.Hide()
            self.registerDlg.Show()
            self.registerDlg.Raise()
            return

        if self.loginDlg:
            self.loginDlg.Hide()
            self.loginDlg.Show()
            self.loginDlg.Raise()
            return

        if self.preferencesDlg:
            self.preferencesDlg.Hide()
            self.preferencesDlg.Show()
            self.preferencesDlg.Raise()
            return

#     def setUpdateInfo(self):
#         if not self.hasUpdatePacket and not self.hasUpdateFrame:
#             self.invokeLater(self.onUpdateInfo)

    def onUpdateInfo(self, ver, url, filesize):
        self.updateDlg = UpdateUI.InfoDialog(self, ver, url, filesize)
        self.updateDlg.Show()
        #self.hasUpdateFrame = True
            
    def OnClose(self, evt):
        """
        Destroy the taskbar icon and the frame
        """
        #StartFunc.stopConnect()

        self.tbIcon.RemoveIcon()
        self.tbIcon.Destroy()
        self.Destroy()
        cherrypy.engine.exit()
        os._exit(0)

frame = None
def runMainForm(isUpdate=False, dataPath = None):
    global frame
    app = wx.App(False)
    if isUpdate:
        frame = UpdateUI.UpdateForm(dataPath)
    frame = MainForm()
    app.MainLoop()
#----------------------------------------------------------------------
# Run the program
#if __name__ == "__main__":
#    app = wx.App(False)
#    frame = MainForm().Show()
#    app.MainLoop()
