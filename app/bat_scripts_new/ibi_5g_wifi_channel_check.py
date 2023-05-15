# -*- coding: utf-8 -*-
""" Test cases to check ibi 5G Wifi channel plan should be follow HW value 0x67, it has disabled DFS channel: U-NII-2 & 2e channels. For Yoda plus only
    https://jira.wdmv.wdc.com/browse/KAM-31069
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys

# platform modules
from middleware.arguments import InputArgumentParser
from bat_scripts_new.reboot import Reboot


class ibi5GWiFiChannelCheck(Reboot):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'KAM-31069 - ibi Wi-Fi Channel Plan Confirmation'
    # Popcorn
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'KAM-31069'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    def test(self):

        model = self.uut.get('model')
        if model == 'monarch' or model == 'pelican':
            raise self.err.TestSkipped('Model is {}, skipped the test !!'.format(model))
        rtwpriv = self.adb.executeShellCommand('rtwpriv wlan0 efuse_get rmap,b8,1')[0]
        fw_ver = self.adb.getFirmwareVersion()
        if '7.3.1' in fw_ver: # For 4.3.1 factory drop release only
            if 'wlan0    efuse_get:0x76' not in rtwpriv:
                self.adb.executeShellCommand('rtwpriv wlan0 efuse_set wmap,b8,76 && rtwpriv wlan0 efuse_get rmap,b8,1')
                try:
                    self.no_rest_api = True
                    super(ibi5GWiFiChannelCheck, self).test()
                except Exception as ex:
                    raise self.err.TestSkipped('Reboot failed ! Skipped the ibi Wi-Fi Channel Plan Confirmation check ! Error message: {}'.format(repr(ex)))
        else:
            if 'wlan0    efuse_get:0x67' not in rtwpriv and 'wlan0    efuse_get:0x43' not in rtwpriv: # Need to remove 0x43 after 4.9.0 release, IBIX-5174
                self.adb.executeShellCommand('rtwpriv wlan0 efuse_set wmap,b8,67 && rtwpriv wlan0 efuse_get rmap,b8,1')
                try:
                    self.no_rest_api = True
                    super(ibi5GWiFiChannelCheck, self).test()
                except Exception as ex:
                    raise self.err.TestSkipped('Reboot failed ! Skipped the ibi Wi-Fi Channel Plan Confirmation check ! Error message: {}'.format(repr(ex)))
        # Check Channel Plan
        channel_plan = self.adb.executeShellCommand('cat /proc/net/rtl88x2be/wlan0/chan_plan')[0]
        if '7.3.1' in fw_ver:
            if '0x76' not in channel_plan:
                raise self.err.TestFailure('Channel plan is not 0x76, test failed !!!')
        else:
            if '0x43' not in channel_plan and '0x67' not in channel_plan: # Need to remove 0x43 after 4.9.0 release, IBIX-5174
                raise self.err.TestFailure('Channel plan is not 0x43 or 0x67, test failed !!!')
            else:
                self.adb.executeShellCommand('svc wifi enable')
                self.adb.executeShellCommand('wpa_cli -i wlan0 -p /data/misc/wifi/sockets scan')
                ap_list = self.adb.executeShellCommand("wpa_cli -i wlan0 -p /data/misc/wifi/sockets scan_results | busybox awk '{print $2}'")[0]
                u_nii_not_dfs_channel_plan_freq_lists = [5180, 5200, 5220, 5240, 5745, 5765, 5785, 5805, 5825]
                u_nii_dfs_channel_plan_freq_lists = [5260, 5280, 5300, 5320 ,5500, 5520, 5540, 5560, 5580, 5600, 5620, 5640, 5660, 5680, 5700]
                u_nni_2_4G_1_11_channel_plan_freq_lists = [2412, 2417, 2422, 2427, 2432, 2437, 2442, 2447, 2452, 2457, 2462]
                if '0x43' in channel_plan:
                    self.log.info('Channel plan is 0x43')
                    for item in u_nii_dfs_channel_plan_freq_lists:
                        if str(item) in ap_list:
                            raise self.err.TestFailure('DFS Frequency {} is in the AP channel scan list, test failed!!'.format(item))
                elif '0x67' in channel_plan:
                    self.log.info('Channel plan is 0x67')
                    channel_67_list = u_nii_not_dfs_channel_plan_freq_lists + u_nii_dfs_channel_plan_freq_lists + u_nni_2_4G_1_11_channel_plan_freq_lists
                    for i in range(2400, 6000):
                        if str(i) in ap_list and i not in channel_67_list:
                            raise self.err.TestFailure('Frequency {} is in the AP channel scan list, test failed!!'.format(i))
                else:
                    self.log.warning('Channel plan is {}, skip freq check ...'.format(channel_plan))

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** 5G Wi-Fi Channel Check Script ***
        Examples: ./run.sh bat_scripts_new/ibi_5g_wifi_channel_check.py --uut_ip 10.92.224.68\
        """)

    test = ibi5GWiFiChannelCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
