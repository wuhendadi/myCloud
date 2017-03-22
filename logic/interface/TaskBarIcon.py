# -*- coding: utf-8 -*-

import wx
import os
import UtilFunc

#http://stackoverflow.com/questions/2015969/wxpython-systray-icon-menu
#http://blog.csdn.net/kiki113/article/details/4067084
ID_OPEN_OPTION = wx.NewId()
ID_ABOUT_OPTION = wx.NewId()
ID_RUN_AT_STARTUP_OPTION = wx.NewId()
ID_OPEN_BROWSER_OPTION = wx.NewId()

class ECloudTaskIcon(wx.TaskBarIcon):

    def __init__(self, parent, icon, tooltip):
        wx.TaskBarIcon.__init__(self)
        self.SetIcon(icon, tooltip)
        self.parent = parent
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnLeftDClick)
        self.CreateMenu()

    def CreateMenu(self):
        self.Bind(wx.EVT_TASKBAR_RIGHT_UP, self.OnPopup)
        self.menu = wx.Menu()
        self.menu.Append(ID_OPEN_OPTION, '&Open...')
        self.menu.AppendSeparator()
        self.menu.Append(ID_RUN_AT_STARTUP_OPTION, '&Run at window startup', kind=wx.ITEM_CHECK)
        self.menu.Append(ID_OPEN_BROWSER_OPTION, '&Open browser on launch', kind=wx.ITEM_CHECK)
        self.menu.AppendSeparator()
        self.menu.Append(ID_ABOUT_OPTION, '&About')
        self.menu.Append(wx.ID_EXIT, 'E&xit')
        self.Bind(wx.EVT_MENU, self.OnOpen, id=ID_OPEN_OPTION) 
        self.Bind(wx.EVT_MENU, self.OnAbout, id=ID_ABOUT_OPTION)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        
    def OnOpen(self, event):
        UtilFunc.openSysmemBrower('http://127.0.0.1:%d'%UtilFunc.getWebServerPort())
    
    def OnAbout(self, event):
        description = """Elastos ECloud"""

        licence = """Elastos ECloud is free software; you can redistribute it and/or modify it 
under the terms of the GNU General Public License as published by the Free Software Foundation; 
either version 2 of the License, or (at your option) any later version.

File Hunter is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; 
without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  
See the GNU General Public License for more details. You should have received a copy of 
the GNU General Public License along with Elastos ECloud"""

        info = wx.AboutDialogInfo()

        info.SetIcon(wx.Icon(r"F:\work\workspace\python\ECloud\src\ui\test.png", wx.BITMAP_TYPE_PNG))
        info.SetName('Elastos ECloud')
        info.SetVersion('1.0')
        info.SetDescription(description)
        info.SetCopyright('(C) 2011 Kortide')
        info.SetWebSite('http://www.kortide.com.cn')
        info.SetLicence(licence)
        info.AddDeveloper('Kortide')
        info.AddDocWriter('Kortide')
        info.AddArtist('Kortide')
        info.AddTranslator('Kortide')

        wx.AboutBox(info)
        
    def OnExit(self, event):
        self.parent.Close()

    def OnPopup(self, event):
        self.PopupMenu(self.menu)

    def OnLeftDClick(self, event):
        #if self.parent.IsIconized():
        #    self.parent.Iconize(False)
        #if not self.parent.IsShown():
        #    self.parent.Show(True)
        #self.parent.Raise()
        return self.OnOpen(event)
    

class ECloudApp(wx.App):
    def OnInit(self):
        frame = TaskbarFrame("Taskbar", (-50, -60), (1, 1))
        frame.Hide()
        #self.SetTopWindow(frame)
        
        return True
    
    def OnExit(self):
        os._exit(0)
    
class TaskbarFrame(wx.Frame):
    def __init__(self, title, pos, size):
        wx.Frame.__init__(self, None, -1, title, pos, size)
        # create a menu
        iconFile = os.path.join(UtilFunc.module_path(), "IconECloud.ico")
        self.TrayIcon  = ECloudTaskIcon(self, wx.Icon(iconFile, wx.BITMAP_TYPE_ICO), "ECloud")
        self.Bind(wx.EVT_ICONIZE, self.OnIconify)
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        
    def OnIconify(self, event):
        self.Hide()
        
    def OnClose(self, event):
        self.TrayIcon.Destroy()
        self.Destroy()
                
