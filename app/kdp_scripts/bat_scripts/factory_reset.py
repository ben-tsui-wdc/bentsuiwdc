# -*- coding: utf-8 -*-
""" Test cases to test fatory reset function.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"
__author2__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import time
from itertools import count
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP
from platform_libraries.constants import RnD
from platform_libraries.restAPI import RestAPI
from kdp_scripts.bat_scripts.check_nasadmin_daemon import CheckNasAdminDaemon
from kdp_scripts.bat_scripts.samba_service_check import SambaServiceCheck
from kdp_scripts.bat_scripts.samba_rw_check import SambaRW


class FactoryReset(KDPTestCase):

    TEST_SUITE = 'KDP_Platform_BAT'
    TEST_NAME = 'KDP-195 - Factory Reset Test'
    # Popcorn
    TEST_JIRA_ID = 'KDP-195,KDP-214,KDP-1937,KDP-3292,KDP-5510,KDP-882,KDP-892'
    REPORT_NAME = 'Single_run'

    SETTINGS = {
        'uut_owner': False,
        'serial_client': True
    }

    def declare(self):
        self.run_rest_api = False
        self.keep_run = False
        self.attach_owner = False
        self.samba_io = False

    def init(self):
        self.timeout = 60*20
        self.model = self.uut.get('model')
        self.is_rnd_device = self.ssh_client.check_is_rnd_device()

    def test(self):
        # This is to prevent sometimes device become pingable before running factory reset
        if self.ssh_client.check_file_in_device('/tmp/system_ready'):
            self.log.info('Remove the /tmp/system_ready before running factory reset')
            self.ssh_client.execute_cmd('rm /tmp/system_ready')

        if self.run_rest_api:
            self.log.info('Use REST API to do factory restore')
            if self.env.uut_restsdk_port:
                uut_ip = "{}:{}".format(self.env.uut_ip, self.env.uut_restsdk_port)
            else:
                uut_ip = self.env.uut_ip
            self.uut_owner = RestAPI(uut_ip=uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
            self.uut_owner.id = 0  # Reset uut_owner.id
            self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
            try:
                # It seems that sync between cloud and restsdk has time gap.
                # So we have to wait for some time then make REST API call after user is attached to device.
                time.sleep(30)
                self.uut_owner.factory_reset()
                self.log.info('Do factory restore....')
            except Exception as ex:
                if self.keep_run:
                    self.log.warning('Send restapi request failed!! Use SSH command to do factory reset, Ex: {}'.format(ex))
                    self.ssh_client.execute_background('reset_button.sh factory')
                else:
                    raise self.err.TestFailure('Execute restapi request for factory reset failed !!!')
        else:
            self.log.info('Use SSH command to do factory restore')
            if self.is_rnd_device:
                self.ssh_client.execute_background('system_event.sh eraseAllData')
            else:
                self.ssh_client.execute_background('reset_button.sh factory')

        self.log.info('Expect device reboot completed in {} seconds.'.format(self.timeout*2))
        start_time = time.time()
        if not self.ssh_client.wait_for_device_to_shutdown(timeout=self.timeout):
            raise self.err.TestFailure('Device was not shut down successfully!')
        if self.serial_client:
            self.serial_client.wait_for_boot_complete_kdp(timeout=self.timeout)
            if not self.env.enable_auto_ota:
                self.log.info('enable_auto_ota is set to false, lock otaclient service')
                self.serial_client.lock_otaclient_service_kdp()
            if self.env.ap_ssid:
                ap_ssid = self.env.ap_ssid
                ap_password = self.env.ap_password
                self.serial_client.retry_for_connect_WiFi_kdp(ssid=ap_ssid, password=ap_password)
            self.env.check_ip_change_by_console()
        if not self.ssh_client.wait_for_device_boot_completed(timeout=self.timeout):
            raise self.err.TestFailure('Device was not boot up successfully!')
        self.log.warning("Reboot complete in {} seconds".format(time.time() - start_time))
        if not self.env.enable_auto_ota:
            self.log.info('enable_auto_ota is set to false, lock otaclient service')
            self.ssh_client.lock_otaclient_service_kdp()

        self.check_disk_space()
        self.ssh_client.check_restsdk_service()
        if self.env.is_nasadmin_supported():
            env_dict = self.env.dump_to_dict()
            check_nasadmin_daemon = CheckNasAdminDaemon(env_dict)
            check_nasadmin_daemon.main()
            if self.uut['model'] == 'yodaplus2':
                check_samba_daemon = SambaServiceCheck(env_dict)
                check_samba_daemon.main()
                if self.samba_io:
                    check_samba_rw = SambaRW(env_dict)
                    check_samba_rw.main()

        if self.uut['model'] in ['monarch2', 'pelican2']:
            env_dict = self.env.dump_to_dict()
            check_samba_daemon = SambaServiceCheck(env_dict)
            check_samba_daemon.main()
            if self.samba_io:
                check_samba_rw = SambaRW(env_dict)
                check_samba_rw.main()

        self.check_user_root_folder()
        RestAPI._ids = count(0)  # Reset the ids count so that the id in the other RestAPI object will be reset to 0
        self.check_wd_config()  # David's request
        self.check_appmgr_service()
        self.check_md_raid()
        self.check_device_vol_mount_opt()
        self.check_crash_report()

    def after_test(self):
        if self.attach_owner:
            if self.env.uut_restsdk_port:
                uut_ip = "{}:{}".format(self.env.uut_ip, self.env.uut_restsdk_port)
            else:
                uut_ip = self.env.uut_ip
            self.uut_owner = RestAPI(uut_ip=uut_ip, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
            self.uut_owner.id = 0  # Reset uut_owner.id
            self.uut_owner.init_session(client_settings={'config_url': self.uut['config_url']})
            self.log.warning('Attach owner after factory_reset.')

    def check_wd_config(self):
        if self.is_rnd_device:
            bootConfig_path = "/sys_configs/bootConfig"
        else:
            bootConfig_path = "/wd_config/bootConfig"
        stdout, stderr = self.ssh_client.execute_cmd('[ -e {} ] && echo  "Found" || echo "Not Found"'.format(bootConfig_path))
        if stdout.strip() == "Found":
            pass
        else:
            raise self.err.TestFailure('{} doesn\'t exist'.format(bootConfig_path))

    def check_user_root_folder(self):
        if self.is_rnd_device:
            user_roots_path = RnD.USER_ROOT_PATH
        else:
            user_roots_path = KDP.USER_ROOT_PATH
        stdout, stderr = self.ssh_client.execute_cmd('ls {} | grep auth'.format(user_roots_path))
        if stdout:
            raise self.err.TestFailure('Wipe user root failed')
        self.log.info('Wipe user root completed.')

    def check_disk_space(self):
        # check userRoots is mounted
        self.timing.reset_start_time()
        while not self.timing.is_timeout(60*5):
            if self.is_rnd_device:
                grep_root_volume_size = 'df | grep /Volume1 | grep -v docker'
            else:
                grep_root_volume_size = 'df | grep /data/wd/diskVolume0'
            userRootsdf = self.ssh_client.execute_cmd(grep_root_volume_size)[0]
            if userRootsdf:
                break
            time.sleep(2)
            if self.timing.is_timeout(60*5):
                raise self.err.TestFailure('userRoots is not mounted!!!')
        freesize = float(filter(lambda ch: ch in '0123456789.', userRootsdf.split()[3]))
        self.log.info('Free space: {}'.format(freesize))
        usesize = float(filter(lambda ch: ch in '0123456789.', userRootsdf.split()[2]))
        self.log.info('Use space: {}'.format(usesize))
        totalsize = float(filter(lambda ch: ch in '0123456789.', userRootsdf.split()[1]))
        self.log.info('Total space: {}'.format(totalsize))
        if usesize > totalsize*0.022:
            raise self.err.TestFailure('Disk used space is more than {}!!'.format(totalsize*0.022))
        elif freesize < totalsize*0.97:
            raise self.err.TestFailure('Free space is less than {}!!'.format(totalsize*0.097))
        else:
            self.log.info('Disk Space check passed !!')

    def check_appmgr_service(self):
        exitcode, _ = self.ssh_client.execute('pidof kdpappmgr')
        if exitcode != 0: raise self.err.TestFailure("kdpappmgr process not found")
        exitcode, _ = self.ssh_client.execute('pidof kdpappmgrd')
        if exitcode != 0: raise self.err.TestFailure("kdpappmgrd process not found")

    def check_md_raid(self):
        if self.uut['model'] in ['pelican2', 'drax']:
            stdout, stderr = self.ssh_client.execute_cmd('mdadm --detail /dev/md1')
            if 'State : clean, degraded' in stdout or 'State : active, degraded' in stdout:
                raise self.err.TestFailure('The md raid is degraded.')
            if 'Active Devices : 2' not in stdout or 'Working Devices : 2' not in stdout:
                raise self.err.TestFailure('The "Active/Working Devices" is not 2.')
            self.timing.reset_start_time()
            while not self.timing.is_timeout(300): # Wait for getprop wd.volume.state
                stdout, stderr = self.ssh_client.execute_cmd('getprop wd.volume.state')
                if stdout.strip() != 'clean': 
                    self.log.warning('"getprop wd.volume.state" is not clean, wait for 30 secs and try again...')
                    time.sleep(30)
                else:
                    break
            else:
                raise self.err.TestFailure('"getprop wd.volume.state" is not clean.')

    def check_device_vol_mount_opt(self):  # KDP-5449 [a few devices fail to set resgid to volume]
        device_vol_path = self.ssh_client.getprop(name='device.feature.vol.path')
        stdout, stderr = self.ssh_client.execute_cmd('mount | grep {} | grep -v docker'.format(device_vol_path))
        if 'resgid=990' not in stdout:
            raise self.err.TestFailure('"resgid=990" is not set successfully on mount option of device volume path({}).'.format(device_vol_path))

    def check_crash_report(self):
        self.log.info('Check analyticpublic log to see has crash report or not ...')
        crash_report = self.ssh_client.execute_cmd('grep -E crash_report /var/log/analyticpublic.log')[0]
        if crash_report:
            raise self.err.TestFailure("got crash_report: {}, test failed !!!".format(crash_report))

if __name__ == '__main__':
    parser = KDPInputArgumentParser("""\
        *** Factory Reset Test Script ***
        Examples: ./run.sh kdp_scripts/bat_scripts/factory_reset.py --uut_ip 10.92.224.68\
        """)

    parser.add_argument('-runapi', '--run_rest_api', help='Use restapi to reboot device', action='store_true')
    parser.add_argument('-keeprun', '--keep_run', help='keep run fatory reset if use restAPI call failed', action='store_true')
    parser.add_argument('-atta_owner', '--attach_owner', help='attach owner after factory_reset', action='store_true')
    parser.add_argument('-samba_io', '--samba_io', help='run Sambe R/W testing after factory reset', action='store_true')

    test = FactoryReset(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
