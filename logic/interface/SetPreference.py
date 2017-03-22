# -*- coding: utf-8 -*-
import wx
import os
import time
import UtilFunc
import ProfileFunc
import locale
import PopoConfig
import SqliteFunc
from TPControls import BGPanel
from LoginDialog import parent_dir

set_back           = "set_back.png"
set_info_bt        = "set_info_bt.png" 
set_info_bt_ch     = "set_info_bt_ch.png"
set_cloud          = "set_cloud.png"
set_cloud_ch       = "set_cloud_ch.png"
set_delete         = 'res/delet.png'
set_edit           = "set_edit.png"
set_add            = "set_add.png"
set_add_choose     = "set_add_choose.png"
set_cloudset       = "set_cloudset.png" 
set_info           = "set_info.png"
set_close_choose   = "set_close_choose.png"

sys_lang = locale.getdefaultlocale()[0]
if sys_lang == "zh_CN":
    parent_dir  = "res/zh_cn"
    shut_down   = u"关闭"
    defaultCode = 'gbk'
elif sys_lang == 'en_US':
    parent_dir  = "res/zh_tw"
    shut_down   = "close"
    defaultCode = 'utf-8'
elif sys_lang == 'zh_TW':
    parent_dir  = "res/zh_tw"
    shut_down   = u"關閉"
    defaultCode = 'big5'
else:
    parent_dir  = "res/zh_tw"
    shut_down   = "close"
    defaultCode = 'utf-8'

def changePath(text, length = 270):
    newText = text[:length]
    text = text[length:]
    while text:
        newText += '\n' + text[:270]
        text = text[length:]
            
    return newText

class ShowSettings(wx.Dialog):
    def __init__(self, parent, user):
        wx.Dialog.__init__(self, None, -1, u"Settings",size=(548,353),style=wx.NO_BORDER)
        
        if 'wxMac' in wx.PlatformInfo:
            device_name = 'ElastosPCServer_OSX'       
        else:
            device_name = 'ElastosPCServer' 
            
        self.parent= parent
        self.user = user
        self.picture_path =ProfileFunc.GetPictureFolder()
        self.add_path = ''
        #self.add_path_list = []

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_back))
        bgpng = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        size = bgpng.GetSize()
        self.SetClientSize(size)
        self.bgParent = BGPanel(self, size=size, bmp=bgpng)

        self.bgParent.Bind(wx.EVT_LEFT_DOWN, self.OnPanelLeftDown)
        self.bgParent.Bind(wx.EVT_MOTION, self.OnPanelMotion)
        self.bgParent.Bind(wx.EVT_LEFT_UP, self.OnPanelLeftUp)
    
        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_info_bt))
        self.set_account = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_account_bt = wx.BitmapButton(self.bgParent, -1, self.set_account, pos=(18, 45), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.Info_set, self.set_account_bt)

        self.cloud_info_panel = cloudinfopanel(self.bgParent, self.user, device_name)

        self.cloud_set_panel = cloudsetpanel(self.bgParent)
        self.cloud_set_panel.Hide()
    

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_cloud))
        set_cloud_one = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_clout_bt = wx.BitmapButton(self.bgParent, -1, set_cloud_one , pos=(124,45), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.Cloud_set, self.set_clout_bt)

        imgPath = os.path.join(UtilFunc.module_path(), 'res/set_close1.png')
        set_close = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_close_bt = wx.BitmapButton(self.bgParent, -1, set_close, pos=(528, 12), style = wx.NO_BORDER)

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%('res', set_close_choose))
        set_close_choose_one = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_close_bt.SetBitmapHover(set_close_choose_one)
        self.set_close_bt.SetToolTipString(shut_down)
        self.Bind(wx.EVT_BUTTON, self.Close_set, self.set_close_bt)
        
    def Cloud_set(self, evet):
        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_info_bt_ch))
        set_account_ch = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_account_bt.SetBitmapLabel(set_account_ch) 

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_cloud_ch))
        set_cloud_ch_one  = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_clout_bt.SetBitmapLabel(set_cloud_ch_one)
        #self.set_info_wx.Hide()
        self.cloud_info_panel.Hide()
        self.cloud_set_panel.Show()

    def Info_set(self, evet):
        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_info_bt))
        set_info_bt_one = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_account_bt.SetBitmapLabel(set_info_bt_one)

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_cloud))
        set_cloud_one = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_clout_bt.SetBitmapLabel(set_cloud_one)
        #self.set_info_wx.Show()
        self.cloud_info_panel.Show()
        self.cloud_set_panel.Hide()
        #self.set_cloudset_wx.Hide()

    def Close_set(self, evet):
        self.Destroy()

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
        if self.bgParent.HasCapture():
            self.bgParent.ReleaseMouse()


