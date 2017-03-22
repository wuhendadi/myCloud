# -*- coding: utf-8 -*-

import wx
import UtilFunc
import unicodedata

SET_FOCUS = 1
KILL_FOCUS = 2
LEFT_DOWN = 3
LEFT_UP = 4
    
class BGPanel(wx.Panel):
    def __init__(self, parent, pos=wx.DefaultPosition, size=wx.DefaultSize, bmp=None):
        wx.Panel.__init__(self, parent, -1, pos=pos, size=size, style=wx.TAB_TRAVERSAL|wx.CLIP_CHILDREN)
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  
        self.bmp = bmp  
        self.Bind(wx.EVT_PAINT, self.OnPaint)

          
    def OnPaint(self,event=None):  
        dc = wx.PaintDC(self)
        if UtilFunc.isWindowsSystem(): dc = wx.GCDC(dc)  
        dc.DrawBitmap(self.bmp, 0, 0, True) 
    

class DCStaticText(wx.StaticText):  
    """ DC StaticText """  
    dc = None
    def __init__(self,parent,id,label='',  
                 pos=wx.DefaultPosition,  
                 size=wx.DefaultSize,  
                 style=0,  
                 name = 'MLStaticText'): 
        style |= wx.CLIP_CHILDREN
        wx.StaticText.__init__(self,parent,id,label,pos,size,style = style)  
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  
        if UtilFunc.isWindowsSystem():
            self.Bind(wx.EVT_PAINT, self.OnPaint)
        else:
            self.OnPaint()
          
    def OnPaint(self,event=None):  
        DCStaticText.dc = wx.PaintDC(self)
        self.Hide() 
        return

#http://blog.csdn.net/zanpen2000/article/details/5947847

class TPStaticText(wx.StaticText):  
    """ transparent StaticText """  
    def __init__(self,parent,id,label='',  
                 pos=wx.DefaultPosition,  
                 size=wx.DefaultSize,  
                 style=0,  
                 name = 'TPStaticText'):  
        style |= wx.CLIP_CHILDREN | wx.TRANSPARENT_WINDOW  
        wx.StaticText.__init__(self,parent,id,label,pos,size,style = style)  
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  
        self.Bind(wx.EVT_PAINT,self.OnPaint)
        self.style = style  
        self.size = size 
          
    def OnPaint(self,event):  
        event.Skip()  
        dc = wx.PaintDC(self)  
        dc.SetFont(self.GetFont())  
        dc.SetTextForeground(self.GetForegroundColour())              
#        dc.DrawText(self.GetLabel(), 0, 0) 
        
        label = self.GetLabel()
        width, height = self.GetClientSize()   
          
        textWidth, textHeight = dc.GetTextExtent(label)          
        textXpos = 0  
        textYpos = (height - textHeight)/2  
        
        if (self.style & wx.ALIGN_RIGHT):
            textXpos = width - textWidth
        elif (self.style & wx.ALIGN_CENTRE):
            textXpos = (width - textWidth) / 2
        
        
        dc.DrawText(label, textXpos, textYpos) 

        
class TPStaticBitmap(wx.StaticBitmap):  
    """ transparent StaticBitmap """  
    def __init__(self,parent,id,bmp,  
                 pos=wx.DefaultPosition,  
                 size=wx.DefaultSize,  
                 style=0,  
                 name = 'TPStaticBitmap'):  
        style |= wx.CLIP_CHILDREN | wx.TRANSPARENT_WINDOW   
        wx.StaticBitmap.__init__(self,parent,id,bmp,pos,size,style = style)  
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  
        self.Bind(wx.EVT_PAINT,self.OnPaint)  
          
    def OnPaint(self,event):  
        event.Skip()  
        dc = wx.GCDC(wx.PaintDC(self) )  
        dc.DrawBitmap(self.GetBitmap(), 0,0, True)

