___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os
import shutil
import signal

from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class fwUpdateUbootUtility(object):

    def __init__(self, adb=None, version=None, uboot=None, env=None, local_image=False, variant=None):
        self.adb = adb
        self.env = env
        self.adb.connect()
        self.local_image = local_image
        self.run_cmd_timeout = 60*30
        self.wait_reboot_time = 60
        self.total_timeout = 60*50
        self.log = common_utils.create_logger(root_log='BAT')
        self.outputpath = '/root/app/output'
        self.ota_folder = '/data/wd/diskVolume0/ota/'
        if local_image:
            self.download_path = 'ftp://ftp:ftppw@fileserver.hgst.com/firmware'
        else:
            self.download_path = 'http://repo.wdc.com/content/repositories/projects/MyCloudOS'
        if self.env == 'qa1':
            self.build_name = 'MCAndroid-QA'
        elif self.env == 'prod':
            self.build_name = 'MCAndroid-prod'
        elif self.env == 'dev1':
            self.build_name = 'MCAndroid'
        elif self.env =='integration':
            self.build_name = 'MCAndroid-integration'

        if variant == 'engr':
            self.tag = '-engr'
        elif variant == 'user':
            self.tag = '-user'
        else:
            self.tag = ''
        self.model = self.device_init()[1]
        if uboot:
            print 'Start to update uboot version :{}'.format(uboot)
            self.origin_uboot_version = uboot
        else:
            self.origin_uboot_version = self.get_uboot_version()
        self.image = 'wd_{0}_uboot.tar'.format(self.model)
        if version:
            self.version = version
        else:
            self.version = self.device_init()[0]

        self.start_time = time.time()

    def run(self):
        try:
            fw_name = '{0}-{1}-ota-installer-{2}{3}.zip'.format(self.build_name, self.version, self.model, self.tag)
            for dir in os.listdir('.'):
                if dir.startswith(self.build_name) and dir.endswith('.zip'):
                    os.remove(dir)
                elif self.build_name in dir:
                    shutil.rmtree(dir)
            os.mkdir(self.build_name)
            if self.local_image:
                download_url = '{0}/{1}'.format(self.download_path, fw_name)
            else:
                download_url = '{0}/{1}/{2}/{3}'.format(self.download_path, self.build_name, self.version, fw_name)
            self.adb.executeCommand('wget -nv -t 10 {}'.format(download_url), timeout=60*50)
            shutil.move('./{}'.format(fw_name), './{0}/{1}'.format(self.build_name, fw_name))
            os.chdir(self.build_name)
            self.safe_unzip(fw_name)
            self.log.info(os.listdir('.'))
        except Exception as ex:
            testcase = TestCase(name='Firmware Update Uboot Utility Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            testcase.add_failure_info('Firmware Update Uboot Utility Test FAILED !!. Err: {}'.format(ex))
            if os.path.exists(self.outputpath):
                print 'Download Firmware Uboot Failed!!!'
                with open("DownloadFailed.txt", "w") as f:
                    f.write('Download Firmware Uboot Failed\n')
                shutil.copy('DownloadFailed.txt', '{}/DownloadFailed.txt'.format(self.outputpath))
            raise Exception('Test Failed. Err: {}'.format(ex))

        time.sleep(3)
        signal.signal(signal.SIGALRM, self.signal_handler)
        signal.alarm(self.run_cmd_timeout)
        try:
            # Create ota dir
            print 'Creating OTA dir {}'.format(self.ota_folder)
            self.adb.executeShellCommand(cmd='mkdir -p {}'.format(self.ota_folder))
            # Remove any image files if already existing
            print 'Removing any files if they exist'
            self.adb.executeShellCommand(cmd='rm -rf {}*'.format(self.ota_folder))
            # Push image file
            print 'Pushing img file to device, this may take a while..'
            self.adb.push(local=self.image, remote=self.ota_folder, timeout=self.run_cmd_timeout-200)
            if self.model == 'monarch':
                cmd = 'factory.spi flash {0}{1}'.format(self.ota_folder, self.image)
            else:
                cmd = 'factory flash {0}{1}'.format(self.ota_folder, self.image)
            print 'Executing factory binary on device (will timeout and device reboots)'
            self.adb.executeShellCommand(cmd=cmd,
                                         timeout=self.run_cmd_timeout-300)
            time.sleep(3)
            self.adb.executeShellCommand('busybox nohup reboot')
            time.sleep(3)
            self.adb.disconnect()
            self.wait_device_back()
        except Exception as ex:
            testcase = TestCase(name='Firmware Update Uboot Utility Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            testcase.add_failure_info('Firmware Update Uboot Utility Test FAILED !!. Err: {}'.format(ex))
            if os.path.exists(self.outputpath):
                print 'Update Firmware Uboot Failed!!!'
                with open("UpdateFailed.txt", "w") as f:
                    f.write('Update Firmware Uboot Failed\n')
                shutil.copy('UpdateFailed.txt', '{}/UpdateFailed.txt'.format(self.outputpath))
            raise Exception('Test Failed. Err: {}'.format(ex))

        new_uboot_version = self.get_uboot_version()
        if new_uboot_version == self.origin_uboot_version:
            print 'Firmware Update Uboot Utility Test PASSED!!'
            testcase = TestCase(name='Firmware Update Uboot Utility Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            if os.path.exists(self.outputpath):
                print 'Update Firmware Uboot Success!!!'
                with open("UpdateSuccess.txt", "w") as f:
                    f.write('Update Firmware Uboot Success\n')
                shutil.copy('UpdateSuccess.txt', '{}/UpdateSuccess.txt'.format(self.outputpath))
        else:
            print 'Firmware Update Uboot Utility Test FAILED!!'
            print 'Current Uboot version is:{0}, Update Uboot version is:{1}, Version not match!!'.format(new_uboot_version, self.origin_uboot_version)
            testcase = TestCase(name='Firmware Update Uboot Utility Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            testcase.add_failure_info('Firmware Update Uboot Utility Test FAILED!! Firmware version did not match')
            if os.path.exists(self.outputpath):
                print 'Update Firmware Uboot Failed!!!'
                with open("UpdateFailed.txt", "w") as f:
                    f.write('Update Firmware Uboot Failed\n')
                shutil.copy('UpdateFailed.txt', '{}/UpdateFailed.txt'.format(self.outputpath))
        self.cleanup()
        return testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.getFirmwareVersion()
            platform = self.adb.getModel()
            print 'Firmware is :{}'.format(version.split()[0])
            print 'Platform is :{}'.format(platform.split()[0])
            time.sleep(1)
            return version.split()[0], platform.split()[0]
        except Exception as ex:
            raise Exception('Failed to connect to device and execute adb command! Err: {}'.format(ex))

    def wait_device_back(self):
        time.sleep(self.wait_reboot_time)
        for j in range(0, 20):
            print 'Attempt to connect {0}'.format(j)
            try:
                self.adb.connect(timeout=10)
            except Exception:
                print 'adb not connecting'
                time.sleep(5)
            if self.adb.connected:
                time.sleep(7)
                boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed')[0]
                if '1' in boot_completed:
                    print 'Boot completed'
                    break
                else:
                    time.sleep(3)
            if j > 8:
                print 'device not responding'
                raise Exception('Device not ready after try {} times to reconnect'.format(j))

    def get_uboot_version(self):
        self.adb.remount()
        self.adb.executeShellCommand('factory.spi load')
        uboot = self.adb.executeShellCommand('fw_printenv ver')[0]
        print 'Uboot version is :{0}'.format(uboot.split()[0].strip('ver='))
        return uboot.split()[0].strip('ver=')

    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout

    def cleanup(self):
        os.chdir('..')
        for item in os.listdir('.'):
            if self.build_name in item:
                shutil.rmtree(item)
        time.sleep(5)

    @staticmethod
    def safe_unzip(zip_file, extractpath='.'):
        import zipfile
        with zipfile.ZipFile(zip_file, 'r') as zf:
            for member in zf.infolist():
                abspath = os.path.abspath(os.path.join(extractpath, member.filename))
                if abspath.startswith(os.path.abspath(extractpath)):
                    zf.extract(member, extractpath)

    @staticmethod
    def signal_handler(signum, frame):
        raise Exception('Timeout on running command locally')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-fw', help='Update firmware version, ex. 4.0.0-100')
    parser.add_argument('-env', help='Target environment, ex. dev1 (default)')
    parser.add_argument('-uboot', help='Update uboot version, ex. 4.0.1')
    parser.add_argument('--variant', help='Build variant, ex. debug', default='debug')
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    version = args.fw
    variant = args.variant
    local_image = args.local_image
    uboot = args.uboot
    env = args.env
    if args.port:
        port = args.port
    else:
        port = '5555'
    adb = ADB(uut_ip=uut_ip, port=port)

    testrun = fwUpdateUbootUtility(adb=adb, version=version, uboot=uboot,
                                   env=env, variant=variant, local_image=local_image)
    testrun.run()
