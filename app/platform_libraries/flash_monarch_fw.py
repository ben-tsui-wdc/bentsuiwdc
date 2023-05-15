import shlex
import subprocess32
import argparse
import os.path
import time
from subprocess32 import Popen, PIPE

# script to flash a monarch device given the IP address and imagefile

# ADB class to connect to device with ADB over TCP and execute commands
class ADB(object):

    def __init__(self, adbServer=None, adbServerPort=None, uut_ip=None, port='5555'):
        if adbServer and adbServerPort:
            self.adbServer = adbServer
            self.adbServerPort = adbServerPort
            self.remoteServer = True
        else:
            self.remoteServer = False
        self.port = port
        self.uut_ip = uut_ip
        self.connected = False


    def connect(self, timeout=60):
        """Attempt to connect to device over TCP"""
        if self.remoteServer:
            cmd = 'adb -H {0} -P {1} connect {2}:{3}'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port)
        else:
            cmd = 'adb connect ' + self.uut_ip + ':' + self.port
        stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout)
        if stdout and 'unable' in stdout:
            raise Exception('Unable to connect to ' + self.uut_ip)
        else:
            self.connected = True
            return stdout, stderr

    def disconnect(self, timeout=60):
        """Disconnect from device"""
        if self.connected:
            if self.remoteServer:
                cmd = 'adb -H {0} -P {1} disconnect {2}:{3}'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port)
            else:
                cmd = 'adb disconnect ' + self.uut_ip + ':' + self.port
            stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout)
            self.connected = False
            print 'Device disconnected'
        else:
            print 'No device connected'

    def startServer(self):
        cmd = 'adb start-server'
        stdout, stderr = self.executeCommand(cmd)
        if stdout:
            print stdout
        return stdout, stderr

    def killServer(self):
        cmd = 'adb kill-server'
        stdout, stderr = self.executeCommand(cmd)
        return stdout, stderr
    def push(self, local=None, remote=None, timeout=60):
        """ adb push command to copy file from local host to remote connected device """
        if self.remoteServer:
            cmd = 'adb -H {0} -P {1} -s {2}:{3} push {4} {5}'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port, local, remote)
        else:
            cmd = 'adb -s %s:%s push %s %s' %(self.uut_ip, self.port, local, remote)
        stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout)
        return stdout, stderr

    def pull(self, remote=None, local=None, timeout=60):
        """ adb pull command to copy file from remote connected device to local machine """
        if self.remoteServer:
            cmd = 'adb -H {0} -P {1} -s {2}:{3} push {4} {5}'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port, remote, local)
        else:
            cmd = 'adb -s %s:%s pull %s %s' %(self.uut_ip, self.port, remote, local)
        stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout)
        return stdout, stderr

    def executeShellCommand(self, cmd=None, timeout=60, consoleOutput=True):
        """ Execute shell command on adb connected device """
        if self.remoteServer:
            cmd = 'adb -H {0} -P {1} -s {2}:{3} shell "{4}"'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port, cmd)
        else:
            cmd = 'adb -s %s:%s shell "%s"' %(self.uut_ip, self.port, cmd)
        stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout, consoleOutput=consoleOutput)
        return stdout, stderr
        
    def executeCommand(self, cmd=None, consoleOutput=True, timeout=60):
        """
        Execute command and return stdout, stderr
        Handle timeout exception if limit exceeded and return None
        """
        if consoleOutput:
            print 'Executing commmand: %s' %(cmd)
        cmd = shlex.split(cmd)
        output = subprocess32.Popen(cmd, stdout=PIPE, stderr=PIPE)
        try:
            stdout, stderr = output.communicate(timeout=timeout)
            if 'device offline' in stderr:
                raise Exception('Device offline!')
        except subprocess32.TimeoutExpired as e:
            print 'Timeout Exceeded: %i seconds' %(timeout) 
            print 'Killing command %s' %(cmd)
            output.kill()
            stdout = None
            stderr = None
            raise e
        else:
            if consoleOutput:
                print 'stdout: ' + stdout
            if stderr:
                print 'stderr: ' + stderr
            return stdout, stderr
    def getModel(self):
        stdout, stderr = self.executeShellCommand(cmd='getprop ro.hardware', consoleOutput=False)
        return stdout
    def getFirmware(self):
        stdout, stderr = self.executeShellCommand(cmd='getprop ro.build.version.incremental', consoleOutput=False)
        return str(stdout).strip()
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Script to flash fw on monarch device Requirements: adb in path, python, module subprocess32 installed via pip')
    parser.add_argument('uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('img', help='Filepath to image to push to device and flash, ex. /imgs/install.img')
    parser.add_argument('-port', help='Device adb port number, ex. 5555 (default)', default='5555')
    parser.add_argument('-server_ip', help='adb server IP address, ex. 10.104.130.130', default=None)
    parser.add_argument('-server_port', help='adb server port number, ex. 5037', default=None)

    args = parser.parse_args()

    uut_ip = args.uut_ip
    img_path = args.img
    devicePort = args.port
    adbServerPort = args.server_port
    adbServer = args.server_ip
    adbServer = args.server_port

    if not os.path.isfile(img_path):
        raise Exception('No file found at "{}"'.format(img_path))
    head, tail = os.path.split(img_path)
    img_name = tail
    adb = ADB(uut_ip=uut_ip, port=devicePort)
    adb.connect()
    time.sleep(1)
    fw_version = adb.getFirmware()
    print 'Current fw version: {}'.format(fw_version)
    ota_folder = '/data/wd/diskVolume0/ota/'
    # Create ota dir
    print 'Creating OTA dir {}'.format(ota_folder)
    adb.executeShellCommand(cmd='mkdir -p {}'.format(ota_folder))
    # Remove any image files if already existing
    print 'Removing any files if they exist'
    adb.executeShellCommand(cmd='rm -rf {}*'.format(ota_folder))
    # Push image file
    print 'Pushing img file to device, this may take a while..'
    adb.push(local=img_path, remote=ota_folder, timeout=900)

    print 'Executing fw_update binary on device (will timeout and device reboots)'
    try:
        adb.executeShellCommand(cmd='fw_update {0}{1}'.format(ota_folder,img_name), timeout=240)
    except subprocess32.TimeoutExpired:
        print 'Sleep ..'
    time.sleep(15)

    print 'Disconnecting and attempting to reconnect'
    adb.disconnect()
    adb.connect()
    time.sleep(1)
    fw_version = adb.getFirmware()
    print 'New fw version: {}'.format(fw_version)
    adb.disconnect()



