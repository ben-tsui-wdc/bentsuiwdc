___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import sys
import os
import shutil
import signal

sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries.adblib import ADB
from platform_libraries import common_utils
from junit_xml import TestCase


class fwUpdateUtility(object):

    def __init__(self, adb=None, version=None, env=None, noreset=False, variant=None,
                 local_image=False, keep_fw_img=False, file_server_ip=None):
        self.adb = adb
        self.env = env
        self.noreset = noreset
        self.local_image = local_image
        self.keep_fw_img = keep_fw_img
        self.run_cmd_timeout = 60*50
        self.wait_reboot_time = 60
        self.total_timeout = 60*60
        self.log = common_utils.create_logger(root_log='BAT')
        self.outputpath = '/root/app/output'
        self.ota_folder = '/data/wd/diskVolume0/ota/'
        if local_image:
            self.download_path = 'ftp://ftp:ftppw@{}/firmware'.format(file_server_ip)
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

        self.image = 'install.img'
        if version:
            self.version = version
        else:
            self.version = self.device_init()[0]
        self.model = self.device_init()[1]

        self.start_time = time.time()

    def run(self):
        tries = 10
        for i in range(tries):
            try:
                fw_name = '{0}-{1}-ota-installer-{2}{3}.zip'.format(self.build_name, self.version, self.model, self.tag)
                if self.build_name in os.listdir('.') and self.keep_fw_img and i == 0:
                    # Only keep firmware image at first-time check,
                    # if i > 0 means download image fail need to clean the firmware image before next download started
                    os.chdir(self.build_name)
                    if fw_name in os.listdir('.'):
                        self.log.info('Firmware image "{0}" and folder "{1}" exist, keep it'.format(fw_name, self.build_name))
                        os.chdir('..')
                    else:
                        os.chdir('..')
                        os.remove(self.build_name)
                else:
                    for dir in os.listdir('.'):
                        if dir.startswith(self.build_name) and '.zip' in dir:
                            self.log.info('Remove unnecessary "{}" files'.format(dir))
                            os.remove(dir)
                        elif self.build_name in dir:
                            self.log.info('Remove unnecessary "{}" folder'.format(dir))
                            shutil.rmtree(dir)
                if not self.keep_fw_img or self.build_name not in os.listdir('.'):
                    os.mkdir(self.build_name)
                    if self.local_image:
                        download_url = '{0}/{1}'.format(self.download_path, fw_name)
                    else:
                        download_url = '{0}/{1}/{2}/{3}'.format(self.download_path, self.build_name, self.version, fw_name)
                    self.adb.executeCommand('wget -nv -t 10 {}'.format(download_url), timeout=60*50)
                    shutil.move('./{}'.format(fw_name), './{0}/{1}'.format(self.build_name, fw_name))
                    os.chdir(self.build_name)
                    self.safe_unzip(fw_name)
                else:
                    os.chdir(self.build_name)
                self.log.info(os.listdir('.'))
            except Exception as ex:
                if i < tries - 1:
                    self.log.warning('Exception happened on download firmware part, try again..iter: {0}, Err: {1}'
                                     .format(i+1, ex))
                    continue
                else:
                    testcase = TestCase(name='Firmware Update Utility Test', classname='BAT',
                                        elapsed_sec=time.time()-self.start_time)
                    testcase.add_failure_info('Firmware Update Utility Test FAILED !!. Err: {}'.format(ex))
                    if os.path.exists(self.outputpath):
                        self.log.warning('Download Firmware Failed!!!')
                        with open("DownloadFailed.txt", "w") as f:
                            f.write('Download Firmware Failed\n')
                        shutil.copy('DownloadFailed.txt', '{}/DownloadFailed.txt'.format(self.outputpath))
                    raise Exception('Download fimware failed after retry {0} times. Err: {1}'.format(tries, ex))
            break

        # Fw update check
        cbr = self.adb.executeShellCommand('cat /proc/device-tree/factory/cbr', consoleOutput=False)[0]
        nbr = self.adb.executeShellCommand('cat /proc/device-tree/factory/nbr', consoleOutput=False)[0]
        bna = self.adb.executeShellCommand('cat /proc/device-tree/factory/bna', consoleOutput=False)[0]
        # bootConfig = self.adb.executeShellCommand('cat /mnt/config/bootConfig', consoleOutput=False)[0]
        bootstate = self.adb.executeShellCommand('cat /proc/device-tree/factory/bootstate', consoleOutput=False)[0]
        prop_bootstate = self.adb.executeShellCommand('getprop wd.ota.boot.state', consoleOutput=False)[0]
        self.log.info('cbr = {}'.format(cbr))
        self.log.info('nbr = {}'.format(nbr))
        self.log.info('bna = {}'.format(bna))
        # self.log.info('bootConfig = {}'.format(bootConfig))
        self.log.info('bootstate = {}'.format(bootstate))
        self.log.info('prop_bootstate = {}'.format(prop_bootstate))

        self._reset_start_time()
        self.fw_update_chk()

        try:
            signal.signal(signal.SIGALRM, self.signal_handler)
            signal.alarm(self.run_cmd_timeout)
            # Create ota dir
            self.log.info('Creating OTA dir {}'.format(self.ota_folder))
            self.adb.executeShellCommand(cmd='mkdir -p {}'.format(self.ota_folder))
            # Remove any image files if already existing
            self.log.info('Removing any files if they exist')
            self.adb.executeShellCommand(cmd='rm -rf {}*'.format(self.ota_folder))
            # Push image file
            self.log.info('Pushing img file to device, this may take a while..')
            dl_md5sum = self.adb.executeCommand('cat {}.md5'.format(self.image), consoleOutput=False)[0].split()[0]
            local_md5sum = self.adb.executeCommand('md5sum {}'.format(self.image),
                                                   consoleOutput=False)[0].strip().split()[0]
            self.adb.push(local=self.image, remote=self.ota_folder, timeout=60*45)
            signal.alarm(0)
            push_md5sum = self.adb.executeShellCommand('busybox md5sum {0}/{1}'.format(self.ota_folder, self.image),
                                                       consoleOutput=False)[0].strip().split()[0]
            self.log.info('Compare checksum..')
            self.log.info('dl_md5sum = {0}, local_md5sum = {1}, push_md5sum = {2}'.format(dl_md5sum, local_md5sum, push_md5sum))
            if dl_md5sum == local_md5sum == push_md5sum:
                self.log.info('Executing fw_update binary on device (will timeout and device reboots)')
                self.adb.executeShellCommand(cmd='busybox nohup fw_update {0}{1} -v {2}'
                                             .format(self.ota_folder, self.image, self.version),
                                             timeout=self.run_cmd_timeout-300)
                start = time.time()
                power_off_time = 60*5
                while self.is_device_pingable():
                    self.log.info('Waiting device power off ...')
                    time.sleep(5)
                    if time.time() - start >= power_off_time:
                        raise Exception('Device failed to power off within {} seconds'.format(power_off_time))
                self.adb.disconnect()
                self.wait_device_back()
                time.sleep(5)
            else:
                self.log.error('md5sum is not match, stop update firmware image')
                sys.exit(1)

            # Reset restsdk database
            if not self.noreset:
                self.adb.executeShellCommand('stop restsdk-server')
                self.adb.executeShellCommand('umount /data/wd/diskVolume0/restsdk/userRoots')
                self.adb.executeShellCommand('rm -rf /data/wd/diskVolume0/restsdk')
                self.adb.executeShellCommand('start restsdk-server')

            # Check bootable is 0
            while not self._is_timeout(self.total_timeout):
                try:
                    check_bootable, err_output = self.adb.executeShellCommand('getprop wd.platform.bootable', timeout=10)
                    if '0' in check_bootable:
                        self.log.info('Bootable is 0')
                        break
                    if 'not found' in err_output:
                        raise Exception
                except Exception:
                    self.log.warning('adb broken (may caused by device reboot by itself), wait device back..')
                    self.adb.disconnect()
                    self.wait_device_back()
                time.sleep(5)
            if self._is_timeout(self.total_timeout):
                raise Exception('Check bootable failed after {} secs'.format(self.total_timeout))

        except Exception as ex:
            testcase = TestCase(name='Firmware Update Utility Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            testcase.add_failure_info('Firmware Update Utility Test FAILED !!. Err: {}'.format(ex))
            if os.path.exists(self.outputpath):
                self.log.info('Update Firmware Failed!!!')
                with open("UpdateFailed.txt", "w") as f:
                    f.write('Update Firmware Failed\n')
                shutil.copy('UpdateFailed.txt', '{}/UpdateFailed.txt'.format(self.outputpath))
                self.adb.pull(remote='/cache/ota_install.log', local='{}/ota_install.log'.format(self.outputpath),
                              timeout=100)
                self.adb.pull(remote='/data/wd/diskVolume0/logs/upload/ota_install.log',
                              local='{}/ota_install.log'.format(self.outputpath), timeout=100)
                self.adb.pull(remote='/data/wd/diskVolume0/uploadedLogs',
                              local='{}/uploadedLogs'.format(self.outputpath), timeout=180)
            raise Exception('Test Failed. Err: {}'.format(ex))

        fw_updated_ver = self.device_init()[0]
        if fw_updated_ver == self.version:
            self.log.info('Firmware Update Utility Test PASSED!!')
            testcase = TestCase(name='Firmware Update Utility Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            if os.path.exists(self.outputpath):
                self.log.info('Update Firmware Success!!!')
                with open("UpdateSuccess.txt", "w") as f:
                    f.write('Update Firmware Success\n')
                shutil.copy('UpdateSuccess.txt', '{}/UpdateSuccess.txt'.format(self.outputpath))
        else:
            testcase = TestCase(name='Firmware Update Utility Test', classname='BAT', elapsed_sec=time.time()-self.start_time)
            testcase.add_failure_info('Firmware Update Utility Test FAILED!! Firmware version did not match')
            if os.path.exists(self.outputpath):
                self.log.info('Update Firmware Failed!!!')
                with open("UpdateFailed.txt", "w") as f:
                    f.write('Update Firmware Failed\n')
                shutil.copy('UpdateFailed.txt', '{}/UpdateFailed.txt'.format(self.outputpath))
        self.cleanup()
        return testcase

    def device_init(self):
        try:
            self.adb.connect()
            time.sleep(2)
            version = self.adb.getFirmwareVersion()
            platform = self.adb.getModel()
            self.log.info('Firmware is :{}'.format(version.split()[0]))
            self.log.info('Platform is :{}'.format(platform.split()[0]))
            time.sleep(1)
            return version.split()[0], platform.split()[0]
        except Exception as ex:
            raise Exception('Failed to connect to device and execute adb command! Err: {}'.format(ex))

    def is_device_pingable(self):
        command = 'nc -zv -w 1 {0} 5555 > /dev/null 2>&1'.format(self.adb.uut_ip)
        response = os.system(command)
        if response == 0:
            return True
        else:
            return False

    def fw_update_chk(self):
        while not self._is_timeout(150):
            try:
                fw_chk = self.adb.executeShellCommand('busybox nohup "fw_update -c; echo $?"', consoleOutput=False)[0]
                if '0' in fw_chk:
                    self.log.info('Device is ready to ota.')
                    break
                elif '2' in fw_chk:
                    self.log.error('Firmware update config error, stop firmware update script!')
                    if os.path.exists(self.outputpath):
                        with open("FWconfigFailed.txt", "w") as f:
                            f.write('Firmware Update Config Failed\n')
                        shutil.copy('FWconfigFailed.txt', '{}/DownloadFailed.txt'.format(self.outputpath))
                    sys.exit(1)
                else:
                    self.log.info('Wait for device reboot (Reboot by fw_update -c)...')
                    self.adb.disconnect()
                    self.wait_device_back()
            except:
                self.log.info('Try to get fw_update return code..')
        time.sleep(3)

    def wait_device_back(self):
        start = time.time()
        wait_bootup_time = 60*2
        while not self.is_device_pingable():
            self.log.info('Waiting device boot up ...')
            time.sleep(5)
            if time.time() - start > wait_bootup_time:
                raise Exception('Timed out waiting to boot within {} seconds'.format(wait_bootup_time))
        # Wait adb launch
        time.sleep(10)
        for j in range(0, 10):
            self.log.info('Attempt to connect {0}'.format(j))
            try:
                self.adb.connect()
            except Exception:
                self.log.info('adb not connecting')
                self.adb.disconnect()
                time.sleep(5)
            if self.adb.connected:
                time.sleep(3)
                try:
                    boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed')[0]
                except Exception as ex:
                    self.log.info(ex)
                    self.log.info('Try again...')
                    time.sleep(3)
                    boot_completed = self.adb.executeShellCommand('getprop sys.boot_completed')[0]
                if '1' in boot_completed:
                    self.log.info('Boot completed')
                    break
                else:
                    time.sleep(3)
            if j > 9:
                self.log.warning('device not responding')
                raise Exception('Device not ready after try {} times to reconnect'.format(j))

    def cleanup(self):
        os.chdir('..')
        if not self.keep_fw_img:
            for item in os.listdir('.'):
                if self.build_name in item:
                    shutil.rmtree(item)
        time.sleep(5)

    def _reset_start_time(self):
        self.start_time = time.time()

    def _is_timeout(self, timeout):
        return (time.time() - self.start_time) >= timeout

    def safe_unzip(self, zip_file, extractpath='.'):
        import zipfile
        self.log.info('Start unzip file')
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
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)', default='5555')
    parser.add_argument('-fw', help='Update firmware version, ex. 4.0.0-100')
    parser.add_argument('-env', help='Target environment, ex. dev1 (default)', default='dev1')
    parser.add_argument('-variant', help='Build variant, ex. debug')
    parser.add_argument('--noreset', help='Not to clear restsdk db', action='store_true', default=False)
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')
    parser.add_argument('--keep_fw_img', action='store_true', default=False, help='Keep downloaded firmware')
    parser.add_argument('--file_server', help='File server IP address', default='fileserver.hgst.com')
    args = parser.parse_args()

    uut_ip = args.uut_ip
    version = args.fw
    port = args.port
    noreset = args.noreset
    env = args.env
    variant = args.variant
    local_image = args.local_image
    keep_fw_img = args.keep_fw_img
    file_server_ip = args.file_server

    adb = ADB(uut_ip=uut_ip, port=port)
    testrun = fwUpdateUtility(adb=adb, version=version, env=env,
                              variant=variant, noreset=noreset, local_image=local_image,
                              keep_fw_img=keep_fw_img, file_server_ip=file_server_ip)
    testrun.run()
