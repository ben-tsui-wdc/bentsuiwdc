# @ Author: Ben Tsui <ben.tsui@wdc.com>

# std modules
import os
import re
import math
import json
import time
from datetime import datetime
from base64 import b64encode
# 3rd party modules
import paramiko
from scp import SCPClient
import lxml.etree
# platform modules
import common_utils
import constants
from constants import Godzilla as GZA, KDP
from platform_libraries.common_utils import execute_local_cmd
from platform_libraries.pyutils import retry, NotSet
from platform_libraries.paser_utls import parse_mdstat, parse_mdadm, parse_smart


def retry_connect(method):
    def wrapper(self, *args, **kwargs):

        def fail_reconnect_method(method, self, *args, **kwargs):
            try:
                return method(self, *args, **kwargs)
            except paramiko.ssh_exception.SSHException as e:
                self.log.info("Got error: {}, try to reconnect the ssh after 60 seconds, then raise the error later".format(repr(e)))
                time.sleep(60)
                self.connect()
                if 'scp_' in method.__name__:
                    self.scp_connect()
                if 'sftp_' in method.__name__:
                    self.sftp_connect()
                self.log.info('Raise the error...')
                raise

        # for retry function
        retry_args = [fail_reconnect_method, Exception, NotSet, 60, 10, self.log.info, False]
        # for fail_reconnect_method function
        retry_args += [method, self]
        retry_args += args
        return retry(*retry_args, **kwargs)
    return wrapper


