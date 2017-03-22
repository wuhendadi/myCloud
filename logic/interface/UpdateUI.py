# -*- coding: utf-8 -*-

import os
import wx
import wx.animate
import time
import UtilFunc
import Frame
import thread
import tempfile, urllib
import popoUpdate as Update

UPDATE_INFO = 1
UPDATE_PROCESS = 2

def msgBox(msg, style = wx.OK):
    dlg=wx.MessageDialog(None ,msg, u"提示", style | wx.ICON_QUESTION )
    ret = dlg.ShowModal()
    dlg.Destroy()
    return ret

    
class UpdateForm(wx.Frame):
     
    def __init__(self, file):
        wx.Frame.__init__(self, None, wx.ID_ANY, "ElastosServer", size=(640, 400), style=wx.SYSTEM_MENU | wx.CAPTION | wx.CLOSE_BOX)
         
        self.Connect(-1, -1, Frame.wxEVT_INVOKE, self.onInvoke)  
        self.processDlg = ProcessDialog()
        self.processDlg.Show()
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.CenterOnScreen()
        thread.start_new_thread(self.update, (file))
        
    def update(self, file):
        if os.path.exists(file):
            os.remove(file)
        import shutil
        shutil.copy2(UtilFunc.module_path(), os.path.abspath(file))
        self.finishUpdate(path)
        
    def onInvoke(self, evt):  
        evt.invoke()  
         
    def invokeLater(self, func, *args, **kwargs):  
        self.GetEventHandler().AddPendingEvent(Frame.InvokeEvent(func, args, kwargs))
          
    def finishUpdate(self, path):
        self.invokeLater(self.RebootMessage, path)
              
    def RebootMessage(self, path):
        if self.processDlg:
            self.processDlg.Hide()
            self.processDlg.Destroy()
        dlg= wx.MessageDialog(None ,u"\r\n新的版本已更新, 是否启动？" , u"提示", wx.OK | wx.CANCEL | wx.ICON_QUESTION)
        ret = dlg.ShowModal()
        dlg.Destroy()
        if ret == wx.ID_OK:
            path = os.path.join(path, 'popoCloud.exe')
            os.popen('start "" "%s"'%path).close()
        self.Close()
 
    def OnClose(self, evt):
        self.Destroy()
        os._exit(0)
        
class ProcessDialog(wx.Dialog):
 
    def __init__(self):
        '''
        Constructor
        '''
        wx.Dialog.__init__(self, None, -1, u"软件安装中")
 
        self.SetClientSize((300, 75))
        self.CenterOnScreen()
         
        self.SetBackgroundColour((0xEC, 0xF6, 0xFC))
        ag_fname = os.path.join(UtilFunc.module_path(), 'res/loading.gif')
        ag = wx.animate.GIFAnimationCtrl(self, -1, ag_fname, pos=(40, 21))
        # clears the background
        ag.GetPlayer().UseBackgroundColour(True)
        # continuously loop through the frames of the gif file (default)
        ag.Play()
        label = wx.StaticText(self, -1, u"正在安装中,请稍等...", (87, 31))
        
        
