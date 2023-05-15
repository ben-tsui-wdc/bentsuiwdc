__author__ = 'Kurt Jensen <kurt.jensen@wdc.com>'

import shlex # to split shell commands
import subprocess32 as subprocess # subprocess module ported from python 3.2 with support for timeout exceptions
from subprocess32 import Popen, PIPE
import os
import errno
import time
import traceback
import logging
import common_utils
import re
import constants
from shell_cmds import ShellCommands
from pyutils import NotSet


def count_nested_calls():
    """ Count total number of resend_on_failure_wrapper() called. """
    nested_calls = 0
    for py, line, f, call in traceback.extract_stack():
        if f == 'resend_on_failure_wrapper':
            nested_calls += 1
    return nested_calls

def resend_on_failure(executeCommand):
    """ Hot fix for ADB failed by unknown issue. """

    def resend_on_failure_wrapper(self, *args, **kwargs):
        resend_max_times = 4 if self.retry_with_reboot_device else 3
        resend_count = 1

        if '_no_resend' in kwargs: # Private argument for disable resending.
            if kwargs.pop('_no_resend'):
                resend_max_times = 0
        timeout_exception = subprocess.TimeoutExpired
        if '_resend_when_timeout' in kwargs: # Private argument for do resend when timeout.
            if kwargs.pop('_resend_when_timeout'):
                timeout_exception = NotSet

        while True:
            try:
                stdout, stderr = executeCommand(self, *args, **kwargs)
                if stderr.startswith('error') or stderr.startswith('protocol failure'): 
                    if kwargs and "disconnect" in kwargs.get('cmd', ''):
                        return stdout, stderr
                    else:
                        raise RuntimeError('ADB command error.') 
                else:
                    return stdout, stderr
            #except timeout_exception: # Ignore TimeoutExpired.
            #    raise
            except:
                if count_nested_calls() > 1: # Only outer function do re-send.
                    raise
                if resend_count > resend_max_times: # Stop re-send.
                    raise
                self.log.exception('[resend_on_failure] Catch An Exception During ADB Command.')
                time.sleep(5)
                if 'cmd' in kwargs:
                    self.log.info('Resend ADB command ({0}) #{1}...'.format(kwargs['cmd'], resend_count))
                else:
                    self.log.info('Resend ADB command #{}...'.format(resend_count))
                resend_count += 1

                try:
                    self.disconnect(timeout=5)
                    self.log.debug('*** has_serial_client:{} resend_count:{} resend_max_times:{}'.format(self.has_serial_client(), resend_count, resend_max_times))
                    if self.has_serial_client():
                        if resend_count == 4: # Restart ADB daemon at 3rd retries.
                            self.restart_adbd_by_serial()
                        elif resend_count > resend_max_times: # Restart device at final retry.
                            self.reboot_device_by_serial()
                    self.connect()
                except Exception, e:
                    self.log.exception('[Re-Connect Error In Retries] {}'.format(e))
    return resend_on_failure_wrapper


