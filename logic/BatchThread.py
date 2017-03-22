# -*- coding: utf-8 -*-

import threading
import os
import UtilFunc
import traceback
import ProfileFunc
import shutil
import Log

class BatchThread(threading.Thread):
    def __init__(self, operateInfo, path, action, target, onExist):
        threading.Thread.__init__(self)
        self.info    = operateInfo
        self.paths   = path
        self.onExist = onExist
        self.action  = action
        self.target  = target
        
    def _isExist(self, path):
        if os.path.exists(path):
            if self.onExist.lower() == 'rename':
                path = UtilFunc.setFileName(path)
            elif self.onExist.lower() == 'skip':
                return None
            elif self.onExist.lower() == 'overwrite':
                if not self._remove(path):
                    return None
        return path
        
    def _OperateFile(self, path):
        if self.action == 'delete':
            ret = self._remove(path)
        elif self.action == 'copy':
            ret = self._copyFile(path, self.target)
        elif self.action == 'move':
            ret = self._move(path, self.target)
        
        if ret:
            self.info['successFiles'] += 1
        else:
            self.info['skipedFiles'] += 1
            self.info['error'].append({'errCode':462,'parh':path,'action':self.action})
        
    def _remove(self, path):
        if not path: return False
        try:
            if not os.path.isdir(path):
                os.remove(path)
            else:
                shutil.rmtree(path)
            return True
        except Exception, e:
            Log.error('remove file failed!!! Reason[%s]'%e)
            return False

    def _moveFolder(self, src, dst):
        real_dst = dst
        try:
            os.rename(src, real_dst)
        except OSError:
            if self.info['finished'] != 0:
                return
            if os.path.isdir(src):
                if shutil._destinsrc(src, dst):
                    raise Exception, "Cannot move a directory '%s' into itself '%s'." % (src, dst)
                self.copytree(src, real_dst, symlinks=True)
                self.rmtree(src)
                sqlStr = 'update mediafolder set url=? where url=?'
                ProfileFunc.execAllScanFolderSql(sqlStr,(real_dst,src))
            else:
                shutil.copy2(src, real_dst)
                os.unlink(src)

    def _move(self, oldPath=None, newPath=None):
        if not oldPath: return False
        try: 
            oldPath = ProfileFunc.slashFormat(oldPath)
            newPath = ProfileFunc.slashFormat(newPath)
            if not os.path.exists(oldPath):
                return False
            if not os.path.exists(newPath):
                UtilFunc.makeDirs(newPath)
            
            newPath = os.path.join(newPath, shutil._basename(oldPath))
            newPath = self._isExist(newPath)
            if not newPath: return False
            if os.path.isdir(oldPath):
                if not os.path.exists(newPath):
                    UtilFunc.makeDirs(newPath)
            self._moveFolder(oldPath, newPath)
            return True
        except Exception, e:
            Log.error('Move file failed!!! Reason[%s]'%e)
            return False  
    
    def copytree(self, src, dst, symlinks=False, ignore=None):
        if self.info['finished'] != 0:
            return
        names = os.listdir(src)
        if ignore is not None:
            ignored_names = ignore(src, names)
        else:
            ignored_names = set()
        
        if not os.path.exists(dst):
            UtilFunc.makeDirs(dst)
            
        errors = []
        for name in names:
            if self.info['finished'] != 0:
                break
            if name in ignored_names:
                continue
            srcname = os.path.join(src, name)
            dstname = os.path.join(dst, name)
            try:
                if symlinks and os.path.islink(srcname):
                    linkto = os.readlink(srcname)
                    os.symlink(linkto, dstname)
                elif os.path.isdir(srcname):
                    self.copytree(srcname, dstname, symlinks, ignore)
                else:
                    shutil.copy2(srcname, dstname)
            except Exception, err:
                errors.extend(err.args[0])
            except EnvironmentError, why:
                errors.append((srcname, dstname, str(why)))
        try:
            shutil.copystat(src, dst)
        except OSError, why:
            if WindowsError is not None and isinstance(why, WindowsError):
                pass
            else:
                errors.extend((src, dst, str(why)))
        if errors:
            raise Exception, errors
    
    def _copyFile(self, oldPath=None, newPath=None):
        if not oldPath: return False
        try:
            oldPath = ProfileFunc.slashFormat(oldPath)
            newPath = ProfileFunc.slashFormat(newPath)
            if not os.path.exists(oldPath):
                return False
            if not os.path.exists(newPath):
                UtilFunc.makeDirs(newPath)
            real_dst = os.path.join(newPath, shutil._basename(oldPath))
            real_dst = self._isExist(real_dst)
            if not real_dst : return False
            if os.path.isdir(oldPath):
                self.copytree(oldPath, real_dst)
            else :
                shutil.copyfile(oldPath, real_dst)
            return True
        except Exception, e:
            Log.error('Copy file failed!!! Reason[%s]'%e)
            return False
        
    def run(self):
        try:
            for path in self.paths:
                folder = os.path.dirname(path)
                if folder == self.target or path == self.target:
                    self.info['skipedFiles'] += 1
                elif not os.path.exists(path):
                    Log.debug('path is not exists,[%s]!!!'%path)
                    self.info['error'].append({'errCode':464,'parh':path,'action':self.action})
                else:
                    self._OperateFile(path)
                self.info['finishedFiles'] += 1
        except:
            Log.error(traceback.format_exc())
            self.info['error'].append({'errCode':462,'parh':[],'action':self.action})
            
        self.info['finished'] = 1
        Log.info('OperateFileThread finished')  
        