class GuageFrame(wx.Frame):  
    def __init__(self, targetver, url, tempZipFile, fileSize=1000):  
        wx.Frame.__init__(self, None, -1, u'软件更新包下载中:  ' + targetver , size = (500, 180))  
        panel = wx.Panel(self, -1)  
        panel.SetBackgroundColour("white") 
        self.count = 0
        self.complited = 0
        self.tempfile = tempZipFile
        self.fileSize = fileSize
        self.url = url
        self.gauge = wx.Gauge(panel, -1, int(self.fileSize), (30, 30), (420, 30), style = wx.GA_PROGRESSBAR)  
        self.gauge.SetBezelFace(3)  
        self.gauge.SetShadowWidth(3)  
        self.Bind(wx.EVT_IDLE, self.OnIdle)
        self.begin = wx.StaticText(panel, -1, '0', (30, 60), (50, 20))
        self.end = wx.StaticText(panel, -1, str(self.fileSize), (350, 60), (100, 20), wx.ALIGN_RIGHT)
        wx.StaticText(panel, -1, u'已用时间: ', (30, 90), (80, 20))
        self.timer = wx.StaticText(panel, -1, '00:00:00', (110, 90), (100, 20))
        self.Center(True)
        self.startTime = time.time()
        thread.start_new_thread(self.downloadFile, (self.url, self.tempfile,))
        
    def downloadFile(self, url, dst):
        try:
            ret = urllib.urlretrieve(url, dst)
            (tmpdir, ext) = os.path.splitext(dst)
            if ext == 'zip':
                if not os.path.exists(tmpdir): os.mkdir(tmpdir)
                UtilFunc.unZip(dst, tmpdir)
                path = os.path.join(tmpdir, 'ElastosServer.exe')
            else:
                path = dst
                
            cmd = 'start '+ path+' update "' + UtilFunc.module_path() + '"'
            cmd = cmd.encode("GBK")
            os.popen(cmd).close()
            
        except Exception, e:
            print e
            dlg= wx.MessageDialog(None ,u"\r\n版本更新失败, 请重新下载完整版？" , u"提示", wx.OK | wx.CANCEL | wx.ICON_WARNING)
            ret = dlg.ShowModal()
            dlg.Destroy()

        os._exit(0)
            
    def OnShow(self, filePath):
        ext = UtilFunc.getFileExt(filePath)
        if ext == 'exe':
            import shutil
            shutil.copy2(filePath, UtilFunc.module_path())
            filepath = os.path.join(UtilFunc.module_path(), 'popoCloud.exe')
            #os.remove(filePath)
        else:
            UtilFunc.unZip(filePath, UtilFunc.module_path())
        self.RebootMessage(path)
    
            
    def OnIdle(self, event): 
        if os.path.exists(self.tempfile): 
            self.count = os.path.getsize(self.tempfile)  
        
        self.begin.SetLabel(str(self.count))
        self.gauge.SetValue(self.count)
        curr = int(time.time() - self.startTime)
        minute = '0' + str(curr / 60) if curr / 60 < 10 else str(curr / 60)
        seconds = '0' + str(curr % 60) if curr % 60 < 10 else str(curr % 60) 
        self.timer.SetLabel('00:%s:%s'%(minute,seconds))

        time.sleep(0.1)  


class InfoDialog(wx.Dialog):

    def __init__(self, parent, ver, url, filesize):
        '''
        Constructor
        '''
        wx.Dialog.__init__(self, None, -1, u"软件更新", size=(400, 209))

        self.frame = parent
#        self.CenterOnScreen()
        self.ver = ver
        self.url = url
        self.filesize = filesize
        self.SetBackgroundColour(wx.WHITE)
#         imgPath = os.path.join(UtilFunc.module_path(), 'res/checknew.png')
#         img = wx.Image(imgPath, wx.BITMAP_TYPE_PNG).ConvertToBitmap()
#         btn = wx.StaticBitmap(self, -1, img, pos=(20, 21))
        from PopoConfig import VersionInfo
        wx.StaticText(self, -1, u"检测到泡泡云软件有新版本，是否立即升级？", (52, 25))
        wx.StaticText(self, -1, u"当前版本："+ VersionInfo, (52, 55))
        wx.StaticText(self, -1, u"最新版本："+ self.ver, (52, 85))
        self.ln = wx.StaticLine(self, -1, pos=(0, 125), size=(400, 1),style=wx.LI_HORIZONTAL)
        self.ln.SetForegroundColour((0xCD, 0xDD, 0xEC))
        panel = wx.Panel(self, pos=(0,126), size=(400, 50))
        panel.SetBackgroundColour((0xE6, 0xF5, 0xFE))

        btn = wx.Button(panel, wx.ID_OK, u"更新", pos=(53, 10))
        self.Bind(wx.EVT_BUTTON, self.OnUpdate, btn)
        btn = wx.Button(panel, wx.ID_CANCEL, u"取消", pos=(250, 10))
        self.Bind(wx.EVT_BUTTON, self.OnNext, btn)
        
        
    def Update(self, update=False):
        if update:
            ext = UtilFunc.getFileExt(self.url)
            if not ext: ext = 'exe' 
            tempZipFile = tempfile.mktemp(suffix='.' + ext)
            GuageFrame(self.ver, self.url, tempZipFile.replace('\\', '/'), self.filesize).Show()
        else:
            self.frame.ShowLoginDlg()

        self.Destroy()
        
#         if self.hasUpdateFrame:
#             self.hasUpdateFrame = False
# 
#         if not self.hasUpdatePacket:
#             self.hasUpdatePacket=True
#             if self.preferencesDlg:
#                 self.preferencesDlg.panel_list[0].ShowUpdateInfo()
                
    def OnUpdate(self, evt):
        self.Update(True)

    def OnNext(self, evt):
        self.Update(False)

if __name__ == '__main__':
    import os
    path = 'c:/users/sunnyz~1/appdata/local/temp/tmpzuk2my.exe'
    os.popen('start ' + path).close()