class SSHClient(object):
    """
        Create a SSH client to connect to a server and execute commands
        Usage:
                import SSHClient
                ssh = SSHClient()
                ssh.connect(hostname, username, password, port)
                ssh.execute(cmd)
                ssh.close()
    """

    def __init__(self, hostname, username, password, port=22, root_log='KAT',
                 root_password=None, stream_log_level=None, timeout=300):
        self.hostname = hostname
        self.username = username
        self.password = password
        self.port = port
        self.client = None
        self.sftp = None
        self.scp = None
        self.log = common_utils.create_logger(root_log=root_log, stream_log_level=stream_log_level)
        self.linesep = '\r\n'
        # for sudo
        self.root_password = root_password if root_password else password
        self.remove_strings = [
            '[sudo] password for {}: '.format(username),  # prompt message.
            root_password  # root password.
        ]
        self.timeout = timeout
        # set default cert. it should no effect to the devices not use securing access.
        self.key_filename = os.path.dirname(__file__) + '/ssh_cert/id_ecdsa'

    def connect(self, retry=True, max_times=12):
        if not retry:
            self._connect()
            return

        for idx in xrange(max_times):
            try:
                self._connect()
                return
            except Exception:
                if idx == max_times-1:
                    self.log.error('Failed to establish SSH connection.')
                    return
                self.log.info(
                    'Failed to establish SSH connection. Try again after 15 secs. (Remaining {} times)'
                        .format(max_times-idx-1))
                time.sleep(15)

    def _connect(self):
        self.log.info('Connecting {} via ssh'.format(self.hostname))
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            self.client.connect(
                self.hostname, username=self.username, password=self.password, port=self.port,
                timeout=300, key_filename=self.key_filename)
        except Exception as e:
            self.log.error(e, exc_info=True)
            raise
        self.log.info('SSH connection established')

    def ssh_is_connected(self):
        if self.client and self.client.get_transport() is not None:
            return True
        else:
            return False

    def update_device_ip(self, ip):
        self.log.info('Current IP: {} now change to IP: {}...'.format(self.hostname, ip))
        self.close_all()
        self.hostname = ip
        return self.check_ssh_connectable()

    def close_all(self):
        self.log.info('Closing current connection')
        try:
            self.sftp_close()
        except Exception as e:
            pass
        try:
            self.scp_close()
        except Exception as e:
            pass
        try:
            self.close()
        except Exception as e:
            pass

    def execute(self, command, timeout=""):
        if not timeout:
            timeout = self.timeout
        self.log.debug('Executing command: {}'.format(command))
        stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
        return self._response(command, stdin, stdout, stderr)

    def _execute_cmd(self, cmd):
        """
            Used to retry the ssh connection in the execute_cmd method
        """
        try:
            stdin, stdout, stderr = self.client.exec_command(cmd)
            stdin.close()
            return stdin, stdout, stderr
        except Exception as e:
            self.log.info("Send command failed due to: {}, try to reconnect the ssh after 60 seconds".format(repr(e)))
            time.sleep(60)
            self.connect()
            raise

    def execute_cmd(self, command, quiet=False, timeout="", stop_on_timeout=False):
        # For Godzilla project
        if not timeout:
            timeout = self.timeout
        log_msg = 'Executing command: {}'.format(command)

        stdin, stdout, stderr = retry(func=self._execute_cmd, excepts=Exception, cmd=command, log=self.log.info)

        # This is a workaround to force stdout close when it's hanged
        endtime = time.time() + timeout
        while not stdout.channel.eof_received:
            time.sleep(5)
            if time.time() > endtime:
                self.log.warning(
                    'stdout hanged for {} seconds while executing "{}", force to close the channel!'.format(timeout,
                                                                                                            command))
                stdout.channel.close()
                if stop_on_timeout:
                    raise Exception("The ssh command was timed out after {} seconds!".format(timeout))
                else:
                    break

        stdout = str(stdout.read()).strip()
        stderr = str(stderr.read()).strip()
        if quiet:
            self.log.debug(log_msg)
            self.log.debug("\tstdout: {}".format(stdout))
            self.log.debug("\tstderr: {}".format(stderr))
        else:
            self.log.info(log_msg)
            self.log.info("\tstdout: {}".format(stdout))
            if stderr:
                self.log.warning("\tstderr: {}".format(stderr))
        return stdout, stderr

    def remount_and_execute_cmd(self, remount_path, command):
        self.execute_cmd('mount -o rw,remount {}'.format(remount_path))
        self.execute_cmd(command)
        self.execute_cmd('mount -o ro,remount {}'.format(remount_path))

    def remount_usb(self, usb_path, max_retry=10, raise_error=True):
        self.log.info("Remounting USB")
        status, _ = self.execute("mount | grep USB | grep 'ro,'")
        try_times = 0
        while status == 0:
            try_times+1
            self.execute("mount -o rw,remount {}".format(usb_path))
            time.sleep(3)
            status, _ = self.execute("mount | grep USB | grep 'ro,'")
            if status != 0 and try_times == max_retry:
                if raise_error: raise RuntimeError("Failed to remount USB")
                self.log.error("Failed to remount USB")

    def _response(self, command, stdin, stdout, stderr):
        stdin.close()
        error = str(stderr.read())
        if error:
            output = "Execute command: {} failed, error message: {}".format(command, error)
            if 'Resource busy' in error or 'File exists' in error:
                self.log.warning(output)

            # Because Python will regard the result as stderr if using "time tmutil startbakup".
            # Need to think a better solution.
            elif 'time ' in command:
                output = str(stdout.read()) + error
            else:
                self.log.error(output)
        else:
            output = str(stdout.read())
        # Remove sudo message.
        output = self.linesep.join(line for line in output.split(self.linesep) if line not in self.remove_strings)
        self.log.info(command)
        self.log.info('{}'.format(output))

        return stdout.channel.recv_exit_status(), output.strip()

    def execute_background(self, command):
        self.log.debug('Executing command: {}'.format(command))
        channel = self.client.get_transport().open_session()
        channel.exec_command('{} > /dev/null 2>&1 &'.format(command))

    def sudo_execute(self, command):
        if not self.root_password:
            raise ValueError('No root_password')
        session = self.client.get_transport().open_session()
        session.get_pty()  # Get pseudo-terminal for interactive TTY.
        # session.exec_command("sudo bash -c \"" + command + "\"")  # Jason are not sure why it needs "bash -c" here.
        session.exec_command("sudo {}".format(command))
        # Generate response of SSHClient.
        stdin = session.makefile('wb', -1)
        stdout = session.makefile('r', -1)
        stderr = session.makefile_stderr('r', -1)
        # Auto type root's password.
        stdin.write(self.root_password + '\n')
        stdin.flush()
        return self._response(command, stdin, stdout, stderr)

    def close(self):
        if self.client:
            self.log.info('Closing SSH connection')
            try:
                self.client.close()
            except Exception as e:
                self.log.warning(e)

    # ======================================================================================#
    #                                         SFTP                                         #
    # ======================================================================================#

    """
        Once the SSH client connection is ready, call sftp_connection to create a new
        SFTPClient session object, and then upload/download/stat command can be executed.
    """

    def sftp_connect(self):
        self.sftp = self.client.open_sftp()

    def sftp_upload(self, localpath, remotepath):
        self.sftp.put(localpath, remotepath)

    def sftp_download(self, remotepath, localpath):
        self.sftp.get(remotepath, localpath)

    def sftp_stat(self, path):
        """ Retrieve a file information on the remote system """
        return self.sftp.stat(path)

    def sftp_chdir(self, path):
        """ Change current directory of this SFTP session """
        self.sftp.chdir(path)

    def sftp_close(self):
        if self.sftp:
            try:
                self.sftp.close()
            except Exception as e:
                self.log.warning(e)
            self.sftp = None

    # ======================================================================================#
    # ..                                        SCP                                         #
    # ======================================================================================#

    """
        Once the SSH client connection is ready, call scp connection to create a new
        SCPClient session object, and then upload/download command can be executed.
    """

    def scp_connect(self):
        if self.scp:
           self.scp_close()
        self._scp_connect()

    def _scp_connect(self):
        self.log.info('Starting scp connection ...')
        self.scp = SCPClient(self.client.get_transport(), socket_timeout=600)

    @retry_connect
    def scp_upload(self, localpath, remotepath):
        self.scp.put(localpath, remotepath)

    @retry_connect
    def scp_download(self, remotepath, localpath=''):
        self.scp.get(remotepath, localpath)

    def scp_close(self):
        if self.scp: 
            self.log.info('Closing scp connection')
            try:
                self.scp.close()
            except Exception as e:
                self.log.warning(e)
            self.scp = None

    # ======================================================================================#
    #                                       MAC OS                                          #
    # ======================================================================================#

    def check_folder_exist(self, folder_path):
        self.log.info("Checking if folder: {} exist".format(folder_path))
        status, output = self.execute('[ -d {} ] && echo "Exist" || echo "NotExist"'.format(folder_path))
        return True if (status == 0 and output == "Exist") else False

    def check_file_exist(self, file_path):
        self.log.info("Checking if file: {} exist".format(file_path))
        status, output = self.execute('[ -e {} ] && echo "Exist" || echo "NotExist"'.format(file_path))
        return True if (status == 0 and output == "Exist") else False

    def create_folder(self, folder_path):
        self.log.info("Creating folder: {}".format(folder_path))
        self.execute('mkdir {}'.format(folder_path))

    def delete_folder(self, folder_path):
        self.log.info("Deleting folder: {}".format(folder_path))
        self.execute('rm -r {}'.format(folder_path))

    def delete_file(self, file_path):
        self.log.info("Deleting file: {}".format(file_path))
        self.execute('rm {}'.format(file_path))

    def check_folder_mounted(self, src_folder, dst_folder=None, protocol=None):
        self.log.info("Checking if folder: {} is mounted".format(src_folder))
        status, output = self.execute('mount | grep {}'.format(src_folder))
        if protocol:
            if protocol == 'afp' and 'afpfs' not in output:
                return False
            if protocol == 'smb' and 'smbfs' not in output:
                return False
        if dst_folder:
            if 'on {}'.format(dst_folder) not in output:
                return False
        return True if (status == 0 and output) else False

    def mount_folder(self, protocol, server, src_path, dst_path, username='', password=''):
        if protocol == "afp":
            mount_cmd = 'mount_afp'
            mount_url = 'afp://;auth=No%20User%20Authent'
        elif protocol == "smb":
            mount_cmd = 'mount_smbfs'
            if username and password:
                mount_url = '//{}:{}'.format(username, password)
            else:
                mount_url = '//GUEST:'
        else:
            self.log.warning("Please choose afp or smb protocol")
            exit(1)
        self.log.info("Mount folder: {} to {} via {}".format(src_path, dst_path, protocol))
        self.execute('{} "{}@{}/{}" {}'.format(mount_cmd, mount_url, server, src_path, dst_path))

    def unmount_folder(self, folder_path, force=False):
        self.log.info("Unmount folder: {}".format(folder_path))
        unmount_cmd = "umount"
        if force:
            unmount_cmd += " -f"
        unmount_cmd += " {}".format(folder_path)
        self.execute(unmount_cmd)

    def mount_afp_on_mac(self, afp_user=None, afp_password=None, share_location=None, mount_point=None):
        authentication = ''
        if afp_user:
            authentication = '{}{}@'.format(afp_user, ':' + afp_password if afp_password else '')
        mount_args = ('afp://' +
                      authentication +
                      share_location +
                      ' ' +
                      mount_point)
        # Run the mount command
        self.log.info('Mounting {} '.format(share_location))
        stdout = self.execute_cmd('mount_afp ' + mount_args)
        # check
        stdout, stderr = self.execute_cmd('df')
        for item in stdout.splitlines():
            if share_location in item and mount_point in item:
                return True
        return False

    def umount_afp_on_mac(self, mount_point=None):
        stdout, stderr = self.execute_cmd('umount {}'.format(mount_point))
        if stderr: 
            if 'not currently mounted' in stderr:
                pass
            else:
                return False
        # check
        stdout, stderr = self.execute_cmd('df')
        for item in stdout.splitlines():
            if mount_point in item:
                return False
        return True

    def get_file_list(self, folder_path):
        self.log.info("Getting file lists in folder: {}".format(folder_path))
        status, output = self.execute('ls -m1 {}'.format(folder_path))
        if output:
            file_list = output.split('\n')
        else:
            file_list = []

        return file_list

    def get_file_checksum(self, file_path):
        file_name = file_path.split('/')[-1] if '/' in file_path else file_path
        self.log.debug("Getting the checksum of file: {}".format(file_name))
        status, output = self.execute('/sbin/md5 {}'.format(file_path))
        if output and 'No such file or directory' not in output:
            checksum = output.split(' = ')[1]
            return checksum
        else:
            self.log.error("Unable to get checksum of file: {}, error message: {}".format(file_name, output))
            return None

    # ======================================================================================#
    #                                   Time Machine                                       #
    # ======================================================================================#

    """
        Enable root user first since most of tmutil command need root permission:
        a. https://support.apple.com/en-us/HT204012
        b. sudo vim /etc/ssh/sshd_config and set "PermitRootLogin yes"
    """

    def tm_version(self):
        stdout, stderr = self.execute_cmd('tmutil version')
        return stdout

    def tm_enable_autobackup(self):
        self.execute_cmd('tmutil enable')

    def tm_disable_autobackup(self):
        self.execute_cmd('tmutil disable')

    def tm_get_dest(self):
        cmd = 'tmutil destinationinfo'
        stdout, stderr = self.execute_cmd(cmd)

        if 'No destinations' in stdout:
            return None
        else:
            tm_dest_info = dict()
            lines = stdout.split('\n')
            for line in lines:
                if ':' in line:
                    line = line.split(':')
                    tm_dest_info[line[0].strip()] = line[1].strip()

            return tm_dest_info

    def tm_set_dest(self, path):
        stdout, stderr = self.execute_cmd('tmutil setdestination {}'.format(path))
        return stdout

    def tm_del_dest(self, dest_id):
        stdout, stderr = self.execute_cmd('tmutil removedestination {}'.format(dest_id))
        return stdout

    def tm_start_backup(self, dest_id=None, block=False, time=False, timeout=14400):
        cmd = 'tmutil startbackup'
        if dest_id:
            cmd += ' -d {}'.format(dest_id)

        if block:
            cmd += ' --block'

        if time:
            cmd = 'time ' + cmd

        stdout, stderr = self.execute_cmd(cmd, timeout=timeout)
        return stdout, stderr

    def tm_stop_backup(self):
        stdout, stderr = self.execute_cmd('tmutil stopbackup')
        return stdout

    def tm_backup_status(self):
        """
            The running status:
            Starting / ThinningPreBackup / Copying / ThinningPostBackup / Finishing
        """
        stdout, stderr = self.execute_cmd('tmutil status')
        tm_backup_info = dict()
        lines = stdout.split('\n')
        for line in lines:
            if ';' in line and '=' in line:
                line = line[:-1].split('=')
                tm_backup_info[line[0].strip()] = line[1].strip()

        return tm_backup_info

    def tm_latest_backup(self, parameter=None):
        cmd = 'tmutil latestbackup'
        if parameter:
            cmd = cmd + ' {}'.format(parameter)
        stdout, stderr = self.execute_cmd(cmd)
        return stdout

    def tm_list_backup(self):
        stdout, stderr = self.execute_cmd('tmutil listbackups')
        return stdout

    def tm_add_exclusion(self, path='*'):
        """
            The most common large size folders:
            /Applications
            /Library
            /Users
            /System
            /private
        """
        # Todo: Exclude some folder will get -50 error code
        stdout, stderr = self.execute_cmd('tmutil addexclusion {}'.format(path))
        return stdout

    def tm_del_exclusion(self, path='*'):
        stdout, stderr = self.execute_cmd('tmutil removeexclusion {}'.format(path))
        return stdout

    def tm_is_excluded(self, path='*'):
        stdout, stderr = self.execute_cmd('tmutil isexcluded {}'.format(path))
        return stdout

    def tm_restore(self, src, dest):
        """
            Just like the same way to use cp command to copy files.
            Use tm_latest_backup to get the path of backup image
            Example: tmutil restore Volumes/Time\ Machine\ Backups/{backup_path}/photo.jpg ./photo-restore.jpg
        """
        self.log.info("tmutil restore is starting...")
        stdout, stderr = self.execute_cmd('tmutil restore {} {}'.format(src, dest))
        return stdout

    # ======================================================================================#
    #                                      GodZilla                                        #
    # ======================================================================================#

    """ Get Device Info libraries """

    def get_model_name(self):
        status, output = self.execute('cat /etc/model')
        if status != 0 or not output:
            return None
        else:
            if output == "WDMyCloud":
                model_name = "Glacier"
            elif output == "WDCloud":
                model_name = "Mirrorman"
            else:
                model_name = output.replace('MyCloud', '').replace('WD', '')  # for EX4100/2100 models
            return model_name

    def get_firmware_version(self):
        status, output = self.execute('cat /etc/version')
        if status != 0 or not output:
            return None
        else:
            return output

    def get_restsdk_service(self):
        status, output = self.execute('ps aux | grep restsdk-server | grep -v grep | grep -v restsdk-serverd')
        if status != 0 or not output:
            return None
        else:
            return output

    def get_restsdk_path(self):
        restsdk_daemon = self.get_restsdk_service()
        if restsdk_daemon:
            m = re.search('restsdk-server -configPath (.+) -crashLog.+', restsdk_daemon)
            if m: return m.group(1)
        else:
            self.log.warning('No restsdk config path found, use constants value')
            return GZA.RESTSDK_CONFIG_PATH

    def get_restsdk_configurl(self):
        restsdk_daemon = self.get_restsdk_service()
        restsdk_cfg_file = ''
        if restsdk_daemon:
            if 'minimal' in restsdk_daemon:
                self.disable_restsdk_minimal_mode()
                restsdk_daemon = self.get_restsdk_service()
            m = re.search('restsdk-server -configPath (.+) -crashLog.+', restsdk_daemon)
            if m: restsdk_cfg_file = m.group(1)
        else:
            self.log.warning('No restsdk config path found, use constants value')
            restsdk_cfg_file = GZA.RESTSDK_CONFIG_PATH

        if not restsdk_cfg_file:
            self.log.warning('Cannot find restsdk config path, check if it is OS3 or Bridge FW')
            return None

        stdout, stderr = self.execute_cmd('cat {} | grep configURL'.format(restsdk_cfg_file), timeout=30)
        if stdout:
            return stdout.split()[-1].strip('"')
        else:
            return None

    def get_restsdk_dataDir(self):
        restsdk_toml_file = self.get_restsdk_path()
        status, output = self.execute('cat {} | grep "dataDir ="'.format(restsdk_toml_file))
        if status == 0 and output:
            return output.split()[-1].strip('"')
        else:
            return None

    def get_restsdk_httpPort(self):
        restsdk_toml_file = self.get_restsdk_path()
        status, output = self.execute('cat {} | grep "httpPort ="'.format(restsdk_toml_file))
        if status == 0 and output:
            return output.split('=')[-1].strip()
        else:
            return None

    def get_service_urls_from_cloud(self, quiet=False):
        config_url = self.get_restsdk_configurl()
        stdout, stderr = self.execute_cmd("curl -s {}/config/v1/config".format(config_url), quiet=quiet)
        return json.loads(stdout).get('data').get('componentMap').get('cloud.service.urls')

    def get_device_environment(self):
        # Get cloud environment type: qa1, dev1, prod
        config_url = self.get_restsdk_configurl()
        if not config_url: # fake env for RND
            return 'qa1'
        if 'dev1' in config_url:
            return 'dev1'
        elif 'qa1' in config_url:
            return 'qa1'
        return 'prod'

    def get_mac_address(self, interface='eth0'):
        stdout, stderr = self.execute_cmd('cat /sys/class/net/{}/address'.format(interface))
        mac_address = stdout.strip()
        if len(mac_address) != 17:
            return None
        return mac_address

    def get_restsdk_version(self):
        return self.get_device_info(fields='version').get('version')

    def get_device_ready_status(self):
        return self.get_device_info(fields='ready').get('ready')

    def get_device_proxy_connect_status(self):
        return self.get_device_info(fields='proxyConnected').get('network').get('proxyConnected')

    def get_device_id(self):
        device_id = self.get_device_info(fields='id').get('id')
        self.log.info('Device ID: {}'.format(device_id))
        return device_id

    def get_otaclient_service(self):
        stdout, stderr = self.execute_cmd('ps aux | grep otaclient | grep -v grep | grep -v log_upload_freq')
        if not stdout:
            return None
        else:
            return stdout

    def get_otaclient_path(self):
        otaclient_daemon = self.get_otaclient_service()
        if otaclient_daemon:
            m = re.search('otaclient -configPath (.+)/etc/otaclient.toml', otaclient_daemon)
            if m:
                return m.group(1)
        return None

    def get_otaclient_configurl(self):
        otaclient_path = self.get_otaclient_path()
        if otaclient_path:
            stdout, strerr = self.execute_cmd('cat {}/etc/otaclient.toml | grep configURL'.format(otaclient_path))
            if stdout:
                return stdout.split()[-1].strip('"')
        return None

    def start_otaclient_service(self, timeout=10):
        # This cmd will usually hang and timeout, so the timeout value cannot be too long
        self.execute_cmd("sudo -u restsdk otaclient.sh start", timeout=timeout)

    def stop_otaclient_service(self, timeout=30):
        self.execute_cmd("otaclient.sh stop", timeout=timeout)

    def unlock_otaclient_service_kdp(self, timeout=10):
        self.execute("setprop persist.wd.ota.lock 0", timeout=timeout)

    def lock_otaclient_service_kdp(self, timeout=10):
        self.execute("setprop persist.wd.ota.lock 1", timeout=timeout)

    def restart_otaclient(self, timeout=10):
        # This cmd will usually hang and timeout, so the timeout value cannot be too long
        self.log.info("Restarting otaclient service")
        self.execute_cmd("otaclient.sh restart", timeout=timeout)
        if not self.get_otaclient_service():
            raise RuntimeError("Failed to restart otaclient service!")

    def restart_restsdk_service(self):
        self.stop_restsdk_service()
        self.start_restsdk_service()

    def start_restsdk_service(self):
        self.execute_cmd('sudo -u restsdk restsdk.sh start', timeout=30)

    def stop_restsdk_service(self):
        self.execute_cmd("restsdk.sh stop", timeout=30)

    def restart_nasadmin_service(self):
        self.stop_nasadmin_service()
        self.start_nasadmin_service()

    def start_nasadmin_service(self):
        self.execute_cmd('nasadmin.sh start', timeout=30)

    def stop_nasadmin_service(self):
        self.execute_cmd("nasadmin.sh stop", timeout=30)

    def clean_up_restsdk_service(self, restart_otaclient=False):  # For KDP/RnD use
        self.log.info('Start to clean up and restarting restsdk service')
        volume_path = constants.KDP.DATA_VOLUME_PATH.get(self.get_model_name())
        if self.check_is_rnd_device():
            restsdk_data_path = '{}/restsdk-data'.format(volume_path)
        else:
            restsdk_data_path = '{}/restsdk'.format(volume_path)
        restsdk_info_path = '{}/restsdk-info'.format(volume_path)

        self.execute_cmd('notify_cloud -s reset_button -n 136')
        self.stop_restsdk_service()
        self.execute_cmd('rm -rf {}'.format(restsdk_data_path), timeout=60*5)
        self.execute_cmd('rm -rf {}'.format(restsdk_info_path), timeout=60*5)
        self.start_restsdk_service()
        self.log.info('Checking restsdk service after restarted')
        self.check_restsdk_service()
        if restart_otaclient:
            self.restart_otaclient()

    def get_app_manager_service(self):
        stdout, stderr = self.execute_cmd('ps aux | grep appmgr | grep -v grep')
        if not stdout:
            return None
        else:
            return stdout

    def get_user_roots_path(self):
        stdout, strerr = self.execute_cmd('df | grep userRoots')
        if stdout:
            user_roots = stdout.split()[-1]
            if "userRoots" in user_roots:
                return user_roots
        return None

    def get_usb_paths(self):
        stdout, strerr = self.execute_cmd('df | grep /mnt/USB/')
        if stdout:
            usb_list = []
            for string in stdout.split():
                if '/mnt/USB' in string:
                    usb_list.append(string)
            self.log.info("USB list: {}".format(usb_list))
            return usb_list
        return None

    def get_system_time(self, executor, args='+%s', raise_error=True):
        executor('uname -a')
        stdout, stderr = executor('date {}'.format(args))
        sec_str = stdout.strip()
        if not sec_str.isdigit():
            if raise_error:
                raise RuntimeError('Get system time failed')
            return None
        return int(sec_str)

    def get_machine_time(self, *args, **kwargs):
        return self.get_system_time(executor=self.execute_cmd)

    def get_local_machine_time(self, sync_time=True, *args, **kwargs):
        if sync_time:
            self.log.info('Sync local machine time by ntpdate ...')
            self.execute_cmd('ntpdate -s pool.ntp.org')
        return self.get_system_time(executor=execute_local_cmd)

    def get_share_permission(self, name_list=[]):
        share_dict = {}
        share_list = self.execute_cmd('cat /var/www/xml/smb.xml', quiet=True)[0]
        if share_list:
            root = lxml.etree.fromstring(share_list)
            folders = root.findall('./samba/item')
            for folder in folders:
                name = folder.find('./name').text
                if name_list and name not in name_list:
                    continue
                else:
                    share_dict[name] = {}
                    share_dict[name]['path'] = folder.find('./path').text
                    share_dict[name]['public'] = folder.find('./public').text
                    if share_dict[name]['public'] == "no":
                        share_dict[name]['read_list'] = folder.find('./read_list').text
                        share_dict[name]['write_list'] = folder.find('./write_list').text
                        share_dict[name]['invalid_users'] = folder.find('./invalid_users').text
                    share_dict[name]['ftp_enable'] = folder.find('./ftp_enable').text
                    share_dict[name]['nfs_enable'] = folder.find('./nfs_enable').text
            return share_dict
        else:
            raise RuntimeError("Cannot get the share permissions from smb.xml!")

    def get_local_ota_status(self):
        result = self.execute_cmd('cat /var/log/otaclient.log | grep -rni "updateStatus"', quiet=True)[0]
        regex = r'.+,"status":"(\S+)","time"'
        matches = re.findall(regex, result)
        if matches:
            return matches[-1]
        else:
            return None

    def get_local_ota_download_progress(self):
        result = self.execute_cmd('cat /var/log/otaclient.log | grep -rni "downloadProgress"', quiet=True)[0]
        regex = r'.+,"percent":(\S+),"rateKBs":(\S+),"time"'
        matches = re.findall(regex, result)
        if matches:
            return matches[-1]
        else:
            return None, None

    def get_db_migration_info(self):
        log_path = "/var/log/wdpublic.log"
        result = self.execute_cmd('cat {} | grep migrated'.format(log_path), quiet=True)[0]
        if result:
            regex = r'restsdk\[\d+\]:.+({.+\"fn\":\"[Mm]igrate\".+})'
            matches = re.findall(regex, result)
            if matches:
                db_info_list = []
                for db_info in matches:
                    db_info_list.append(json.loads(db_info))
                return db_info_list
            else:
                self.log.warning("Cannot find DB migration related info!")
        else:
            self.log.warning("No log information in {}!".format(log_path))
        return None

    def get_fts_rebuild_info(self):
        log_path = "/var/log/wdpublic.log"
        result = self.execute_cmd('cat {} | grep rebuildFTSEnd'.format(log_path), quiet=True)[0]
        if result:
            regex = r'restsdk\[\d+\]:.+({.+\"fn\":\"rebuildFTS.+})'
            match = re.findall(regex, result)
            if match:
                return json.loads(match[0])
        self.log.warning("Cannot find FTS rebuild info!")
        return None

    def get_folder_md5_checksum(self, path):
        result = self.execute_cmd("find " + path +
                                  " -type f -exec busybox md5sum {} + | awk '{print $1}'" 
                                  " | sort | busybox md5sum | awk '{print $1}'")[0]
        if result:
            self.log.info("Folder MD5 checksum: {}".format(result))
            return result
        else:
            self.log.warning("Cannot get the folder MD5 checksum info!")
            return None

    """ Device Check libraries """

    def check_ssh_connectable(self):
        self.log.info("Checking if SSH is connectable, attempt to connect...")
        try:
            self.connect(retry=False)
            self.log.info("SSH is connected")
            return True
        except:
            self.log.info('Cannot connect device by SSH')
        return False

    def check_platform_bootable(self):
        self.log.info("Checking if the system is boot up and ready...")
        stdout, stderr = self.execute_cmd('[ -f /tmp/system_ready ] && echo "Found" || echo "Not found"', quiet=True)
        if 'Found' in stdout:
            self.log.info("Found /tmp/system_ready flag, system is ready")
            return True
        return False

    def check_device_pingable(self):
        if common_utils.check_port_pingable(self.hostname, self.port):
            return True
        self.close()
        return False

    def check_machine_time_correct(self, sync_local_time=False, tolerance_sec=60):
        # To verify target machine time with local host system time.
        machine_time = self.get_machine_time()
        local_time = self.get_local_machine_time(sync_time=sync_local_time)
        if (local_time + tolerance_sec) >= machine_time >= (local_time - tolerance_sec):
            return True
        return False

    def check_hdd_ready_to_upgrade_fw(self):
        self.log.info("Checking if HDD is ready before upgrading FW or installing APKGs")
        self.execute_cmd('upload_firmware -c auto > /dev/null 2>&1')
        self.log.info("Wait for 30 seconds to verify the check status")
        time.sleep(30)
        stdout, stderr = self.execute_cmd('cat /var/www/xml/check_disk_size_status.xml')
        if stdout:
            root = lxml.etree.fromstring(stdout)
            hdd_status = root.text
            if hdd_status == '0':
                return True
            else:
                return False
        else:
            return False

    def check_file_in_device(self, file_path):
        self.log.info("Checking if file: {} is in test device".format(file_path))
        result = self.execute_cmd('[ -e {} ] && echo "Exist" || echo "NotExist"'.format(file_path))[0]
        if result == "Exist":
            return True
        else:
            return False

    def check_folder_in_device(self, folder_path):
        self.log.info("Checking if folder: {} is in test device".format(folder_path))
        result = self.execute_cmd('[ -d {} ] && echo "Exist" || echo "NotExist"'.format(folder_path))[0]
        if result == "Exist":
            return True
        else:
            return False

    def check_folder_is_empty(self, folder_path):
        return_code, output = self.execute('[ $(ls -A {} | wc -l) -ne 0 ] && echo "contains files" || echo "empty"'
                                           .format(folder_path))
        if return_code != 0:
            raise RuntimeError('Failed to check file exist in folder: {0}! Return code: {1}'
                               .format(folder_path, return_code))
        elif output == 'empty':
            return True
        else:
            return False

    def check_hdd_in_standby_mode(self):
        self.log.info("Checking if the HDD is in standby mode")
        result = self.execute_cmd('cat /var/log/user.log | grep set_pwm | tail -1')[0]
        if result:
            if "stand by now" in result:
                self.log.info("HDD is in standby mode!")
                return True
            elif "awake now" in result:
                self.log.info("HDD is in awake mode!")
                return False
            else:
                raise RuntimeError("Unknown logs: {}".format(result))
        else:
            self.log.warning("Cannot find any log, HDD might be in awake status")
            return False

    def check_restsdk_service(self):

        def is_timeout(timeout): return time.time() - self.start >= timeout

        self.start = time.time()
        while not is_timeout(60*3):
            # Execute command to check restsdk is running
            exitcode, _ = self.execute('pidof restsdk-server')
            exitcode2, _ = self.execute('pidof restsdk-serverd')
            if exitcode == 0 and exitcode2 == 0:
                self.log.info('Restsdk-server is running')
                break
            time.sleep(3)
        else:
            raise RuntimeError("Restsdk-server is not running after wait for 3 mins")

        # Sometimes following error occurred if making REST call immediately after restsdk is running.
        # ("stdout: curl: (7) Failed to connect to localhost port 80: Connection refused)
        # Add retry mechanism for get device info check
        self.start_time = time.time()
        while not is_timeout(60*2):
            # Execute sdk/v1/device command to check device info to confirm restsdk service running properly
            url = 'http://localhost:{}/sdk/v1/device'.format(self.get_restsdk_httpPort())
            stdout, stderr = self.execute_cmd('curl {}?fields=ready'.format(url), quiet=True)
            if 'Connection refused' in stderr:
                self.log.warning('Connection refused happened, wait for 5 secs and try again...')
                time.sleep(5)
            else:
                break
        else:
            raise RuntimeError("Connected to localhost failed after retry for 2 mins ...")

    def ls(self, path):
        return self.execute_cmd("ls -al '{}'".format(path), quiet=True)[0]

    def grep_value_in_conf(self, value, conf_path):
        return self.execute_cmd("grep '{}' {}".format(value, conf_path), quiet=True)[0]

    def value_exits_in_conf(self, value, conf_path):
        output = self.grep_value_in_conf(value, conf_path)
        if output:
            self.log.debug('{} exists in {}'.format(value, conf_path))
            return True
        self.log.debug("{} doesn't exist in {}".format(value, conf_path))
        return False

    def user_exists_in_shadow_conf(self, user_name):
        return self.value_exits_in_conf(value=user_name + ':', conf_path=KDP.SHADOW_CONF_PATH)

    def user_exists_in_group_conf(self, user_name):
        return self.value_exits_in_conf(value=',' + user_name, conf_path=KDP.GROUP_CONF_PATH)

    def user_exists_in_passwd_conf(self, user_name):
        return self.value_exits_in_conf(value=user_name + ':', conf_path=KDP.PASSWD_CONF_PATH)

    def user_exists_in_smb_passwd_conf(self, user_name):
        return self.value_exits_in_conf(value=user_name + ':', conf_path=KDP.SMB_PASSWD_CONF_PATH)

    def value_exists_in_smb_conf(self, value):
        return self.value_exits_in_conf(value=value, conf_path=KDP.SMB_CONF_PATH)

    def user_exists_in_kdp_system(self, user_name):
        exists = True
        exists &= self.user_exists_in_shadow_conf(user_name)
        exists &= self.user_exists_in_group_conf(user_name)
        exists &= self.user_exists_in_passwd_conf(user_name)
        exists &= self.user_exists_in_smb_passwd_conf(user_name)
        exists &= self.value_exists_in_smb_conf(user_name)
        return exists

    def user_not_exist_in_kdp_system(self, user_name):
        exists = False
        exists |= self.user_exists_in_shadow_conf(user_name)
        exists |= self.user_exists_in_group_conf(user_name)
        exists |= self.user_exists_in_passwd_conf(user_name)
        exists |= self.user_exists_in_smb_passwd_conf(user_name)
        exists |= self.value_exists_in_smb_conf(user_name)
        return exists

    def space_exists_in_smb_conf(self, space_name):
        return self.value_exists_in_smb_conf(space_name)

    def path_exists(self, path):
        if self.ls(path):
            return True
        return False

    def share_exists(self, share_name):
        return self.path_exists('{}{}'.format(KDP.SHARES_PATH, share_name))

    """ Device Utils """

    def ping(self, url, timeout=5, count=1):
        stdout, _ = self.execute_cmd('ping -W {} -c {} {}; echo [exitCode=$?]'.format(timeout, count, url))
        if '[exitCode=0]' in stdout:
            return True
        return False

    def getprop(self, name=None, grep=None):
        cmd = 'getprop'
        if name:
            cmd = 'getprop {}'.format(name)
        elif grep:
            cmd = 'getprop | grep {}'.format(grep)

        stdout, _ = self.execute_cmd(cmd)
        resp = stdout.strip()
        if grep:
            resp = resp.rsplit('[', 1)[1][:-1]
        return resp

    def reboot_device(self):
        if self.check_file_in_device('/tmp/system_ready'):
            self.execute_cmd('rm /tmp/system_ready')
        self.execute_background('do_reboot')

    def unsafe_reboot_device(self):
        self.execute_background('reboot')

    def wait_for_device_to_shutdown(self, timeout=60 * 15, pingable_count=2):
        start_time = time.time()
        current_count = 0
        log_frequency = 10  # 10 * 1 secs = print per 10 secs
        while timeout > time.time() - start_time:
            if not self.check_device_pingable():
                current_count += 1
                self.log.info('Device is not pingable for {} time...'.format(current_count))
                if current_count >= pingable_count:
                    self.log.info('Device is shutdown')
                    self.close()
                    end_time = time.time()
                    self.log.warning('Shutdown duration: {} secs'.format(end_time - start_time))
                    return True
            else:
                log_frequency -= 1
                if log_frequency == 0:
                    log_frequency = 10  # Restore the counts
                    self.log.info('Waiting for device to shutdown, already wait for {} seconds'.
                                  format(math.ceil(time.time() - start_time)))
            time.sleep(1)
        self.log.warning('Device still works')
        return False

    def wait_for_device_boot_completed(self, timeout=60 * 10, time_calibration_retry=True, max_retries=10,
                                       retry_delay=30, disable_ota=False):
        self.log.info("Waiting for the device boot completed...")
        start_time = time.time()
        while timeout > time.time() - start_time:
            if self.check_ssh_connectable():
                break
            time.sleep(20)

        while timeout > time.time() - start_time:
            if self.check_platform_bootable():
                break
            time.sleep(20)

        if not (timeout > time.time() - start_time):
            self.log.warning('Timeout exceeded! ({} seconds)'.format(timeout))
            return False

        # Todo: Check the replacement of "logcat" to get the time
        """
        if not (timeout > time.time() - start_time):
            self.log.info('Wait timeout: {}s'.format(timeout))
            return False
        for retries in range(1, max_retries+1):
            result = self.check_machine_time_correct(tolerance_sec=60)
            if result:
                self.log.info('Device boot completed')
                return True
            else:
                if time_calibration_retry:
                    self.log.info('Machine time is not correct, retry {} times after {} secs...'.format(retries, retry_delay))
                    self.ssh_client.execute('logcat -d | grep NetworkTimeUpdateService')
                    time.sleep(retry_delay)
                    if retries == max_retries:
                        return False
                else:
                    self.log.warning('No time calibration retry and Machine time is not correct !!!')
                    return True  # Return True even if machine time is not correct
        """
        return True

    def reboot_and_wait_for_boot_completed(self, timeout=60 * 10):
        self.reboot_device()
        self.wait_for_device_to_shutdown(timeout, pingable_count=5)
        self.wait_for_device_boot_completed(timeout)

    def download_file(self, download_url, dst_path="", retries=20, timeout=120 * 60, is_folder=False):
        self.log.info("Download URL: {}".format(download_url))
        wget_cmd = 'wget -nv -N -t {0} -T {1} {2} -P {3} --no-check-certificate'. \
            format(retries, timeout, download_url, dst_path)
        if is_folder:
            wget_cmd += ' -r -np -nd -R "index.html*"'

        self.execute_cmd(command=wget_cmd, timeout=timeout, stop_on_timeout=True)

    def enable_ftp_service(self):
        self.log.info("Enabling FTP service...")
        self.execute_cmd("xmldbc -s /app_mgr/ftp/setting/state 1")
        self.execute_cmd("ftp start", timeout=10)
        time.sleep(10)

    def enable_nfs_service(self):
        self.log.info("Enabling NFS service...")
        self.execute_cmd("xmldbc -s /system_mgr/nfs/enable 1")
        self.execute_cmd("nfs start", timeout=10)
        time.sleep(10)

    def create_user(self, username):
        self.log.info("Checking if the user: {} is already existing".format(username))
        if self.check_user_in_device(username):
            self.log.warning("User is already existing!")
        else:
            self.log.info("User is not existing, creating the user now")
            self.execute_cmd("account -a -u '{0}' -p '{1}'".format(username, username))
            if not self.check_user_in_device(username):
                self.log.error('Create user: "{}" failed!'.format(username))
                return False
            self.log.info("Creating a share folder for the user, set public=off since the user has a password")
            if not self.create_share(share_name=username, public=False):
                return False
        return True

    def delete_user(self, username):
        self.log.info("Checking if the user: {} is already existing".format(username))
        if self.check_user_in_device(username):
            self.log.info("User is exissting, deleting the user now")
            self.execute_cmd("account -d -u '{0}'".format(username))
            if self.check_user_in_device(username):
                self.log.error('User still exist, delete user: "{}" failed!'.format(username))
                return False
        else:
            self.log.warning("User is not existing, skip the delete step!")
        return True

    def check_user_in_device(self, username):
        result = self.execute_cmd('cat /etc/passwd | grep {}'.format(username))[0]
        if result:
            return True
        else:
            return False

    def get_local_users(self):
        output = self.execute_cmd('cat /etc/passwd')[0]
        return [l.split(':') for l in output.strip().splitlines()]

    def create_group(self, groupname):
        self.log.info("Checking if the group: {} is already existing".format(groupname))
        if self.check_group_in_device(groupname):
            self.log.warning("Group is already existing!")
        else:
            self.log.info("Group is not existing, creating the group now")
            self.execute_cmd("account -a -g '{0}'".format(groupname))
            if not self.check_group_in_device(groupname):
                self.log.error('Create group: "{}" failed!'.format(groupname))
                return False
        return True

    def delete_group(self, groupname):
        self.log.info("Checking if the group: {} is already existing".format(groupname))
        if self.check_group_in_device(groupname):
            self.log.info("Group is exissting, deleting the group now")
            self.execute_cmd("account -d -g '{0}'".format(groupname))
            if self.check_group_in_device(groupname):
                self.log.error('Group still exist, delete group: "{}" failed!'.format(groupname))
                return False
        else:
            self.log.warning("Group is not existing, skip the delete step!")
        return True

    def check_group_in_device(self, groupname):
        result = self.execute_cmd('cat /etc/group | grep {}'.format(groupname))[0]
        if result:
            return True
        else:
            return False

    def create_share(self, share_name, public=False):
        self.log.info("Creating share folder: {}".format(share_name))
        self.execute_cmd('smbif -a /mnt/HD/HD_a2/{}'.format(share_name))
        self.change_share_public_status(share_name, public=public)
        # There's no success response when creating a share folder, check the smb.xml data
        share_folders = self.get_share_permission()
        if share_name in share_folders.keys():
            self.log.info("Create share folder successfully!")
            return True
        else:
            self.log.error("Failed to create the share folder!")
            return False

    def change_share_public_status(self, share_name, public=False):
        if public:
            param = '-p'
            public_status = 'yes'
        else:
            param = '-t'
            public_status = 'no'
        self.log.info('Changing the share: "{0}" public status to: "{1}"'.format(share_name, public_status))
        self.execute_cmd('smbif {0} {1}'.format(param, share_name))
        share_status = self.get_share_permission(name_list=[share_name])
        if share_status:
            if share_status[share_name]['public'] != public_status:
                self.log.error('Change share public status failed!')
                return False
            else:
                self.log.info('Share public status is changed to "{}"!'.format(public_status))
        else:
            self.log.error('Unable to get the share status of share folder: {}'.format(share_name))
            return False
        return True

    def change_share_user_permission(self, share_name, user='admin', permission=2):
        # Permission-> 1:Read Only 2:Read Write 3:Deny
        if permission == 1:
            check_field = 'read_list'
            log_msg = "read only"
        elif permission == 2:
            check_field = 'write_list'
            log_msg = "read / write"
        elif permission == 3:
            check_field = 'invalid_users'
            log_msg = "deny"
        else:
            self.log.error('The user permission need to be an int value: 1(ro)/2(rw)/3(deny)!')
            return False

        self.log.info('Changing the permission of user: "{0}" to "{1}" in share folder: "{2}"'.
                      format(user, log_msg, share_name))
        self.execute_cmd('smbif -m {0} -s {1} -u {2}'.format(permission, share_name, user))
        share_status = self.get_share_permission(name_list=[share_name])
        if share_status:
            if user not in share_status[share_name][check_field]:
                self.log.error('Failed to change the share user permission!')
                return False
            else:
                self.log.info("The share user permission is changed to [{}]".format(log_msg))
        else:
            self.log.error('Unable to get the share status of share folder: {}'.format(share_name))
            return False
        return True

    def check_share_in_device(self, share_name):
        if self.execute_cmd("cat /var/www/xml/smb.xml | grep '<name>{}</name>'".format(share_name))[0]:
            return True
        return False

    def delete_share(self, share_name):
        self.log.info("Checking if the share: {} is already existing".format(share_name))
        if self.check_share_in_device(share_name):
            self.execute_cmd('smbif -b {}'.format(share_name))
            share_status = self.get_share_permission(name_list=[share_name])
            if share_status:
                self.log.error("Share folder still exist in the share status, delete share folder failed!")
                return False
            else:
                self.log.info("Delete share folder successfully!")
        else:
            self.log.warning("Share is not existing, skip the delete step!")
        return True

    def enable_share_ftp(self, share_name):
        # Todo: 1. Check if ftp is enabled in /etc/NAS_CFG/ftp.xml 2. specified permissions
        self.log.info("Enable the FTP access in share folder: {}".format(share_name))
        self.execute_cmd('ftp -A -n {0} -p /mnt/HD/HD_a2/{1} -r "" -w "#@allaccount#,#ftp#" -d ""'.
                         format(share_name, share_name))

    def disable_share_ftp(self, share_name):
        # Todo: Check if ftp is disabled in /etc/NAS_CFG/ftp.xml
        self.log.info("Disable the FTP access in share folder: {}".format(share_name))
        self.execute_cmd('ftp -D -n {}'.format(share_name))

    def enable_share_nfs(self, share_name):
        # Todo: 1. Check if nfs is enabled in ??? config 2. specified permissions
        self.log.info("Enable the NFS access in share folder: {}".format(share_name))
        self.execute_cmd("echo '\"/nfs/{}\" *(rw,all_squash,sync,no_wdelay,insecure_locks,insecure,"
                         "no_subtree_check,anonuid=501,anongid=1000)' >> /etc/exports".format(share_name))
        self.execute_cmd("exportfs -r")

    def disable_share_nfs(self, share_name):
        self.log.info("Disable the NFS access in share folder: {}".format(share_name))
        self.execute_cmd("sed -i '/\/nfs\/{}/d' /etc/exports".format(share_name))
        self.execute_cmd("exportfs -r")

    def get_fileserver_url(self):
        stdout, _ = self.execute_cmd(
            'ping -W 1 -c 1 {} > /dev/null 2>&1; echo $?'.format(constants.FILESERVER_TW_MVWARRIOR))
        if stdout.rstrip() == '0':
            return constants.FILESERVER_TW_MVWARRIOR
        return constants.FILESERVER_TW_CORPORATE

    def disable_restsdk_minimal_mode(self):
        restsdk_status = self.get_restsdk_service()
        if not restsdk_status:
            self.log.warning("RestSDK service was not started!")
        else:
            if "minimal" in restsdk_status:
                self.log.info("RestSDK is in minimal mode, enable the cloud access and restart the RestSDK service")
                self.execute_cmd("xmldbc -s /cloud/cloud_access 1")
                self.execute_cmd("xmldbc -D /etc/NAS_CFG/config.xml")
                self.execute_cmd("cp /etc/NAS_CFG/config.xml /usr/local/config/config.xml")
                self.execute_cmd("restsdk.sh restart", timeout=60)
                restsdk_status = self.get_restsdk_service()
                if "minimal" in restsdk_status:
                    raise RuntimeError('Failed to disable RestSDK minimal mode!')
                else:
                    self.log.info("RestSDK minimal mode was disabled successfully")
            else:
                self.log.info("RestSDK is not in minimal mode")

    def enable_restsdk_minimal_mode(self):
        restsdk_status = self.get_restsdk_service()
        if not restsdk_status:
            self.log.warning("RestSDK service was not started!")
        else:
            if "minimal" not in restsdk_status:
                self.log.info(
                    "RestSDK is not in minimal mode, disable the cloud access and restart the RestSDK service")
                self.execute_cmd("xmldbc -s /cloud/cloud_access 0")
                self.execute_cmd("xmldbc -D /etc/NAS_CFG/config.xml")
                self.execute_cmd("cp /etc/NAS_CFG/config.xml /usr/local/config/config.xml")
                self.execute_cmd("restsdk.sh restart", timeout=60)
                restsdk_status = self.get_restsdk_service()
                if restsdk_status and "minimal" not in restsdk_status:
                    raise RuntimeError('Failed to enable RestSDK minimal mode!')
                else:
                    self.log.info("RestSDK minimal mode was enabled successfully")
            else:
                self.log.info("RestSDK is in minimal mode")

    def remove_cloud_user_from_local_user(self, user):
        """ Make sure to remove the user before detach from device.
        Check user info:
            cat /var/www/xml/account.xml | grep -E 'entityID|email'
        """
        self.execute_cmd('account -m -u {} -e "" -b ""'.format(user))
        stdout, _ = self.execute_cmd('echo $?')
        if stdout != '0':
            raise RuntimeError('Fail to remove cloud user')

    def update_ota_interval(self, interval=60):
        old_ota_config_path = '/usr/local/modules/otaclient/etc/otaclient.toml'
        new_ota_config_path = '/shares/Public/otaclient.toml'
        self.log.info('Clone the ota config to a new path for rw permission')
        if not self.check_file_in_device(new_ota_config_path):
            self.execute_cmd('cp {} {}'.format(old_ota_config_path, new_ota_config_path))
        self.log.info('Check the original OTA interval')
        result = self.execute_cmd('cat {} | grep otaCheckInterval'.format(new_ota_config_path))[0]
        if result:
            old_interval = result.split(' = ')[-1]
            self.log.info('The original OTA interval is {}'.format(old_interval))
        else:
            raise RuntimeError('Cannot find the OTA interval info!')

        if int(old_interval) != int(interval):
            self.log.info("Update the OTA interval from {} to {} secs".format(old_interval, interval))
            self.execute_cmd("sed -i 's/otaCheckInterval = {0}/otaCheckInterval = {1}/g' {2}".
                             format(old_interval, interval, new_ota_config_path))
        else:
            self.log.info("The OTA interval is already {} secs".format(interval))

        self.log.info("Restart otacliet with new config")
        self.stop_otaclient_service()
        self.execute_cmd('/usr/local/modules/otaclient/bin/otaclient -configPath {} &'.
                         format(new_ota_config_path), timeout=30)
        if not self.get_otaclient_service():
            raise RuntimeError('OTA service failed to start with config: {}!'.format(new_ota_config_path))
        else:
            self.log.info("Setup the OTA interval to {} with config {} successfully!".
                          format(interval, new_ota_config_path))

    def update_ntp_status(self, status="on"):
        if status == "on":
            ntp_code = 0
        else:
            ntp_code = 1
        self.execute_cmd("xmldbc -s /system_mgr/time/ntp_enable {}".format(ntp_code))

    def update_device_date(self, year="2020", month="09", day="14", hour="21", minute="55", second="00"):
        import calendar
        # date format: mmddhhmmyyyy.ss
        date = "{0}{1}{2}{3}{4}.{5}".format(month, day, hour, minute, year, second)
        result = self.execute_cmd("SetDate {}".format(date))[0]
        if "{0} {1} {2}:{3}:{4} PDT {5}".format(calendar.month_abbr[int(month.replace("0", ""))],
                                                day, hour, minute, second, year) in result:
            self.log.info("Update device date PASS!")
        else:
            raise RuntimeError("Failed to update the device date! The result is {}".format(result))

    def delete_file_in_device(self, file_path):
        self.execute_cmd("test -f {0} && rm {0}".format(file_path))

    def create_dummyfiles(self, file_path, file_size):
        self.execute_cmd('dd if=/dev/urandom of={0} bs=1 count={1}'.format(file_path, file_size))

    def get_file_md5_checksum(self, file_path):
        if not self.check_file_in_device(file_path):
            raise RuntimeError("Cannot find the file: {} in test device!".format(file_path))
        result = self.execute_cmd('busybox md5sum {}'.format(file_path))[0]
        if result:
            md5_checksum = result.strip().split()[0]
        else:
            md5_checksum = None
        return md5_checksum

    def stop_logpp(self):
        self.log.info("Stopping LogPP process")
        return_code, output = self.execute("killall logpp")
        if return_code == 0:
            self.log.info("LogPP is stopped")
        elif return_code == 1:
            self.log.warning("LogPP was not exist, skip this step!")
        else:
            raise RuntimeError('Fail to stop LogPP process! Error code: {}'.format(return_code))

    def start_logpp(self, debug_mode=False):
        self.log.info("Starting LogPP service")
        cmd = "logpp -f /etc/kxlog_config.json"
        if debug_mode:
            cmd += " -d 1"
        self.execute_background(cmd)
        self.log.info("Wait 15 seconds after starting logpp process")
        time.sleep(15)

    def restart_logpp(self, debug_mode=False):
        self.stop_logpp()
        time.sleep(10)
        self.start_logpp(debug_mode)

    def log_rotate_kdp(self, force=True):
        # Force: like force rotate hourly, log will be rotated if file size > 0
        # Not force: like normal rotate every 15 minutes, log will be rotated if file size > 400 KB
        cmd = "/usr/sbin/rt_script.sh"
        if force:
            cmd += " force"
        self.execute_cmd(cmd)

    def log_upload_kdp(self, reason="Test"):
        # Reason can be "Test", "Reboot", "Shutdown"...etc.
        cmd = "logpp_client /tmp/logpp_socket/FilterAndUploader {}".format(reason)
        self.execute_cmd(cmd)

    def generate_logs(self, log_number=5, log_type="INFO", log_messages="dummy_test_logs"):
        """
            log_number:
            0: /var/log/appMgr.log
            1: /var/log/wdhwlib.log
            2: /var/log/nasAdmin.log
            3: /var/log/wdpublic.log, /var/log/wdlog.log
            4: /var/log/wdlog.log
            5: /var/log/analyticpublic.log
            6: /var/log/analyticprivate.log
            7: /var/log/otaclient.log
        """
        cmd = "analyticlog -f {0} -l {1} -s dummy_test_logs -m 12345 string:message:{2} number:code:1002".format(
            log_number, log_type, log_messages
        )
        self.execute_cmd(cmd)

    def get_device_serial_number(self):
        self.log.info("Getting the device serial number")
        status, output = self.execute('cat /proc/device-tree/factory/serial')
        if status != 0 or not output:
            return None
        else:
            return output.strip('\x00')

    def get_device_hostname(self):
        self.log.info("Getting the device hostname")
        status, output = self.execute('cat /etc/hostname')
        if status != 0 or not output:
            return None
        else:
            return output

    def get_mdstat(self, ignored=['md100', 'md0']):
        self.log.info("Getting information from mdstat")
        status, output = self.execute('cat /proc/mdstat')
        return parse_mdstat(output.split('\n'), ignored)

    def get_mdadm(self, md_name):
        self.log.info("Getting information from mdadm by name: " + md_name)
        status, output = self.execute('mdadm -D /dev/' + md_name)
        return parse_mdadm(output.split('\n'))

    def all_md_info(self):
        mdadms = {}
        mdstat = self.get_mdstat()
        for md_name in mdstat:
            v = self.get_mdadm(md_name)
            mdadms[md_name] = v
        return mdstat, mdadms

    def get_blocks_by_md(self, md_name):
        self.log.info("Getting blocks by name: " + md_name)
        status, output = self.execute("df -B1 /dev/" + md_name + " | grep " + md_name + " | awk '{print $2}'")
        if not output:
            raise AssertionError('Cannot found /dev/' + md_name)
        return int(output)

    def get_drive_slot_by_node(self, node_name):
        self.log.info("Getting drive by name: " + node_name)
        status, output = self.execute("getprop | grep slot | grep {}".format(node_name))
        if not output:
            raise AssertionError('Cannot found ' + node_name)
        return int(output[9:10])

    def get_drive_nodes(self):
        self.log.info("Getting drive nodes")
        status, output = self.execute('getprop | grep ".drive]"')
        return [(int(l.split('slot')[1].split('.', 1)[0]), '/dev/' + l.strip().rsplit('[', 1)[1][:-1])
                for l in output.split('\n')] # [(slotNumber, /dev/nodeName)]

    def get_smart_info(self, drive_node):
        self.log.info("Getting SMART information by drive node: " + drive_node)
        status, output = self.execute('smartctl -a ' + drive_node)
        return parse_smart(output.split('\n'))

    def get_all_smart_info(self):
        resp = {}
        for v in self.get_drive_nodes():
            resp[v[0]] = self.get_smart_info(v[1])
        return resp # {slotNumber: SMARTInfo}

    def clearFile(self, path):
        self.log.info("Clearing file: {}".format(path))
        status, output = self.execute('echo "" > "{}"'.format(path))
        if status != 0:
            raise AssertionError('Clear file: {}'.format(path))

    def clearAnalyticPublicLog(self):
        return self.clearFile(KDP.SystemLog.AnalyticPublic)

    def clearAnalyticPrivateLog(self):
        return self.clearFile(KDP.SystemLog.AnalyticPrivate)

    def getClientLogFromAnalyticPublicLog(self):
        self.log.info("Getting client logs from: {}".format(KDP.SystemLog.AnalyticPublic))
        status, output = self.execute('grep clientLogger {}'.format(KDP.SystemLog.AnalyticPublic))
        self.log.debug("Output: {}".format(output))
        return output.splitlines()

    def getClientLogFromAnalyticPrivateLog(self):
        self.log.info("Getting client logs from: {}".format(KDP.SystemLog.AnalyticPrivate))
        status, output = self.execute('grep clientLogger {}'.format(KDP.SystemLog.AnalyticPrivate))
        self.log.debug("Output: {}".format(output))
        return output.splitlines()

    def get_total_user_space(self, user_root=KDP.USER_ROOT_PATH):
        self.log.info("Getting total of user spaces")
        status, output = self.execute('ls /data/wd/diskVolume0/userStorage/ | grep auth | wc -l'.format(user_root))
        self.log.debug("Output: {}".format(output))
        return int(output)

    def wait_for_total_user_space_reach(self, to_number, delay=30, max_retry=240, user_root=KDP.USER_ROOT_PATH):
        self.log.info("Waiting for total user spaces reach to {}".format(to_number))
        count = retry(
            func=self.get_total_user_space, user_root=user_root,
            retry_lambda=lambda x: x < to_number,
            excepts=Exception, delay=delay, max_retry=max_retry, log=self.log.info
        )
        if count >= to_number:
            return True
        return False

    def docker_inspect(self, container_id):
        exitcode, output = self.execute("docker inspect {}".format(container_id))
        info_dict = json.loads(output)[0]
        return info_dict

    def docker_ps(self, app_id=None):
        exitcode, output = self.execute("docker ps")
        lines = output.splitlines()
        if not app_id:
            return lines[1:]
        if app_id:
            for line in lines:
                if self.get_app_container_search_key(app_id) in line:
                    return line

    @classmethod
    def get_app_container_search_key(cls, app_id):
        """ Return a pattern key to search app container in "docker ps".
        """
        return {
            'com.elephantdrive.elephantdrive': '/etc/start.sh',
            'com.plexapp.mediaserver.smb': 'init',
            'com.wdc.nasslurp': 'nasslurp',
            'com.stress-ng.test': 'stress-ng'
        }.get(app_id)

    def get_container_id(self, app_id):
        status_line = self.docker_ps(app_id)
        if status_line:
            return status_line.split()[0]

    def get_app_master_config(self):
        self.log.info("Getting info from appMaster.json")
        status, output = self.execute('cat /data/wd/diskVolume0/kdpappmgr/appStore/appMaster.json')
        self.log.debug("Output: {}".format(output))
        return json.loads(output)

    def get_app_log_type(self, app_id):
        found = False
        for config in self.get_app_master_config():
            if app_id in config['appId']:
                if 'logsToDisk' in config and config['logsToDisk']:
                    found = True
                    return True
        if not found:
            assert AssertionError('Not found APP({})'.format(app_id))
        return False

    """ Device Utils End """

    """ Transcoding libraries """

    def is_any_FFmpeg_running(self, trace_zombie=False, ignore_zombie=False):
        if trace_zombie:
            self.log.info('>>>>>>>>>>>>>>>>>>>>>>>>> ffmpeg Monitor >>>>>>>>>>>>>>>>>>>>>>>>>')
            stdout, stderr = self.execute_cmd(
                "busybox ps -o pid,ppid,stat,comm,args | grep -v 'grep -E ffmpeg|rest' | grep -E 'ffmpeg|rest' | tail")
            if ' Z  ' in stdout:
                self.log.warning('Zombie process found!')
            if ' 1 Z ' in stdout:
                stdout, stderr = self.execute_cmd(
                    "busybox ps -o pid,ppid,stat,comm,args | grep -v 'grep -E 1 Z    ffmpeg' | grep -E '1 Z    ffmpeg' | wc -l")
                self.log.error('init-child zombie process: {}'.format(stdout))
            self.log.info('<<<<<<<<<<<<<<<<<<<<<<<<< ffmpeg Monitor <<<<<<<<<<<<<<<<<<<<<<<<<')
        cmd = "busybox ps -ef | grep -v 'grep /usr/local/sbin/ffmpeg' | grep /usr/local/sbin/ffmpeg"
        if ignore_zombie:
            cmd += " | grep -v ' Z '"
        stdout, stderr = self.execute_cmd(cmd)
        self.log.warning("stdout: {}".format(stdout))
        return True if stdout else False

    def kill_first_found_FFmpeg(self, signal=13):
        self.log.info('Send singal -{} to the first found FFmpeg'.format(signal))
        self.execute_cmd(
            "busybox ps -ef | grep -v 'grep /usr/local/sbin/ffmpeg' | grep /usr/local/sbin/ffmpeg | busybox awk '{print $1}' | xargs kill -%s" % signal)

    def wait_all_FFmpeg_finish(self, delay=10, timeout=60, time_to_kill=None, ignore_zombie=False, check_func=None):
        start_time = time.time()
        if not check_func:
            check_func = self.is_any_FFmpeg_running
        while check_func(ignore_zombie=ignore_zombie):
            self.log.warning("Running!")
            now_time = time.time()
            if now_time >= start_time + timeout:
                return False
            if time_to_kill is not None and now_time >= start_time + time_to_kill:
                self.log.warning('Timeout wait {} sec, try to kill FFmpeg'.format(time_to_kill))
                self.kill_first_found_FFmpeg()
            self.log.info('Waiting {} sec for all FFmpeg to finish...'.format(delay))
            time.sleep(delay)
        return True

    def is_any_FFmpeg_running_kdp(self, ignore_zombie=False):
        cmd = "ps aux | grep 'ffmpeg' | grep -v 'grep'"
        if ignore_zombie:
            cmd += " | grep -v ' Z '"
        stdout, stderr = self.execute_cmd(cmd)
        return True if stdout else False

    def save_gza_device_logs(self, file_name, device_log_folder='/var/log', device_tmp_log='/mnt/HD/HD_a2/logs.tgz'):
        self.log.info('Compressing logs and save to {}...'.format(file_name))
        # Dump logs from cache.
        self.execute_cmd("logwdmsg -o")
        # clear existing compressed log.
        self.execute_cmd("[ -e {0} ] && rm {0}".format(device_tmp_log))
        # Compressing log folder to a file.
        self.execute_cmd("tar cvzfp {0} /var/log".format(device_tmp_log))
        if not self.sftp: self.sftp_connect()
        self.sftp_download(device_tmp_log, file_name)

    def save_kdp_device_logs(self, file_name, device_log_folder='/var/log', device_tmp_log='/data/logs.tgz'):
        self.log.info('Compressing logs and save to {}...'.format(file_name))
        # clear existing compressed log.
        self.execute_cmd("[ -e {0} ] && rm {0}".format(device_tmp_log))
        # Compressing log folder to a file.
        self.execute_cmd("tar cvzfp {0} /var/log/*".format(device_tmp_log))
        if not self.scp: self.scp_connect()
        self.scp_download(device_tmp_log, file_name)

    def clean_device_logs(self):
        self.log.info('Clean up logs...')
        # clear existing logs.
        # Empty existing other log file instead of deleting them.
        self.execute_cmd('find /var/log/ -name "*.log*" | xargs -I{} sh -c "echo > {}"')
        # delete backup log files.
        self.execute_cmd('find /var/log/ -name "*.log.*" | xargs -I{} sh -c "test {} && rm {}"')
        if self.check_is_kdp_device() or self.check_is_rnd_device():
            self.execute_cmd("rsyslog.sh reload")
        else:
            self.execute_cmd("rsyslog restart")

    """ Indexing libraries """

    @classmethod
    def get_intel_models(cls):
        return ['PR2100', 'PR4100', 'DL2100', 'DL4100']

    def is_intel_model(self):
        return self.get_model_name() in self.get_intel_models()

    def push_sqlite3_utils(self):
        # Upload small tools to home folder.
        if not self.sftp: self.sftp_connect()
        if self.is_intel_model():
            self.log.info('Push sqlite binary for INTEL chipset...')
            self.sftp_upload('./godzilla_scripts/tools/sqlite3_intel', 'sqlite3')
        else:
            self.log.info('Push sqlite binary for Marvel chipset...')
            self.sftp_upload('./godzilla_scripts/tools/sqlite3_arm', 'sqlite3')

        self.log.info('Push util script...')
        self.sftp_upload('./godzilla_scripts/tools/sqlite_godzilla.sh', 'sqlite_godzilla.sh')
        self.execute_cmd("chmod +x ~/sqlite*")

    def get_total_files_in_sqlite(self):
        number, stderr = self.execute_cmd(". ~/sqlite_godzilla.sh")
        return number

    def wait_for_sqlite_no_change(self, time_of_no_change=30, max_waiting_time=None):
        """
        Return total file number if there is no change in sqlite more than time_of_no_change secs,
        otherwise return None if specify a max_waiting_time secs or keep waiting.
        """
        start_time = start_time_of_no_change = time.time()
        last_total_files = self.get_total_files_in_sqlite()
        while (time.time() - start_time < max_waiting_time if max_waiting_time else True):
            total_files = self.get_total_files_in_sqlite()
            if total_files != last_total_files:
                start_time_of_no_change = time.time()
                last_total_files = total_files
            else:
                if time.time() - start_time_of_no_change >= time_of_no_change:
                    self.log.info(
                        'The number of files in sqlite db is not change after {} seconds.'.format(time_of_no_change))
                    return last_total_files
                time.sleep(5)
        return None

    def get_total_thumbnails(self):
        number, stderr = self.execute_cmd("find /mnt/HD/HD_a2/restsdk-data/data/files -type f ! -size 0 | wc -l")
        return number

    def get_restsdk_pid(self):
        pid, stderr = self.execute_cmd("ps | grep restsdk-serverd | grep -v grep | awk '{print $1}'")
        return pid

    @classmethod
    def log_time_format(cls):
        return '%Y-%m-%dT%H:%M:%S'

    def get_local_machine_time_in_log_format(self):
        time_str, stderr = self.execute_cmd(command='date +{}'.format(self.log_time_format()))
        return time_str

    @classmethod
    def parse_log_time_str(cls, time_str):
        return datetime.strptime(time_str, cls.log_time_format())

    def get_indexing_log(self, path, index_start_machine_time=None):
        stdout, stderr = self.execute_cmd("grep {} /var/log/* | grep -i '\"isfullscan\":true'".format(path))
        latest_log_time = None
        latest_log = None
        for log in [s for s in stdout.split('\n') if s]:
            try:
                timestamp = self.parse_log_time_str(time_str=log.split(':', 1)[1][:19])
            except:
                continue
            if not latest_log_time or timestamp > latest_log_time:
                latest_log_time = timestamp
                latest_log = log
        if index_start_machine_time:
            if isinstance(index_start_machine_time, str):
                index_start_machine_time = self.parse_log_time_str(time_str=index_start_machine_time)
            if latest_log_time is None or index_start_machine_time > latest_log_time:
                latest_log = None
        return latest_log

    def fetch_indexing_log(self, indexing_log_str):
        return {
            'duration': float(re.findall('"duration":\d*', indexing_log_str)[0].split(':')[1]) / 1000000,
            'totalIndexedFiles': int(re.findall('"totalIndexedFiles":\d*', indexing_log_str)[0].split(':')[1]),
            'totalSkipped': int(re.findall('"totalSkipped":\d*', indexing_log_str)[0].split(':')[1])
        }

    """ USB libraries """

    def push_format_utils(self, force=False):
        # Upload format binary to home folder.
        fileserver_url = self.get_fileserver_url()
        if self.is_intel_model():
            self.log.info('Push format binary for INTEL chipset...')
            if force or self.execute_cmd('test -e intel_x86_64 && echo y')[0] != 'y':
                self.execute_cmd(
                    'wget -r -nH --cut-dirs=3 --no-parent --reject="index.html*" http://{}/Tools/format_binary/GZA/intel_x86_64/ -P /home/root > /dev/null 2>&1'.format(
                        fileserver_url))
        else:
            self.log.info('Push format binary for Marvel chipset...')
            if force or self.execute_cmd('test -e arm && echo y')[0] != 'y':
                self.execute_cmd(
                    'wget -r -nH --cut-dirs=3 --no-parent --reject="index.html*" http://{}/Tools/format_binary/GZA/arm/ -P /home/root > /dev/null 2>&1'.format(
                        fileserver_url))
        self.execute_cmd("chmod +x */sbin/*")

    def push_data_set_to_usb(self, source_url, total_files=None, timeout=1200):
        cut_dirs = len([s for s in source_url.replace('//', '').split('/') if s]) - 1
        usb_path = self.get_usb_path()
        self.execute_cmd(
            'wget -r -nH --cut-dirs={0} --no-parent --reject="index.html*" {1} -P {2} > /dev/null 2>&1'.format(cut_dirs,
                                                                                                               source_url,
                                                                                                               usb_path))
        if not total_files:
            return
        # Wait and check total file for SMB command early return case.
        start_time = time.time()
        while timeout > time.time() - start_time:
            total, _ = self.execute_cmd("find {} -type f | wc -l".format(usb_path))
            if total and int(total) >= total_files:
                return
            time.sleep(20)
        self.log.warning('Waiting timeout, please check data is ready')

    def get_usb_path(self):
        path, stderr = self.execute_cmd("mount | grep USB | awk '{print $3}'")
        return path

    def get_usb_node(self):
        node, stderr = self.execute_cmd("mount | grep USB | awk '{print $1}'")
        return node

    def get_usb_format(self):
        usb_node = self.get_usb_node()
        if not usb_node: return
        usb_node = usb_node.split()
        usb_path = self.get_usb_path().split()
        usb_format_dict = dict()
        for index, usb in enumerate(usb_node):
            info, stderr = self.execute_cmd("blkid {}".format(usb))
            if 'vfat' in info:
                usb_format = "fat32"
            elif 'hfsplus' in info:
                usb_format = 'hfs+'
            elif 'ntfs' in info:
                usb_format = "ntfs"
            elif 'exfat' in info:
                usb_format = "exfat"
            else:
                usb_format = "unknown"
            usb_format_dict[usb_path[index]] = usb_format
        return usb_format_dict

    def format_usb(self, to_type, reattach_func=None):
        # Expect one USB driver attached.
        self.log.info('Start to format USB to {}'.format(to_type))
        if reattach_func:
            reattach_func()
        else:
            self.log.info('Reboot device to release USB drive...')
            self.reboot_and_wait_for_boot_completed()
        self.wait_for_usb_mount()
        self.log.info('Push format command utils...')
        self.push_format_utils()  # push here for utils may be deleted after reboot.
        self.log.info('Formating USB drive to {}...'.format(to_type))
        node = self.get_usb_node()
        self.execute_cmd("umount {}".format(node))

        if self.is_intel_model():
            if 'fat32' in to_type:
                cmd = "LD_LIBRARY_PATH=/home/root/intel_x86_64/lib /home/root/intel_x86_64/sbin/mkfs.fat {}".format(
                    node)
            elif 'hfs+' in to_type:
                cmd = "LD_LIBRARY_PATH=/home/root/intel_x86_64/lib /home/root/intel_x86_64/sbin/mkfs.hfs {}".format(
                    node)
            elif 'ntfs' in to_type:
                cmd = "LD_LIBRARY_PATH=/home/root/intel_x86_64/lib /home/root/intel_x86_64/sbin/mkntfs -qf {}".format(
                    node)
            elif 'exfat' in to_type:
                cmd = "/home/root/intel_x86_64/sbin/mkexfatfs {}".format(node)
        else:
            if 'fat32' in to_type:
                cmd = "/home/root/arm/sbin/mkfs.fat {}".format(node)
            elif 'hfs+' in to_type:
                cmd = "/home/root/arm/sbin/mkfs.hfs {}".format(node)
            elif 'ntfs' in to_type:
                cmd = "LD_LIBRARY_PATH=/home/root/arm/lib /home/root/arm/sbin/mkntfs -qf {}".format(node)
            elif 'exfat' in to_type:
                cmd = "/home/root/arm/sbin/mkexfatfs {}".format(node)

        self.execute_cmd(cmd)
        if reattach_func:
            reattach_func()
        else:
            # Reboot for mount USB.
            self.log.info('Reboot device for mount USB drive...')
            self.reboot_and_wait_for_boot_completed()
        self.wait_for_usb_mount()
        usbs = self.get_usb_format()
        if not usbs: raise RuntimeError('USB not found')
        if usbs.values()[0] != to_type: raise RuntimeError('Fail to format USB')

    def wait_for_usb_mount(self):
        for _ in xrange(30):
            if self.get_usb_node(): return True
            time.sleep(10)
        return False

    def get_usb_smb_name(self):
        name, stderr = self.execute_cmd("smbclient -L 127.0.0.1 --no-pass | grep 'USB Device Share' | awk '{print $1}'")
        return name

    def get_led_logs(self, log_filter=None, cmd=None):
        led_list = []
        stdout, stderr = self.execute_cmd(cmd)
        if stdout:
            led_logcat_lines = stdout.splitlines()
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

    def get_sys_slot_count(self):
        stdout, stderr = self.execute_cmd("getprop sys.slot.count")
        return stdout.strip()

    def get_sys_slot_drive(self, slot=None):
        if self.check_is_kdp_device():
            drive_code = 'hdd'
            slot_init = 0
        elif self.check_is_rnd_device():
            drive_code = 'drive'
            slot_init = 1
        else:
            drive_code = ''
            slot_init = 0
        drive_list = []
        if slot:
            stdout, stderr = self.execute_cmd('getprop sys.slot{}.{}'.format(slot, drive_code))
            drive_list.append(stdout.strip())
        else:
            sys_slot_count = self.get_sys_slot_count()
            slot = slot_init
            for i in xrange(int(sys_slot_count)):
                stdout, stderr = self.execute_cmd('getprop sys.slot{}.{}'.format(slot, drive_code))
                drive_list.append(stdout.strip())
                slot = slot + 1
        return drive_list

    def get_drive_state(self, drive):
        stdout, stderr = self.execute_cmd('hdparm -C /dev/{}'.format(drive))
        return stdout.strip()

    def set_drive_standby(self, drive, wait_until_standby=False, timeout=600):
        stdout, stderr = self.execute_cmd('hdparm -y /dev/{}'.format(drive))
        start_time = time.time()
        while wait_until_standby:
            if 'standby' in self.get_drive_state(drive):
                break
            else:
                if time.time() - start_time > timeout:
                    raise RuntimeError('Failed to set drive ({}) standby after {} seconds'.format(drive, timeout))
                    break
                time.sleep(30)
                stdout, stderr = self.execute_cmd('hdparm -y /dev/{}'.format(drive))

    """ serial use """
    def set_serial_client(self, serial_client):
        self.log.debug('Set serial_client: {}'.format(serial_client))
        self._serial_client = serial_client

    def has_serial_client(self):
        return hasattr(self, '_serial_client')
    """ serial use end """

    """ nasAdmin libraries """
    def get_nas_admin_token(self, username="admin", password="adminadmin", cookie="/tmp/cookie.txt"):
        self.log.debug("Gettiing the nasAdmin token")
        url = 'http://localhost/nas/v1/auth'
        data = {"username": username, "password": b64encode(password)}
        cmd = "curl -i -X POST {0} -H 'content-type: application/json' -d '{1}' -c {2}".format(url, json.dumps(data), cookie)
        response = self.execute_cmd(cmd, quiet=True)[0]
        if "200 OK" not in response or "expires" not in response:
            raise RuntimeError("Failed to get nasAdmin token!")
        nas_admin_token = self.execute_cmd('cat {} | tail -1'.format(cookie), quiet=True)[0].split()[-1]
        if nas_admin_token:
            self.log.debug("Get nasAdmin token successfully")
            return nas_admin_token
        else:
            raise RuntimeError('Failed to parser the nasAdmin token from cookie file!')

    def nas_admin_user_logout(self, cookie="/tmp/cookie.txt"):
        self.log.debug("Logging out the nasAdmin user")
        url = 'http://localhost/nas/v1/auth'
        cmd = 'curl -i -b {0} -X DELETE {1}'.format(cookie, url)
        response = self.execute_cmd(cmd, quiet=True)[0]
        if "200 OK" not in response:
            raise RuntimeError("Failed to logout the nasAdmin user!")
        else:
            self.log.debug("Logout the nasAdmin user successfully")

    def get_ota_update_status(self):
        nas_admin_token = self.get_nas_admin_token()
        url = 'http://localhost:8002/ota/v1/firmware'
        cmd = 'curl -i {0} -H "content-type: application/json" -H "Authorization: Bearer {1}"'.format(url, nas_admin_token)
        response = self.execute_cmd(cmd, quiet=True)[0]
        self.nas_admin_user_logout()
        if "200 OK" not in response:
            raise RuntimeError("Failed to get the OTA status!")
        else:
            self.log.debug("Get OTA status successfully!")
            ota_status = response.split()[-1]
            if "updateStatus" not in ota_status:
                raise RuntimeError("Failed to get the OTA status from the response!")
            else:
                ota_status = json.loads(ota_status)
                self.log.debug("OTA status: {}".format(ota_status))
            return ota_status

    def ota_change_auto_update(self, mode="enabled", schedule={"day": "monday", "hour": 22}):
        if mode == "scheduled" and schedule:
            if not schedule.get("day") or not schedule.get("hour"):
                raise RuntimeError('The schedule format need to be like {"day": "monday", "hour": 22}!')

        need_update = True
        result = self.get_ota_update_status()
        self.log.warning("Result before update: {}".format(result))
        # Scheduled need to be update every time or the device date change won't affect the OTA update time
        if result.get('updatePolicy').get('mode') == mode and mode != "scheduled":
            need_update = False

        if need_update:
            self.log.info("Changing the auto update mode to: {}".format(mode))
            nas_admin_token = self.get_nas_admin_token()
            url = 'http://localhost:8002/ota/v1/firmware'
            data = {"updatePolicy":{"mode":"{}".format(mode)}}
            if mode == "scheduled" and schedule:
                data["updatePolicy"]["schedule"] = schedule
            cmd = "curl -i -X PUT {0} -H 'content-type: application/json' -H 'Authorization: Bearer {1}' -d '{2}'".\
                format(url, nas_admin_token, json.dumps(data))
            response = self.execute_cmd(cmd, quiet=True)[0]
            self.nas_admin_user_logout()
            if "204 No Content" not in response:
                raise RuntimeError("Failed to change the auto update mode!")
            else:
                result = self.get_ota_update_status()
                self.log.warning("Result after update: {}".format(result))
                if result.get("updatePolicy").get('mode') == mode:
                    self.log.info("Change the auto update mode to '{}' successfully!".format(mode))
                else:
                    raise RuntimeError("Failed to change the auto update mode!")
        else:
            self.log.info("The auto update mode is already {}".format(mode))

    def ota_update_firmware_now(self):
        self.log.info("Trigger the OTA immediately")
        nas_admin_token = self.get_nas_admin_token()
        url = 'http://localhost:8002/ota/v1/firmware/update'
        cmd = "curl -i -X POST {0} -H 'content-type: application/json' -H 'Authorization: Bearer {1}'". \
            format(url, nas_admin_token)
        response = self.execute_cmd(cmd, quiet=True)[0]
        self.nas_admin_user_logout()
        if "204 No Content" not in response:
            raise RuntimeError("Failed to trigger the OTA!")
        else:
            self.log.info('Trigger the OTA successfully')

    def ota_check_only(self):
        self.log.info("Send the OTA check only call to update the cloud status")
        nas_admin_token = self.get_nas_admin_token()
        url = 'http://localhost:8002/ota/v1/firmware/check'
        cmd = "curl -i -X POST {0} -H 'content-type: application/json' -H 'Authorization: Bearer {1}'". \
            format(url, nas_admin_token)
        response = self.execute_cmd(cmd, quiet=True)[0]
        self.nas_admin_user_logout()
        if "204 No Content" not in response:
            raise RuntimeError("Failed to send the OTA check only call!")
        else:
            self.log.info('Send the OTA check only call successfully')

    def get_tls_info(self):
        url = 'http://localhost/nas/v1/locale'
        cmd = 'curl -i {0} -H "content-type: application/json"'.format(url)
        response = self.execute_cmd(cmd, quiet=True)[0]
        if "200 OK" not in response:
            self.log.error("Response: {}".format(response))
            raise RuntimeError("Failed to get the TLS info!")
        else:
            self.log.debug("Get TLS info successfully!")
            tls_info = response.split()[-1]
            if not tls_info:
                raise RuntimeError("Failed to get the TLS info from the response!")
            else:
                tls_url = json.loads(tls_info)
                return tls_url

    def get_tls_redirect_enabled_flag(self, cookie="/tmp/cookie.txt"):
        self.log.info("Get the TLS Redirect enabled flag")
        self.get_nas_admin_token(cookie=cookie)
        url = 'http://localhost/nas/v1/api/tlsRedirect'
        cmd = 'curl -b {0} -i {1} -H "content-type: application/json"'.format(cookie, url)
        response = self.execute_cmd(cmd, quiet=True)[0]
        self.log.warning(response)
        self.nas_admin_user_logout()
        if "200 OK" not in response:
            self.log.error("Response: {}".format(response))
            raise RuntimeError("Failed to get the TLS Redirect flag!")
        else:
            self.log.info("Get TLS flag successfully!")
            tls_info = response.split()[-1]
            return json.loads(tls_info)

    def set_tls_redirect_enabled_flag(self, enabled=True, cookie="/tmp/cookie.txt"):
        self.log.info("Set the TLS Redirect enabled flag to: {}".format(enabled))
        self.get_nas_admin_token(cookie=cookie)
        url = 'http://localhost/nas/v1/api/tlsRedirect'
        data = json.dumps({'enabled': enabled})
        cmd = "curl -X PUT -b {0} -i {1} -H 'content-type: application/json' -d '{2}'".format(cookie, url, data)
        response = self.execute_cmd(cmd, quiet=True)[0]
        self.nas_admin_user_logout()
        if "200 OK" not in response:
            self.log.error("Response: {}".format(response))
            raise RuntimeError("Failed to set the TLS Redirect enabled flag to: {}!".format(enabled))
        else:
            self.log.info("Set TLS Redirect enabled flag to: {} successfully!".format(enabled))

    def get_wan_filter_enabled_flag(self, cookie="/tmp/cookie.txt"):
        self.log.info("Get the WAN filter enabled flag")
        self.get_nas_admin_token(cookie=cookie)
        url = 'http://localhost/nas/v1/api/wanFilter'
        cmd = 'curl -b {0} -i {1} -H "content-type: application/json"'.format(cookie, url)
        response = self.execute_cmd(cmd, quiet=True)[0]
        self.log.warning(response)
        self.nas_admin_user_logout()
        if "200 OK" not in response:
            self.log.error("Response: {}".format(response))
            raise RuntimeError("Failed to get the WAN filter enabled flag!")
        else:
            self.log.info("Get WAN filter enabled flag successfully!")
            wan_info = response.split()[-1]
            return json.loads(wan_info)

    def set_wan_filter_enabled_flag(self, enabled=True, cookie="/tmp/cookie.txt"):
        self.log.info("Set the WAN filter enabled flag to: {}".format(enabled))
        self.get_nas_admin_token(cookie=cookie)
        url = 'http://localhost/nas/v1/api/wanFilter'
        data = json.dumps({'enabled': enabled})
        cmd = "curl -X PUT -b {0} -i {1} -H 'content-type: application/json' -d '{2}'".format(cookie, url, data)
        response = self.execute_cmd(cmd, quiet=True)[0]
        self.nas_admin_user_logout()
        if "200 OK" not in response:
            self.log.error("Response: {}".format(response))
            raise RuntimeError("Failed to set the WAN filter enabled flag to: {}!".format(enabled))
        else:
            self.log.info("Set WAN filter enabled flag to: {} successfully!".format(enabled))

    def get_device_info(self, fields=None):
        self.log.info("Get the device info with fields={}".format(fields))
        url = 'http://localhost:{}/sdk/v1/device'.format(self.get_restsdk_httpPort())
        if fields:
            url += "?fields={}".format(fields)
        cmd = 'curl -i {0} -H "content-type: application/json"'.format(url)

        max_retries = 3
        retry_delay = 60
        for retries in range(max_retries + 1):
            response = self.execute_cmd(cmd, quiet=True)[0]
            if "200 OK" in response:
                self.log.info("Get device info successfully!")
                break
            elif "503 Service Unavailable" in response and "migrating" in response:
                self.log.warning("DB migration is in progress")
            else:
                self.log.warning("Failed to get device info")

            if max_retries - retries != 0:
                self.log.warning("Retry after {} secs, {} retries remaining...".format(retry_delay, max_retries-retries))
                time.sleep(retry_delay)
        else:
            if "503 Service Unavailable" in response:
                if "migrating" in response:
                    self.log.warning("DB migration is still in progress after {} secs!".format(max_retries * retry_delay))
                else:
                    raise RuntimeError("Failed to get the device info! Error code: 503")
            else:
                self.log.error("Response: {}".format(response))
                raise RuntimeError("Failed to get the device info!")

        device_info = response.splitlines()[-1]
        return json.loads(device_info)

    def check_is_kdp_device(self):
        model_name = self.get_model_name()
        if model_name in ['monarch2', 'pelican2', 'yodaplus2']:
            return True
        else:
            return False

    def check_is_rnd_device(self):
        model_name = self.get_model_name()
        if model_name in ['rocket', 'drax']:
            return True
        else:
            return False

    def check_is_kdp_rnd_device(self):
        model_name = self.get_model_name()
        if model_name in ['rocket', 'drax', 'monarch2', 'pelican2', 'yodaplus2']:
            return True
        else:
            return False

    def set_device_info(self, data):
        self.log.info("Set the device info with data: {}".format(data))
        token = self.get_nas_admin_token()
        url = 'http://localhost:{}/sdk/v1/device'.format(self.get_restsdk_httpPort())
        cmd = "curl -X PUT -i {0} -H 'content-type: application/json' -H 'Authorization: Bearer {1}' -d '{2}'".\
            format(url, token, json.dumps(data))
        response = self.execute_cmd(cmd, quiet=False)[0]
        self.nas_admin_user_logout()
        if "200 OK" not in response and "204 No Content" not in response:
            self.log.error("Response: {}".format(response))
            raise RuntimeError("Failed to set the device info!")
        else:
            self.log.info("Set device info successfully!")

    def get_device_status(self, cookie="/tmp/cookie.txt"):
        self.log.info("Getting the device status by nasAdmin API")
        self.get_nas_admin_token(cookie=cookie)
        url = 'http://localhost/nas/v1/api/system/status'
        cmd = "curl -b {0} -i {1} -H 'content-type: application/json'".format(cookie, url)
        response = self.execute_cmd(cmd, quiet=False)[0]
        self.nas_admin_user_logout()
        if "200 OK" not in response:
            self.log.error("Response: {}".format(response))
            raise RuntimeError("Failed to get the device status by nasAdmin API!")
        else:
            self.log.info("Get the device status by nasAdmin API successfully!")
            device_status = response.split()[-1]
            return json.loads(device_status)

    def get_current_lang(self):
        current_lang = self.execute_cmd("ls -al /var/www/xml/lang.xml | awk '{ print $11 }'")[0].split('/')[-2]
        self.log.info('Current lang is {}'.format(current_lang))
        return current_lang

    def change_lang(self, lang):
        self.log.info('Change lang to {}...'.format(lang))
        self.execute_cmd("ln -fs {} /var/www/xml/lang.xml".format(self.gza_lang()[lang]), quiet=True)
        current_lang = self.get_current_lang()
        if current_lang != lang:
            return False
        return True

    def gza_lang(self, base='/usr/local/modules/language/'):
        return {
            'cs-CZ': base + 'cs-CZ/english_cs-cz.xml',
            'de-DE': base + 'de-DE/english_de-de.xml',
            'en-US': base + 'en-US/english_en-us.xml',
            'es-ES': base + 'es-ES/english_es-es.xml',
            'fr-FR': base + 'fr-FR/english_fr-fr.xml',
            'hu-HU': base + 'hu-HU/english_hu-hu.xml',
            'it_IT': base + 'it_IT/english_it-it.xml',
            'ja-JP': base + 'ja-JP/english_ja-jp.xml',
            'ko-KR': base + 'ko-KR/english_ko-kr.xml',
            'nl-NL': base + 'nl-NL/english_nl-nl.xml',
            'no-NO': base + 'no-NO/english_no-no.xml',
            'pl-PL': base + 'pl-PL/english_pl-pl.xml',
            'pt-BR': base + 'pt-BR/english_pt-br.xml',
            'ru-RU': base + 'ru-RU/english_ru-RU.xml',
            'sv-SE': base + 'sv-SE/english_sv-se.xml',
            'tr-TR': base + 'tr-TR/english_tr-tr.xml',
            'zh-CN': base + 'zh-CN/english_zh-cn.xml',
            'zh-TW': base + 'zh-TW/english_zh-tw.xml'
        }

    def add_alert_message(self, code):
        """ Ref to https://confluence.wdmv.wdc.com/pages/viewpage.action?spaceKey=QA&title=Godzilla+Alert+Email+notification+Test+Plan 
        """
        self.log.info('Add alert message, code: {}...'.format(code))
        exitcode, _ = self.execute("alert_test -a {} -f".format(code))
        if exitcode != 0:
            return False
        return True

    def clean_alert_messages(self):
        self.log.info('Clean up all alert messages...')
        exitcode, _ = self.execute("alert_test -R -f")
        if exitcode != 0:
            return False
        return True

    def delete_continuous_users(self, pre_name, start_idx=1, total=512):
        end_idx = start_idx + total - 1
        self.log.info('Delete user: {0}{1} to {0}{2}...'.format(pre_name, start_idx, end_idx))
        exitcode, _ = self.execute('for idx in $(seq {1} {2}); do cat /etc/passwd | grep {0}$idx && account -d -u {0}$idx; cat /var/www/xml/smb.xml | grep "<name>{0}$idx</name>" && smbif -b {0}$idx; done'.format(pre_name, start_idx, end_idx))
        if exitcode != 0:
            return False
        return True

    def check_continuous_users(self, pre_name, start_idx=1, total=512):
        end_idx = start_idx + total - 1
        self.log.info('Check user: {0}{1} to {0}{2}...'.format(pre_name, start_idx, end_idx))
        output, _ = self.execute_cmd('for idx in $(seq {1} {2}); do cat /etc/passwd | grep {0}$idx > /dev/null || echo {0}$idx; done'.format(pre_name, start_idx, end_idx), quiet=True)
        if output:
            self.log.error('User not found: ' + ' '.join(output.split('\n')))
        output, _ = self.execute_cmd('for idx in $(seq {1} {2}); do cat /var/www/xml/smb.xml | grep "<name>{0}$idx</name>" > /dev/null || echo {0}$idx; done'.format(pre_name, start_idx, end_idx), quiet=True)
        if output:
            self.log.error('Share not found: ' + ' '.join(output.split('\n')))
            return False
        return True

    def delete_continuous_groups(self, pre_name, start_idx=1, total=512):
        end_idx = start_idx + total - 1
        self.log.info('Delete group: {0}{1} to {0}{2}...'.format(pre_name, start_idx, end_idx))
        exitcode, _ = self.execute('for idx in $(seq {1} {2}); do cat /etc/group | grep {0}$idx && account -d -g {0}$idx; done'.format(pre_name, start_idx, end_idx))
        if exitcode != 0:
            return False
        return True

    """ nasAdmin libraries end """


