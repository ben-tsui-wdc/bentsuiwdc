# -*- coding: utf-8 -*-

__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

# std modules
import os
import sys
import time
# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase

from bat_scripts_new.factory_reset import FactoryReset
from bat_scripts_new.reboot import Reboot

from platform_libraries.restAPI import RestAPI
from platform_libraries.ssh_client import SSHClient


class ServiceCheck(TestCase):
    TEST_SUITE = 'Functional_Tests'
    TEST_NAME = 'service_check'
    # Popcorn
    TEST_JIRA_ID = 'KAM-21810'
    SETTINGS = {'uut_owner':False}

    def declare(self):
        self.timeout = 300


    def init(self):
        self.samba_user = None
        self.samba_password = None
        self.sharelocation = '//{}/Public'.format(self.env.uut_ip)
        self.mountpoint = '/mnt/cifs'


    def test(self):
        if self.test_protocol == 'afp':
            self.afp_check()
        elif self.test_protocol == 'smb':
            self.smb_check()
        elif self.test_protocol == 'smb_after_factory_reset':
            self.smb_after_factory_reset()


    # # KAM-24656:   Check Samba daemon is active after factory reset
    def smb_after_factory_reset(self):
        # factory_reset device and check if smbd is launched
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=True']
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = False
        factory_reset.test()
        self.adb.stop_otaclient()

        # Onboarding device
        self.uut_owner = RestAPI(uut_ip=self.env.uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False)
        if self.env.cloud_env == 'prod':
            self.log.warning('Env is {}, skipped the wait cloud connected check ...'.format(self.env.cloud_env))
            with_cloud_connected = False
        else:
            with_cloud_connected = True
        self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']}, with_cloud_connected=with_cloud_connected)
        
        # Check samba
        self.smb_check()

        # reboot device and check if smbd is launched
        env_dict = self.env.dump_to_dict()
        env_dict['Settings'] = ['uut_owner=True']
        reboot_object = Reboot(env_dict)
        reboot_object.no_rest_api = False
        reboot_object.test()
        self.adb.stop_otaclient()
        self.smb_check()


    def afp_check(self):
        # check afpd
        stdout, stderr = self.adb.executeShellCommand('ps | grep afpd')
        if not stdout and self.uut.get('model') == 'yoda':
            pass
        elif stdout and self.uut.get('model') != 'yoda':
            pass
        else:
            raise self.err.TestFailure('afpd issue occurred on {}.\n{}'.format(self.uut.get('model'), stdout))
        # check if afp can be mounted.
        dst_folder = '/Volumes/functional_test_{}_{}'.format(self.uut.get('model'), int(time.time()))
        mac_ssh = SSHClient(self.mac_server_ip, self.mac_username, self.mac_password)
        mac_ssh.connect()
        mac_ssh.unmount_folder(dst_folder, force=True)
        mac_ssh.create_folder(dst_folder)
        mac_ssh.mount_folder(self.test_protocol, self.env.uut_ip, 'TimeMachineBackup', dst_folder)
        if mac_ssh.check_folder_mounted('{}/TimeMachineBackup'.format(self.env.uut_ip), dst_folder=dst_folder, protocol=self.test_protocol):
            if self.uut.get('model') == 'yoda':
                raise self.err.TestFailure('{} mount successed on {}'.format(self.test_protocol, self.uut.get('model')))
            elif self.uut.get('model') != 'yoda':
                pass 
        else:
            if self.uut.get('model') == 'yoda':
                pass
            elif self.uut.get('model') != 'yoda':
                raise self.err.TestFailure('{} mount failed on {}'.format(self.test_protocol, self.uut.get('model')))
        mac_ssh.unmount_folder(dst_folder, force=True)
        mac_ssh.delete_folder(dst_folder)
        mac_ssh.close()


    def delete_folder(self, folder_path):
        self.log.info("Deleting folder: {}".format(folder_path))
        self.execute('rm -r {}'.format(folder_path))


    def smb_check(self, upload_file=True):
        # check smbd
        start_time = time.time()
        while True:
            try:
                stdout, stderr = self.adb.executeShellCommand('ps | grep smbd')
                if not stdout and self.uut.get('model') == 'yoda':
                    break
                elif stdout and self.uut.get('model') != 'yoda':
                    break
                else:
                    raise self.err.TestFailure('smbd issue occurred on {}.\n{}'.format(self.uut.get('model'), stdout))
            except self.err.TestFailure as e:
                if time.time() - start_time > 300:  # Wait 300 seconds
                    raise
                time.sleep(5)
                print 'retry "ps | grep smbd" after {} seconds'.format(int(time.time() - start_time))

        # mkdir on local
        if not os.path.isdir(self.mountpoint):
            os.mkdir(self.mountpoint)
        # check if samba can be mounted. 
        if self.mount_samba():
            if self.uut.get('model') == 'yoda':
                raise self.err.TestFailure('samba mount successed on {}'.format(self.uut.get('model')))
            elif self.uut.get('model') != 'yoda':
                pass 
        else:
            if self.uut.get('model') == 'yoda':
                pass
            elif self.uut.get('model') != 'yoda':
                raise self.err.TestFailure('samba mount failed on {}'.format(self.uut.get('model')))
        # upload_file
        if upload_file:
            testfile = 'testfile_{}'.format(time.time())
            stdout, stderr = self.adb.executeCommand('dd if=/dev/urandom of=./{} bs=1024k count=20'.format(testfile), timeout=180)
            stdout, stderr = self.adb.executeCommand('ls ./{}'.format(testfile))
            if 'No such file or directory' in stdout:
                raise self.err.TestError('Failed to dd file in testing client.')
            stdout, stderr = self.adb.executeCommand('cp {} {}'.format(testfile, self.mountpoint))
            stdout, stderr = self.adb.executeShellCommand('ls /data/wd/diskVolume0/samba/share/{}'.format(testfile))
            if 'No such file or directory' in stdout:
                raise self.err.TestFailure('Failed to copy testfile to DUT by samba!')
        # unmount samba
        self.umount_samba()


    def mount_samba(self):
        max_retry = 10
        while True:
            if self.samba_user is None:
                authentication = 'guest'
            else:
                if self.samba_password is None:
                    password = ''
                authentication = 'username=' + user + ',password=' + password
            mount_cmd = 'mount.cifs'
            mount_args = (self.sharelocation +
                          ' ' +
                          self.mountpoint +
                          ' -o ' +
                          authentication +
                          ',' +
                          'rw,nounix,file_mode=0777,dir_mode=0777')
            # Run the mount command
            self.log.info('Mounting {} '.format(self.sharelocation))
            self.adb.executeCommand(mount_cmd + ' ' + mount_args)
            stdout, stderr = self.adb.executeCommand('df')
            if self.sharelocation in stdout and self.mountpoint in stdout:
                return True
            else:
                max_retry -= 1
                if max_retry == 0: 
                    return False
                time.sleep(5)

    def umount_samba(self):
        self.adb.executeCommand('umount {}'.format(self.mountpoint))


if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** raid type conversion test on Kamino Android ***
        Examples: ./run.sh functional_tests/service_check.py --uut_ip 10.92.224.61 --cloud_env qa1 --dry_run --debug_middleware\
         --disable_clean_logcat_log  --led_test_case  softap_mode """)
    ''' 
    led_test_case includes
        softap_mode
        ready_to_onboard
    '''
    parser.add_argument('--test_protocol', help='For differenct protocol that will be checked', choices=['afp', 'smb', 'smb_after_factory_reset'], default=None)
    parser.add_argument('--mac_server_ip', help='mac_server_ip which is used to be as client.' , default='10.92.224.28')
    parser.add_argument('--mac_username', help='mac_username which is used to login to mac client', default='root')
    parser.add_argument('--mac_password', help='mac_password which is used to login to mac clientt', default='`1q')

    test = ServiceCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)