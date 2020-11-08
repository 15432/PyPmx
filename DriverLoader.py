#this class performs driver-related tasks
#register / delete / start / stop / ioctl

#driver binaries are taken from the 'Drivers' folder

import platform
import os
import errno
import win32service, win32serviceutil, win32file

def is_x64():
    return platform.machine().endswith('64')

class PmxDriver:
    #takes the driver name, checks if the driver file is present in the folder
    def __init__(self, name):
        self.name = name
        if is_x64():
            file_name = name + "_x64.sys"
        else:
            file_name = name + "_x86.sys"
        file_path = os.path.join("Drivers", file_name)
        if not os.path.isfile(file_path):
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), file_path)
        self.file_path = file_path

    #stops the driver to prevent others using it
    def __del__(self):
        try:
            self.StopDriver()
        except:
            pass #if there was no driver, just leave it
        
    #checks if the driver is installed
    def IsDriverInstalled(self):
        try:
            win32serviceutil.QueryServiceStatus(self.name)
        except BaseException as e: 
            if e.args[0] == 1060: #not installed
                return False
            else:
                raise #other error
        return True

    #puts the driver into Windows/System32/drivers folder
    def SaveDriverFile(self):
        winPath = os.environ['WINDIR']
        sysNativePath = os.path.join(winPath, "Sysnative")
        sys32Path = os.path.join(winPath, "System32")
        if os.path.exists(sysNativePath):
            sys32Path = sysNativePath
        targetPath = os.path.join(sys32Path, "drivers\\" + self.name + ".sys")
        if os.path.isfile(targetPath):
            return
        file_data = open(self.file_path, "rb").read()
        open(targetPath, "wb").write(file_data)
        
    #registers the driver for further startup
    def RegisterDriver(self):
        serviceManager = win32service.OpenSCManager(None, None, win32service.SC_MANAGER_ALL_ACCESS)
        driverPath = os.path.join(os.environ['WINDIR'], 'system32\\drivers\\' + self.name + '.sys')
        try:
            serviceHandle = win32service.CreateService(serviceManager, self.name, self.name,
                win32service.SERVICE_ALL_ACCESS, win32service.SERVICE_KERNEL_DRIVER, win32service.SERVICE_DEMAND_START, win32service.SERVICE_ERROR_NORMAL,
                driverPath, None, 0, None, None, None)
        except:
            return False
        finally:
            win32service.CloseServiceHandle(serviceManager)
        win32service.CloseServiceHandle(serviceHandle)
        return True

    #unregisters the driver from the system
    def UnregisterDriver(self):
        try:
            win32serviceutil.RemoveService(self.name)
        except:
            pass
            
    #stops the driver
    def StopDriver(self):
        win32serviceutil.StopService(self.name)
        
    #starts the driver
    def RunDriver(self):
        win32serviceutil.StartService(self.name)

    #tries to start the driver
    def ReinstallDriver(self):
        self.SaveDriverFile()
        if not self.IsDriverInstalled():
            self.RegisterDriver()
        self.RunDriver()

    #tries to open the driver by name
    def OpenDriver(self):
        try:
            handle = win32file.CreateFile("\\\\.\\" + self.name, 
                                                win32file.FILE_SHARE_READ | win32file.FILE_SHARE_WRITE, 
                                                0, None, win32file.OPEN_EXISTING, 
                                                win32file.FILE_ATTRIBUTE_NORMAL | win32file.FILE_FLAG_OVERLAPPED, 
                                                None)
            if handle == win32file.INVALID_HANDLE_VALUE:
                return None
            return handle
        except:
            return None

    #perform IOCTL!
    def IoCtl(self, ioctlCode, inData, outLen=0x1100):
        #open driver file link
        driverHandle = self.OpenDriver()
        if driverHandle is None:
            self.ReinstallDriver()
            driverHandle = self.OpenDriver()
            #second try
            if driverHandle is None:
                return None
        #perform IOCTL
        try:
            out_buf = win32file.DeviceIoControl(driverHandle, ioctlCode, inData, outLen, None)
        except:
            out_buf = None
        #close driver file link
        win32file.CloseHandle(driverHandle)
        #return result array
        return out_buf