class TPButton(wx.Button):  
    """ transparent Button """  
    def __init__(self,parent,id,label='',  
                 pos=wx.DefaultPosition,  
                 size=wx.DefaultSize,  
                 style=0,  
                 name = 'TPButton'):  
        style |= wx.CLIP_CHILDREN | wx.TRANSPARENT_WINDOW | wx.NO_BORDER  
        wx.Button.__init__(self,parent,id,label,pos,size,style = style)  
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)   
        self.textColor = range(5)
        self.parent = parent
        self.status = 0
        
        (self.x, self.y) = pos
        self.x2 = self.x + 80
        self.y2 = self.y + 30
        self.RefRect = (self.x, self.y, self.x2, self.y2)
        
        self.Bind(wx.EVT_PAINT, self.OnPaint)
        self.Bind(wx.EVT_ENTER_WINDOW, self.OnFocus)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.OnKillFocus)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnDown, self)
        #self.Bind(wx.EVT_LEFT_UP, self.OnUp, self)
        
        self.status = LEFT_UP
        self.lastStatus =  None
        self.textColor[LEFT_DOWN] = (0x21, 0x47, 0x87)
        self.textColor[LEFT_UP] = (0xff, 0xff, 0xff)
        self.textColor[SET_FOCUS] = (0x00, 0x00, 0x00)
        self.textColor[KILL_FOCUS] = (0xff, 0xff, 0xff)

    
    def SetTextForeground(self, color):
        pass
        
    def DoneEvent(self, event, status):
        event.Skip()
        self.lastStatus = self.status
        self.status = status

        if (self.lastStatus == SET_FOCUS and self.status == KILL_FOCUS) or \
           (self.status == SET_FOCUS and self.lastStatus == KILL_FOCUS):
            self.Refresh()
        else:
            self.parent.RefreshRect(self.RefRect)
#            self.parent.Refresh()

    def OnFocus(self, event): 
        self.DoneEvent(event, SET_FOCUS)

    def OnKillFocus(self, event): 
        self.DoneEvent(event, KILL_FOCUS)
        
    def OnDown(self,event=None):  
        self.DoneEvent(event, LEFT_DOWN)
        
    #def OnUp(self,event=None):  
    #    self.DoneEvent(event, LEFT_UP)
    #    self.SendClickEvent()
#   #     self.Parent.Refresh()
    #    self.parent.RefreshRect(self.RefRect)
           
    def OnPaint(self,event=None):  
        dc = wx.PaintDC(self)
        dc = wx.GCDC(dc)  
        dc.SetFont(self.GetFont()) 
        dc.SetTextForeground(self.textColor[self.status]) 

        label = self.GetLabel()
        width, height = self.GetClientSize()   
        textWidth, textHeight = dc.GetTextExtent(label)  
        textXpos = (width - textWidth)/2  
        textYpos = (height - textHeight)/2  
        
        if self.status == LEFT_DOWN:
            textXpos += 2
            textYpos += 1
        dc.DrawText(label, textXpos, textYpos)

    def SendClickEvent( self ) :
        checkEvent = wx.CommandEvent( wx.wxEVT_COMMAND_BUTTON_CLICKED, self.GetId() )
        checkEvent.SetEventObject( self )
        self.GetEventHandler().ProcessEvent( checkEvent )
#        self.Refresh()

class TPBitmapButton(wx.BitmapButton):  
    """ transparent BitmapButton """  
    def __init__(self,parent,id,bitmap,  
                 pos=wx.DefaultPosition,  
                 size=wx.DefaultSize,  
                 style=0,  
                 name = 'TPBitmapButton',
                 label= None,
                 font = None):  
        style |= wx.CLIP_CHILDREN | wx.TRANSPARENT_WINDOW   
        wx.BitmapButton.__init__(self,parent,id,bitmap,pos,size,style = style) 
        self.label = label 
        self.bmp = bitmap
        self.font = font
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  
        self.Bind(wx.EVT_PAINT,self.OnPaint) 
        
#        self.Bind(wx.EVT_ERASE_BACKGROUND, self.OnEraseBackground)  
      
    def OnEraseBackground(self, evt):  
        pass       
           
    def OnPaint(self,event=None):  
        event.Skip()  
        dc = wx.GCDC(wx.PaintDC(self) )  
        dc.DrawBitmap(self.bmp, 0, 0, True) 
        
        if not self.label:
            return
        
        if self.font:
            dc.SetFont(self.font)              
        
        width, height = self.GetClientSize()   
          
        textWidth, textHeight = dc.GetTextExtent(self.label)          
        textXpos = (width - textWidth)/2   
        textYpos = (height - textHeight)/2 
        
        dc.DrawText(self.label, textXpos, textYpos) 