class cloudinfopanel(wx.Window):
    def __init__(self, parent, user, device_name):
        self.user = user
        wx.Window.__init__(self, parent,  -1, pos=(12, 73), size=(526,281))
        self.SetBackgroundColour(wx.RED)

        self.parent = parent

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_info))
        bgpng = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        size = bgpng.GetSize()
        self.SetClientSize(size)
        self.bgParent = BGPanel(self, size=size, bmp=bgpng)

        #device name
        wx.StaticText(self.bgParent, -1, device_name, (112,37), size=(120,-1)).SetBackgroundColour((0xFF, 0xFF, 0xFF))
        #device info
        wx.StaticText(self.bgParent, -1, UtilFunc.getSN(), (112,67), size=(120,-1)).SetBackgroundColour((0xFF, 0xFF, 0xFF))
        #software version
        wx.StaticText(self.bgParent, -1, PopoConfig.VersionInfo , (112,98), size=(120,-1)).SetBackgroundColour((0xFF, 0xFF, 0xFF))

        #elastos id 
        wx.StaticText(self.bgParent, -1, u"" , (112,168), size=(140,-1)).SetBackgroundColour((0xFF, 0xFF, 0xFF))
        #telephone num
        if '@' not in self.user and str(self.user) == 15:
            tel_num = self.user
        else:
            tel_num = ''
        wx.StaticText(self.bgParent, -1, tel_num, (112,196), size=(140,-1)).SetBackgroundColour((0xFF, 0xFF, 0xFF))
        #email
        if '@' not in self.user:
            email = ''
        else:
            email = self.user
        wx.StaticText(self.bgParent, -1, email, (112,222), size=(240,-1)).SetBackgroundColour((0xFF, 0xFF, 0xFF))

        #imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_edit))
        #set_edit_one  = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        #self.btn_set_edit = wx.BitmapButton(self.bgParent, -1, set_edit_one, pos=(187, 35), style = wx.NO_BORDER)
        #self.Bind(wx.EVT_BUTTON, self.Edit_device_info, self.btn_set_edit)
        
    def Edit_device_info(self, evet):
        wx.TextCtrl(self.bgParent, -1, u"",(112,36), size=(60,20), style = wx.NO_BORDER)