if __name__ == '__main__':
    uut_path = '/Volumes/TimeMachineBackup'
    uut_ip = '{NAS_IP_ADDRESS}'
    server_ip = '{MAC_IP_ADDRESS}'
    name = 'root'
    password = '{ROOT_PASSWORD}'
    folder = '{BACKUP_FOLDER_IN_MAC}'
    mac_root = "Macintosh HD"
    protocol = '{afp or smb}'

    ssh = SSHClient(server_ip, name, password)
    ssh.connect()
    try:
        """
            Note: Sometimes the backup folder will be unmount after backup finished,
            we need to call latest backup once so it will be remounted.
        """
        result = ssh.tm_latest_backup()
        print result

        result = ssh.tm_get_dest()
        if result:
            dest_id = result.get('ID')
            ssh.tm_del_dest(dest_id)

        if ssh.check_folder_mounted(uut_path):
            print "already mounted before"
            ssh.unmount_folder(uut_path, force=True)

        if ssh.check_folder_exist(uut_path):
            print "folder already exist"
            ssh.delete_folder(uut_path)

        exclude_list = ['/Applications', '/Library', '/Users', '/System', '/private']
        for exclude_item in exclude_list:
            ssh.tm_add_exclusion(exclude_item)

        ssh.create_folder(uut_path)
        ssh.mount_folder(protocol, uut_ip, "TimeMachineBackup", uut_path)
        ssh.tm_set_dest(uut_path)

        result = ssh.tm_get_dest()
        dest_id = result.get('ID')
        ssh.tm_start_backup(dest_id)

        import time

        time.sleep(5)
        timer = 600
        while (timer >= 0):
            x = ssh.tm_backup_status()
            run_status = x.get('Running')
            if run_status is '0':
                print "Status: Complete"
                break
            else:
                backup_phase = x.get('BackupPhase')
                print "Status:", backup_phase

            time.sleep(5)
            timer -= 5

        result = ssh.tm_latest_backup()
        print result

    except Exception as e:
        print repr(e)

    ssh.close()