class TPCheckBox(wx.Control):  
    """ transparent checkbox  
        Important: The parent window must have wx.TRANSPARENT_WINDOW flag!!!! 
    """  
    def __init__(self,parent,id,label='',  
                 pos=wx.DefaultPosition,  
                 size=wx.DefaultSize,  
                 style=0,  
                 name = 'TPCheckBox'):  
        style |= wx.CLIP_CHILDREN | wx.TRANSPARENT_WINDOW | wx.NO_BORDER 
        wx.Control.__init__(self,parent,id,pos,size,style = style)    
        self.SetBackgroundStyle(wx.BG_STYLE_CUSTOM)  
        self.textColor = None
        self._spacing = 3
        self.is_check = False
        self.parent = parent
        self.label = label

        self.Bind(wx.EVT_PAINT, self.OnPaint)
#        self.Bind(wx.EVT_ENTER_WINDOW, self.OnFocus)
#        self.Bind(wx.EVT_LEAVE_WINDOW, self.onKillFocus)
        self.Bind(wx.EVT_LEFT_DOWN, self.OnDown, self)
#        self.Bind(wx.EVT_LEFT_UP, self.OnUp, self)
  
    def SetTextForeground(self, color):
        self.textColor = color

    def OnFocus(self, event): 
        event.Skip()

    def onKillFocus(self, event): 
        event.Skip()
        
    def OnDown(self,event=None):  
        self.is_check = not self.is_check
        self.parent.Refresh()
        event.Skip()
        
    def OnUp(self,event=None):  
        event.Skip()
        
        
    def Draw(self, dc):  
#        dc.SetBackground(wx.TRANSPARENT_BRUSH )  
#        dc.Clear()  
         
        render = wx.RendererNative.Get()  

        label = self.label#self.GetLabel()  
        spacing = self._spacing  
          
        width, height = self.GetClientSize() 
          
        textWidth, textHeight = dc.GetTextExtent(label)  
        cboxWidth, cboxHeight = 13, 13          
        cboxXpos = 0  
        cboxYpos = (height - textHeight)/2
        textXpos = cboxWidth + spacing  
        textYpos = (height - textHeight)/2
                
        if not self.IsChecked():  
            render.DrawCheckBox(self, dc, (cboxXpos, cboxYpos, cboxWidth, cboxHeight))  
        else:  
            render.DrawCheckBox(self, dc, (cboxXpos, cboxYpos, cboxWidth, cboxHeight), wx.CONTROL_CHECKED)  
             
        dc.SetFont(self.GetFont())
        dc.DrawText(label, textXpos, textYpos)   
  
    def OnPaint(self, event=None): 
        dc = wx.PaintDC(self)
        if UtilFunc.isWindowsSystem(): dc = wx.GCDC(dc)  
        dc.SetFont(self.GetFont()) 
        if self.textColor:
            dc.SetTextForeground(self.textColor) 
        self.Draw(dc)
        return
   
    def IsChecked(self):
        return self.is_check
    
    def GetValue(self):
        return self.is_check

def ShowOKMessage(parent,msn):        
    dlg = wx.MessageDialog(parent, msn,
                               u'提示',
                               wx.OK | wx.ICON_INFORMATION
                               #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                               )
    dlg.ShowModal()
    dlg.Destroy()

def ShowOKCancelMessage(parent,msn):        
    dlg = wx.MessageDialog(parent, msn,
                               u'提示',
                               wx.OK | wx.ICON_INFORMATION | wx.CANCEL
                               #wx.YES_NO | wx.NO_DEFAULT | wx.CANCEL | wx.ICON_INFORMATION
                               )
    ret = dlg.ShowModal()
    dlg.Destroy()
    
    return ret

def _get_hz_string_width(string):
    lens = 0
    for ch in string:
        if isinstance(ch, unicode):
            if unicodedata.east_asian_width(ch) != 'Na':
                lens +=1
            else:
                lens +=1
        else:
            lens +=1
    return lens

def GetShortString(string, length=None):
    s = []
    pos = 0
    for ch in string:
        s.append(ch)
        if isinstance(ch, unicode):
            if unicodedata.east_asian_width(ch) != 'Na':
                pos +=2
            else:
                pos +=1
        else:
            pos +=1
        if length != None and _get_hz_string_width(''.join(s))  >= length:
            return ''.join(s) + '...'
    return ''.join(s)