class cloudsetpanel(wx.Window):
    def __init__(self, parent):
        wx.Window.__init__(self, parent, -1, pos=(12, 73), size=(526,281))
        self.SetBackgroundColour(wx.RED)

        self.parent = parent

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir,set_cloudset))
        bgpng = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        size = bgpng.GetSize()
        self.SetClientSize(size)
        self.bgParent = BGPanel(self, size=size, bmp=bgpng)

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_add))
        set_add_one  = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_add_bt = wx.BitmapButton(self.bgParent, -1, set_add_one, pos=(347, 33), style = wx.NO_BORDER)

        imgPath = os.path.join(UtilFunc.module_path(), '%s/%s'%(parent_dir, set_add_choose))
        set_add_one  = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.set_add_bt.SetBitmapHover(set_add_one)
        self.Bind(wx.EVT_BUTTON, self.OnBrowser, self.set_add_bt)

        self.scan_path= wx.TextCtrl(self.bgParent, -1, ProfileFunc.GetPictureFolder() , (118,36), size=(218,22))
        self.scan_path.SetBackgroundColour((0xFF, 0xFF, 0xFF))
        self.scan_path.Disable()

        self.file_panels = FileScanListPannel(self.bgParent)
        self.file_panels.showList()

    def OnBrowser(self, evt):
        # In this case we include a "New directory" button.
        dlg = wx.DirDialog(self, "Choose a directory:",
                          style=wx.DD_DEFAULT_STYLE
                           #| wx.DD_DIR_MUST_EXIST
                           #| wx.DD_CHANGE_DIR
                           )

        # If the user selects OK, then we process the dialog's data.
        # This is done by getting the path data from the dialog - BEFORE
        # we destroy it.
        add_path = ''
        if dlg.ShowModal() == wx.ID_OK:
            add_path = dlg.GetPath().replace('\\','/')
            self.scan_path.SetValue(add_path)

        # Only destroy a dialog after you're done with it.
        dlg.Destroy()

        if add_path:
            strSql = 'replace into folders(type, partpath, path, needScan, scanning) values(?,?,?,1,0)'
            SqliteFunc.execSql(strSql, ('all', UtilFunc.getDiskPath(add_path), add_path))
            ProfileFunc.addToLibrary(add_path, True, 'all', True)
            #ProfileFunc.getMainServer().scanFolderMoniter.setMediaFolder([{'folder':add_path,'type':'all'}],[])
            time.sleep(0.5)
            self.file_panels.showList()

class FileScanListPannel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1, pos=(20, 86), size=(490,175))
        self.SetBackgroundColour(wx.WHITE)
        self.virtual_height = 165

        self.panelBg = wx.ScrolledWindow(self, -1, pos=(0, 6), size=(490,165), style=wx.SIMPLE_BORDER)
        self.panelBg.SetBackgroundColour(wx.WHITE)
        self.panelBg.SetScrollbars(1, 1, 1, 86)
        self.panelBg.SetVirtualSize((500, 265))

        self.items = []

    def showList(self, evt=None):
        for item in self.items:
            item.Destroy()

        data = ProfileFunc.getLibraryFolderInfo()
        self.panelBg.Scroll(1, 1)
        self.items = []
        
        height = 0
        for info in data:
            add_path = UtilFunc.formatPath(info['path'])
            y = height + 10
            self.panelBg.SetVirtualSize((500, y+40))
            item = FolderPannel(self.panelBg, self, (0, y), height, path=add_path)
            height = height + item.height
            self.items.append(item)

class FolderPannel(wx.Window):
    def __init__(self, parent, filepannel, pos, p_height, path=""):

        self.height = 35  
        wx.Window.__init__(self, parent, -1, pos, size=(490, self.height))

        self.filepannel = filepannel
        if UtilFunc.isWindowsSystem():
            self.path = path.encode(defaultCode)
        else:
            self.path = path
        
        self.txt_name= wx.StaticText(self, -1, 'Folder'+str(p_height/30+1), (5, -1), size=(180, self.height))
        self.txt = wx.StaticText(self, -1, changePath(self.path, 54), (75, -1), size=(280, self.height))

        imgPath = os.path.join(UtilFunc.module_path(), set_delete)
        delete_png = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
        self.delete_bt= wx.BitmapButton(self, -1, delete_png, pos=(460, -1), style = wx.NO_BORDER)
        self.Bind(wx.EVT_BUTTON, self.delPath, self.delete_bt)

    def delPath(self, evt=None):
        if UtilFunc.isWindowsSystem():
            self.path = self.path.decode(defaultCode)
        if self.path != ProfileFunc.GetPictureFolder():
            SqliteFunc.tableRemove(SqliteFunc.TB_FOLDER, 'path = ?',(self.path,))
            ProfileFunc.removeFromLibrary(self.path)
            
            time.sleep(0.5)
            self.filepannel.showList()

