
import shlex # to split shell commands
import subprocess32 as subprocess # subprocess module ported from python 3.2 with support for timeout exceptions
from subprocess32 import Popen, PIPE
import logging
import common_utils


class ShellCommands(object):

    def __init__(self, log_name=None, stream_log_level=None):
        self.log = common_utils.create_logger(overwrite=False, log_name=log_name, stream_log_level=stream_log_level)

    def executeCommand(self, cmd=None, consoleOutput=True, stdout=PIPE, stderr=PIPE, timeout=60, exitcode=False, shell=False):
        """
        Execute command and return stdout, stderr
        Handle timeout exception if limit exceeded and return None
        """
        if consoleOutput:
            self.log.info('Executing command: %s' %(cmd))
        if not shell: cmd = shlex.split(cmd)
        output = subprocess.Popen(cmd, stdout=stdout, stderr=stderr, shell=shell)
        try:
            stdout, stderr = output.communicate(timeout=timeout)
            if 'device offline' in stderr:
                self.log.error(stderr)
                raise Exception('Device offline!')
        except subprocess.TimeoutExpired as e:
            self.log.info('Timeout Exceeded: %i seconds' %(timeout))
            self.log.info('Killing command %s' %(cmd))
            output.kill()
            self.log.debug('Timeout exceeded: {0} seconds, killing command {1}'.format(timeout, cmd))
            raise e
        else:
            if consoleOutput:
                self.log.info('stdout: ' + stdout)
            if stderr:
                self.log.info('stderr: ' + stderr)
            if exitcode:
                return stdout, stderr, output.wait()
            return stdout, stderr

    def get_system_time(self, executor, args='+%s', raise_error=True):
        stdout, stderr = executor(cmd='date {}'.format(args))
        sec_str = stdout.strip()
        if not sec_str.isdigit():
            if raise_error:
                raise RuntimeError('Get system time failed')
            return None
        return int(sec_str)

    def get_machine_time(self, *args, **kwargs):
        return self.get_system_time(executor=self.executeShellCommand)

    def get_local_machine_time(self, sync_time=True, *args, **kwargs):
        if sync_time:
            self.log.info('Sync local machine time by ntpdate ...')
            self.executeCommand('ntpdate -s pool.ntp.org')
        return self.get_system_time(executor=self.executeCommand)

    def mount_samba(self, samba_user=None, samba_password=None, share_location=None, mount_point=None, vers=None):
        if samba_user == None:
            authentication = 'guest'
        else:
            if samba_password == None:
                password = ''
            authentication = 'username=' + samba_user + ',password=' + samba_password
        mount_cmd = 'mount.cifs'
        mount_args = (share_location +
                      ' ' +
                      mount_point +
                      ' -o ' +
                      authentication +
                      ',' +
                      'rw,nounix,file_mode=0777,dir_mode=0777')
        if vers: mount_args += ',vers=' + vers
        # Run the mount command
        self.log.info('Mounting {} '.format(share_location))
        stdout, stderr = self.executeCommand(mount_cmd + ' ' + mount_args)
        # check
        stdout, stderr = self.executeCommand('df')
        for item in stdout.splitlines():
            if share_location in item and mount_point in item:
                return True
        return False

    def umount_samba(self, mount_point=None):
        stdout, stderr = self.executeCommand('umount {}'.format(mount_point))
        if stderr: 
            if 'not mounted' in stderr:
                pass
            else:
                return False
        # check
        stdout, stderr = self.executeCommand('df')
        for item in stdout.splitlines():
            if mount_point in item:
                return False
        return True