# ADB class to connect to device with ADB over TCP and execute commands
class ADB(ShellCommands):

    def __init__(self, adbServer=None, adbServerPort=None, uut_ip=None, port='5555', log_name=None, stream_log_level=None, retry_with_reboot_device=False):
        if adbServer and adbServerPort:
            self.adbServer = adbServer
            self.adbServerPort = str(adbServerPort)
            self.remoteServer = True
        else:
            self.remoteServer = False
        self.port = str(port)
        self.uut_ip = uut_ip
        self.connected = False
        self.log = common_utils.create_logger(overwrite=False, log_name=log_name, stream_log_level=stream_log_level)
        self.prefix_command = self.gen_prefix_command()
        self.retry_with_reboot_device = retry_with_reboot_device

    def set_serial_client(self, serial_client):
        self.log.debug('Set serial_client: {}'.format(serial_client))
        self._serial_client = serial_client

    def has_serial_client(self):
        return hasattr(self, '_serial_client')

    def restart_adbd_by_serial(self):
        self._serial_client.restart_adbd()
        time.sleep(5) # Wait a while for ADB daemon start up.

    def reboot_device_by_serial(self):
        self.log.info('Reboot device by serial...')
        self._serial_client.reboot_device()
        self._serial_client.wait_for_boot_complete()

    def gen_prefix_command(self):
        if self.remoteServer:
            cmd = 'adb -H %s -P %s {} -s %s:%s' % (self.adbServer, self.adbServerPort, self.uut_ip, self.port)
        else:
            cmd = 'adb -s %s:%s {}' % (self.uut_ip, self.port)
        return cmd

    def update_device_ip(self, ip):
        self.log.info('Current IP: {} now change to IP: {}...'.format(self.uut_ip, ip))
        need_to_recovery_connection = False
        # Disconnect current connection.
        if self.connected:
            self.disconnect()
            need_to_recovery_connection =True
        # Change IP
        self.uut_ip = ip
        self.prefix_command = self.gen_prefix_command()
        # Recovery connection
        if need_to_recovery_connection:
            self.connect()

    def test_connection(self):
        self.log.info('Test ADB connect with whoami...')
        stdout, stderr = self.executeShellCommand(cmd='whoami', consoleOutput=False, timeout=5)
        if stderr.startswith('error'): raise RuntimeError('ADB connect error.')
        self.log.info('ADB Connect works.')

    def connect(self, timeout=60):
        """ Attempt to connect to device with root user. """
        # TODO: Think about the correctness of timeout value to these steps.
        stdout, stderr = self.retry_connect(timeout)
        try:
            # Am I root user?
            if 'root' in self.whoami():
                self.log.info('Connect as root user.')
                return stdout, stderr
            # Switch root and reconnect.
            self.log.info('Switch to root user.')
            self.switch_root(timeout=5)
            self.disconnect(timeout=5)
        except Exception, e:
            # TODO: Workaround for switch_root timeout, we need to make sure what behaviors are right.
            self.log.warning('[connect] Catch Exception during switch to root user: {}'.format(e))
            if getattr(self, '_retry', False):
                del self._retry
                raise
            self._retry = True
            self.log.warning('Retry one more time...')
            time.sleep(3)
            self.disconnect(timeout=5)
            return self.connect(timeout)
        return self.retry_connect(timeout)

    def retry_connect(self, timeout=60, retry_timeout=70):
        start_time = time.time()
        while timeout > (time.time()-start_time):
            try:
                stdout, stderr = self._connect(retry_timeout)
                time.sleep(0.5) # Wait 0.5 sec and then execute test_connect(), for bad network environment
                self.test_connection()
                return stdout, stderr
            except Exception, e:
                self.log.warning('[retry_connect] Catch Exception: {}'.format(e))
                self.log.info('Retry ADB connect...')
                self.disconnect()
                time.sleep(1)

        raise RuntimeError('Retry timeout for {} secs.'.format(timeout))
        
    def _connect(self, timeout=60):
        """Attempt to connect to device over TCP"""
        if self.remoteServer:
            cmd = 'adb -H {0} -P {1} connect {2}:{3}'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port)
        else:
            cmd = 'adb connect ' + self.uut_ip + ':' + self.port
        stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout)
        if stdout and 'unable' in stdout:
            raise Exception('Unable to connect to ' + self.uut_ip)
        else:
            self.log.debug(stdout.strip())
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
            self.log.debug(stdout)
            self.log.info('Device disconnected')
        else:
            self.log.info('No device connected')

    def disconnect_all(self, timeout=60):
        stdout, stderr = self.executeCommand(cmd='adb disconnect', timeout=timeout)
        self.connected = False
        self.log.debug(stdout)
        self.log.info('Device disconnected')

    def startServer(self):
        cmd = 'adb start-server'
        stdout, stderr = self.executeCommand(cmd)
        if stdout:
            self.log.debug(stdout)
        else:
            self.log.debug('ADB server already started')
        return stdout, stderr

    def killServer(self):
        cmd = 'adb kill-server'
        stdout, stderr = self.executeCommand(cmd)
        self.log.debug('ADB server killed')
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

    def remount(self, timeout=60):
        """ adb remount command to remount adb connected device """
        if self.remoteServer:
            cmd = 'adb -H {0} -P {1} -s {2}:{3} remount'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port)
        else:
            cmd = 'adb -s %s:%s remount' %(self.uut_ip, self.port)
        stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout)
        return stdout, stderr

    def switch_root(self, timeout=60):
        """ adb shell root """
        cmd = self.prefix_command.format('root')
        stdout, stderr = self.executeCommand(cmd=cmd, timeout=timeout)
        return stdout, stderr

    def logcat_to_file(self, file_name, buffer_name=None, timeout=60*8):
        """ Save logcat information to file. """
        self.log.info('Save logcat information to %s' % file_name)
        buffer_str = ''
        if buffer_name:
            buffer_str = ' -b ' + buffer_name
        cmd = self.prefix_command.format('logcat -d{}'.format(buffer_str))
        with open(file_name, 'w') as out:
            self.executeCommand(cmd=cmd, consoleOutput=False, stdout=out, timeout=timeout)

    def clean_logcat(self, buffer_name=None, timeout=60):
        """ Clean logcat logs."""
        self.log.info('Clean logcat logs.')
        buffer_str = ''
        if buffer_name:
            buffer_str = ' -b ' + buffer_name
        cmd = self.prefix_command.format('logcat -c{}'.format(buffer_str))
        self.executeCommand(cmd=cmd, timeout=timeout)

    def executeShellCommand(self, cmd=None, timeout=60, consoleOutput=True, _no_resend=False, _resend_when_timeout=False):
        """ Execute shell command on adb connected device """
        if self.remoteServer:
            cmd = 'adb -H {0} -P {1} -s {2}:{3} shell "{4}"'.format(self.adbServer, self.adbServerPort, self.uut_ip, self.port, cmd)
        else:
            cmd = 'adb -s %s:%s shell "%s"' %(self.uut_ip, self.port, cmd)
        stdout, stderr = self.retry_execute(cmd=cmd, timeout=timeout, consoleOutput=consoleOutput,
            _no_resend=_no_resend, _resend_when_timeout=_resend_when_timeout # privare args.
        )
        return stdout, stderr
        
    @resend_on_failure
    def retry_execute(self, cmd=None, consoleOutput=True, stdout=PIPE, stderr=PIPE, timeout=60):
        return self.executeCommand(cmd, consoleOutput, stdout, stderr, timeout)

    def load_factory_env(self):
        """ Load factory env.txt before use fw_printenv command. """
        stdout, stderr = self.executeShellCommand(cmd='fw_printenv > /dev/null 2>&1; echo $?', consoleOutput=False)
        if '0' in stdout: # Already loaded.
            return
        model = self.getModel()
        if model == 'pelican':
            self.executeShellCommand('factory load')
        else:
            self.executeShellCommand('factory.spi load')

    def getSerialNumber(self, old_style=False):
        """
        Get serial number from monarch or pelican device, if it doesn't exist, load it into the temp textfile and grep
        """
        if old_style:
            self.load_factory_env()
            stdout, stderr = self.executeShellCommand(cmd='fw_printenv serial', consoleOutput=False)
            if 'serial=' in stdout:
                return stdout.strip()[7:]
            return stdout
        else:
            stdout, stderr = self.executeShellCommand(cmd='busybox cat /proc/device-tree/factory/serial', consoleOutput=False)
            return stdout.strip()
        
    def getModel(self):
        # Get model, 'monarch' or 'pelican'
        stdout, stderr = self.executeShellCommand(cmd='getprop ro.hardware', consoleOutput=False)
        return stdout.strip()

    def getFirmwareVersion(self):
        # Get FW version, 4.0.0.X
        stdout, stderr = self.executeShellCommand(cmd='getprop ro.build.version.incremental', consoleOutput=False)
        return str(stdout).strip()

    def get_variant(self):
        # Get variant type: user, userdebug or prod
        stdout, stderr = self.executeShellCommand(cmd='getprop ro.build.type', consoleOutput=False)
        return stdout.strip()

    def get_uboot(self):
        # Get uboot version. Ex: 4.1.4
        self.load_factory_env()
        stdout, stderr = self.executeShellCommand(cmd='fw_printenv ver', consoleOutput=False)
        if 'ver=' in stdout:
            return stdout.strip()[4:]
        return stdout

    def get_config_url(self):
        stdout, stderr = self.executeShellCommand(cmd='cat /etc/restsdk-server.toml | grep configURL', consoleOutput=False)
        return stdout.replace('configURL = ', '').replace('"','').strip()

    def get_environment(self):
        # Get cloud environment type: qa1, dev1, prod
        config_url = self.get_config_url()
        if 'dev1' in config_url:
            return 'dev1'
        elif 'qa1' in config_url:
            return 'qa1'
        return 'prod'

    def get_mac_address(self, interface='eth0'):
        stdout, stderr = self.executeShellCommand(cmd='cat /sys/class/net/{}/address'.format(interface), consoleOutput=False)
        mac_address = stdout.strip()
        if len(mac_address) != 17:
            return None
        return mac_address

    def whoami(self):
        """ adb shell whoami """
        stdout, stderr = self.executeShellCommand(cmd='whoami', consoleOutput=False)
        return stdout

    def check_otaclient(self):
        stdout, stderr = self.executeShellCommand(cmd='ps | grep otaclient')
        if stdout:
            return True
        return False

    def start_otaclient(self):
        self.executeShellCommand(cmd='setprop persist.wd.ota.lock 0')
        return self.check_otaclient()

    def stop_otaclient(self):
        self.executeShellCommand(cmd='setprop persist.wd.ota.lock 1')
        return not self.check_otaclient()

    def is_device_pingable(self):
        command = 'nc -zvn -w 1 {0} {1} > /dev/null 2>&1'.format(self.uut_ip, self.port)
        response = os.system(command)
        if response == 0:
            return True
        self.disconnect()
        return False

    def wait_for_device_to_shutdown(self, timeout=60*30, pingable_count=2):
        # Extend the timeout from 5 minutes to 30 minutes since Yodaplus will take much time to upload log while factory_reset.
        start_time = time.time()
        current_count = 0
        while (timeout > time.time() - start_time):
            if not self.is_device_pingable():
                current_count += 1
                self.log.info('Device is not pingable {} time...'.format(current_count))
                if current_count >= pingable_count:
                    self.log.info('Device is shutdown')
                    return True

            self.log.info('Waiting for device to shutdown...')
            time.sleep(5)
        self.log.info('Device still works')
        return False

    def check_adb_connectable(self):
        if self.connected:
            self.disconnect()
        self.log.info('Attempt to connect...')
        try:
            self.connect(timeout=10)
            return True
        except:
            self.log.info('Can not connect to adbd')
        return False

    def check_platform_bootable(self):
        # Changed check flag due to IBIX-4715
        '''
        platform_bootable, _ = self.executeShellCommand('getprop persist.wd.platform.bootable', timeout=10)
        if '0' in platform_bootable:
            return True
        return False
        '''
        boot_completed, _ = self.executeShellCommand('cat /proc/boot_completed', timeout=10)
        disk_mounted, _ = self.executeShellCommand('getprop sys.wd.disk.mounted', timeout=10)
        otaclient, _ = self.executeShellCommand('getprop init.svc.otaclient', timeout=10)
        if '1' in boot_completed and '1' in disk_mounted and 'running' in otaclient:
            return True
        return False

    def wait_for_device_boot_completed(self, timeout=60*5, time_calibration_retry=True, max_retries=10, retry_delay=30, disable_ota=False):
        start_time = time.time()
        while (timeout > time.time() - start_time):
            if self.check_adb_connectable():
                break
            time.sleep(5)

        if disable_ota:
            self.log.info('Stop otaclient...')
            self.stop_otaclient()

        while (timeout > time.time() - start_time):
            if self.check_platform_bootable():
                break
            time.sleep(5)

        if not (timeout > time.time() - start_time):
            self.log.info('Wait timeout: {}s'.format(timeout))
            return False
        for retries in range(1, max_retries+1):
            result = self.is_machine_time_correct(tolerance_sec=60)
            if result:
                self.log.info('Device boot completed')
                return True
            else:
                if time_calibration_retry:
                    self.log.info('Machine time is not correct, retry {} times after {} secs...'.format(retries, retry_delay))
                    self.executeShellCommand('logcat -d | grep NetworkTimeUpdateService')
                    time.sleep(retry_delay)
                    if retries == max_retries:
                        return False
                else:
                    self.log.warning('No time calibration retry and Machine time is not correct !!!')
                    return True  # Return True even if machine time is not correct


    def MD5_checksum(self, user_id, folder_path, consoleOutput=True, timeout=120):
        user_id = user_id.replace('auth0|', 'auth0\|')
        command = "busybox md5sum /data/wd/diskVolume0/restsdk/userRoots/{0}/{1}/*".format(user_id, folder_path)
        result = self.executeShellCommand(command, timeout=timeout, consoleOutput=consoleOutput)[0]
        MD5_nas_dict = {}
        for element in result.split('\r\n'):
            if element:
                MD5_nas_dict.update({element.split('/')[-1]:element.split(' ')[0]})
        return MD5_nas_dict

    def download_file_from_server(self, file_server_ip, file_path, user_id, download_folder):
        file_server_url = 'ftp://ftp:ftppw@{}{}'.format(file_server_ip, file_path)
        abs_file_path = "/data/wd/diskVolume0/restsdk/userRoots/{0}/{1}".format(user_id, download_folder)
        self.executeShellCommand("busybox wget -q {} -P {}".format(file_server_url, abs_file_path))[0]

    def download_file_to_local_host(self, download_url, local_path="", retries=20, timeout=120 * 60, is_folder=False):
        self.log.info("Download URL: {}".format(download_url))
        wget_cmd = 'wget -nv -N -t {0} -T {1} {2} -P {3} --no-check-certificate'. \
        format(retries, timeout, download_url, local_path)
        if is_folder:
            wget_cmd += ' -r -np -nd -R "index.html*"'
        self.executeCommand(cmd=wget_cmd, timeout=timeout)

    def download_files_and_upload_to_test_device(self,
            download_url=constants.FILESERVER_TW_MVWARRIOR, 
            local_path="", test_device_path="", is_folder=False):
        self.log.info('Start to download files(from {0}) and upload to test device...'
            .format(download_url))
        self.download_file_to_local_host(download_url=download_url, local_path=local_path, is_folder=is_folder)
        self.push(local=local_path, remote=test_device_path, timeout=300)

    def check_file_exist_in_nas(self, file_path, user_id, retry=False, max_retries=3, retry_delay=30):
        abs_file_path = "/data/wd/diskVolume0/restsdk/userRoots/{0}/{1}".format(user_id, file_path)
        for retries in range(max_retries):
            result = self.executeShellCommand('[ -e {} ] && echo "Found" || echo "Not Found"'.format(abs_file_path),
                                              consoleOutput=False)[0].strip()
            if result == "Found":
                return True
            else:
                if retry:
                    self.log.info('Cannot find file:{}, retry after 30 secs'.format(file_path))
                    time.sleep(retry_delay)
                else:
                    return False
        return False

    def upload_logs_to_sumologic(self):
        self.log.info('Upload logs to sumologic...')
        self.executeShellCommand('move_logs_manager.sh -i', consoleOutput=True, timeout=5*60)
        self.executeShellCommand('upload_logs_manager.sh -n', consoleOutput=True, timeout=5*60)

    def write_logcat(self, message, priority='V', tag='AutomationTest', buffer=None, console_output=False):
        self.log.info('Write logcat: {}'.format(message))
        args = []
        if priority: args.append('-p {}'.format(priority))
        if tag: args.append("-t '{}'".format(tag))
        if buffer: args.append('-b {}'.format(buffer))
        cmd = "log {} '{}'".format(' '.join(args), message)
        self.executeShellCommand(cmd, consoleOutput=console_output, _resend_when_timeout=True)

    def get_log_metrics(self, do_clean_log=False):
        self.log.info('Get device metrics logs...')
        if do_clean_log:
            self.clean_logcat()
        self.executeShellCommand('log_metrics.sh')
        stdout, stderr = self.executeShellCommand('logcat -d | grep METRICS')
        return stdout

    def is_any_FFmpeg_running(self, trace_zombie=False):
        if trace_zombie:
            self.log.info('>>>>>>>>>>>>>>>>>>>>>>>>> ffmpeg Monitor >>>>>>>>>>>>>>>>>>>>>>>>>')
            stdout, stderr = self.executeShellCommand("busybox ps -o pid,ppid,stat,comm,args | grep -v 'grep -E ffmpeg|rest' | grep -E 'ffmpeg|rest' | tail")
            if ' Z  ' in stdout:
                self.log.warning('Zombie process found!')
            if ' 1 Z ' in stdout:
                stdout, _ = self.executeShellCommand("busybox ps -o pid,ppid,stat,comm,args | grep -v 'grep -E 1 Z    ffmpeg' | grep -E '1 Z    ffmpeg' | wc -l", consoleOutput=False)
                self.log.error('init-child zombie process: {}'.format(stdout))
            self.log.info('<<<<<<<<<<<<<<<<<<<<<<<<< ffmpeg Monitor <<<<<<<<<<<<<<<<<<<<<<<<<')
        stdout, stderr = self.executeShellCommand("busybox ps -ef | grep -v 'grep /system/bin/ffmpeg' | grep /system/bin/ffmpeg")
        return True if stdout else False

    def kill_first_found_FFmpeg(self, signal=13):
        self.log.info('Send singal -{} to the first found FFmpeg'.format(signal))
        self.executeShellCommand("busybox ps -ef | grep -v 'grep /system/bin/ffmpeg' | grep /system/bin/ffmpeg | busybox awk '{print $1}' | xargs kill -%s" % signal)

    def wait_all_FFmpeg_finish(self, delay=10, timeout=60, time_to_kill=None):
        start_time = time.time()
        while self.is_any_FFmpeg_running():
            now_time = time.time()
            if now_time >= start_time+timeout:
                return False
            if time_to_kill is not None and now_time >= start_time+time_to_kill:
                self.log.warning('Timeout wait {} sec, try to kill FFmpeg'.format(time_to_kill))
                self.kill_first_found_FFmpeg()
            self.log.info('Waiting {} sec for all FFmpeg to finish...'.format(delay))
            time.sleep(delay)
        return True

    def is_any_FFmpeg_zombie_existing(self):
        stdout, stderr = self.executeShellCommand("busybox ps -o pid,ppid,stat,comm,args | grep -v 'grep -E ffmpeg|rest' | grep -E 'ffmpeg|rest'")
        return True if ' Z  ' in stdout else False

    def wait_all_FFmpeg_zombie_exit(self, delay=10, timeout=60*5):
        start_time = time.time()
        while self.is_any_FFmpeg_zombie_existing():
            now_time = time.time()
            if now_time >= start_time+timeout:
                return False
            self.log.info('Waiting {} sec for all FFmpeg zombie to exit...'.format(delay))
            time.sleep(delay)
        return True

    def reboot_if_zombie_found(self, wait_for_zombie_exit=60, wait_for_reboot=30*60, wait_for_boot_up=30*60):
        """ This is workaround for zombie issue.
        [Return]
            True if rebooted / False do nothing.
        """
        self.log.info('Zombie process checking...')
        if self.wait_all_FFmpeg_zombie_exit(timeout=wait_for_zombie_exit):
            return False
        # Reboot device when zombie process found.
        self.log.warning('Zombie process still exist! Reboot this device!')
        self.reboot_device_and_wait_boot_up(wait_for_reboot, wait_for_boot_up)
        return True

    def reboot_device_and_wait_boot_up(self, wait_for_reboot=30*60, wait_for_boot_up=30*60):
        self.executeShellCommand('busybox nohup reboot')
        # Wait for reboot.
        self.log.info('Expect device do reboot in {} secs...'.format(wait_for_reboot))
        if not self.wait_for_device_to_shutdown(timeout=wait_for_reboot):
            raise RuntimeError('Device does not reboot after {} secs.'.format(wait_for_reboot))
        # Wait for boot up.
        self.log.info('Device has been rebooted. Expect device boot up in {} secs...'.format(wait_for_boot_up))
        if not self.wait_for_device_boot_completed(timeout=wait_for_boot_up):
            self.log.error('Device seems down.')
            raise RuntimeError('Device does not boot up after {} secs.'.format(wait_for_boot_up))
        self.log.info('Device reboot complete.')

    def is_machine_time_correct(self, tolerance_sec=60):
        # To verify target machine time with local host system time.
        machine_time = self.get_machine_time()
        local_time = self.get_local_machine_time()
        if (local_time + tolerance_sec) >= machine_time >= (local_time - tolerance_sec):
            return True
        return False

    def get_led_logs(self, log_filter=None):
        led_list = []
        led_logcat = self.executeShellCommand('logcat -d -b system | grep LedServer')[0]
        if led_logcat:
            led_logcat_lines = led_logcat.splitlines()
            if log_filter:
                led_logcat_lines = log_filter(led_logcat_lines)
            for line in led_logcat_lines:
                if 'sys state change' in line:
                    led_re = re.compile("\((.+)\).->.\((.+)\)")
                    type = 'SYS'
                elif 'Switching Led state' in line:
                    led_re = re.compile("\((.+)\)->\((.+)\)")
                    type = 'LED'
                else:
                    continue

                results = led_re.search(line)
                if results:
                    string_split = line.split()
                    led_dict = {
                        'date': string_split[0],
                        'time': string_split[1],
                        'type': type,
                        'before': results.group(1),
                        'after': results.group(2)
                    }
                    led_list.append(led_dict)
        else:
            self.log.warning('There are no LED info in logcat!')

        return led_list

    def print_led_info(self, led_list):
        if led_list:
            self.log.info("*** Start printing LED info ***")
            for led in led_list:
                self.log.info('{} {} [Type] {} [Before] {} [After] {}'.format(
                    led.get('date'),
                    led.get('time'),
                    led.get('type'),
                    led.get('before'),
                    led.get('after'))
                )
            self.log.info("*** Print LED info complete ***")

    def check_PIP_status(self):
        try:
            pip_check = self.executeShellCommand("getprop | grep pip")
            pip_check2str = ''.join(pip_check)
            pipStatus = pip_check2str.split(":", 1)[1].split("[")[1].split("]")[0]
            return pipStatus
        except Exception as ex:
            self.log.error("Failed to check PIP status. Interrupt the testing. Err: {0} ".format(ex))
            return

    def check_sumo_URL(self):
        try:
            #self.log.info("To Verify sumo URL exist or not.")
            sumoURL_check = self.executeShellCommand('getprop | grep sumo')
            sumoURL_check2string = ''.join(sumoURL_check)
            URL = sumoURL_check2string.split(":", 1)[1].split("[")[1].split("]")[0]
            return URL
        except Exception as ex:
            self.log.error("Failed to check sumo url. Interrupt the testing. Err: {0} ".format(ex))
            return

    def get_hashed_mac_address(self, interface=None):
        if not interface:
            interface = 'wlan0'
        try:
            stdout, stderr = self.executeShellCommand("cat /sys/class/net/{}/address | xargs echo -n | tr 'A-Z' 'a-z' | md5sum -b".format(interface))
            if 'No such file or directory' in stdout:
                self.log.error("Failed to get hashed mac address.")
                return
            else:
                return stdout.rstrip()
        except Exception as ex:
            self.log.error("Failed to get hashed mac address in realtime. Interrupt the testing. Err: {0} ".format(ex))
            return

    def get_pipstatus(self):
        try:
            pipStatus = self.executeShellCommand("configtool pipstatus")
            pipStatus = ''.join(pipStatus)
            return pipStatus
        except Exception as ex:
            self.log.error("Failed to get pipstatus in realtime. Interrupt the testing. Err: {0} ".format(ex))
            return

    def get_fileserver_url(self):
        stdout, _ = self.executeShellCommand(cmd='ping -W 1 -c 1 {} > /dev/null 2>&1; echo $?'.format(constants.FILESERVER_TW_MVWARRIOR), consoleOutput=False)
        if stdout.rstrip() == '0':
            return constants.FILESERVER_TW_MVWARRIOR
        return constants.FILESERVER_TW_CORPORATE
