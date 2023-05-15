import argparse
import os
import sys
import time

from platform_libraries import common_utils
from platform_libraries.adblib import ADB


class fwcheck(object):
    def __init__(self, uut_ip=None, port=None, adbserver=None):
        self.log = common_utils.create_logger(overwrite=False)
        if adbserver:
            self.adb = ADB(adbServer='10.10.10.10', adbServerPort='5037', uut_ip=uut_ip, port=port)
        else:
            self.adb = ADB(uut_ip=uut_ip, port=port)

        i = 0
        while True:
            i += 1
            print "############# {0}".format(i)
            try:
                self.adb.connect()
                self.fw_device = self.adb.getFirmwareVersion()
                self.env_device = self.adb.executeShellCommand('cat /system/etc/restsdk-server.toml | grep "configURL"')[0].strip()
                self.variant_device = self.adb.executeShellCommand('getprop | grep build | grep type')[0].strip()
                break
            except Exception as ex:
                self.log.error('Failed to connect with NAS to get firmwareVersion!! Err: {0}'.format(ex))
                self.adb.disconnect()

            if i == 3:
                print 'Failed to connect with NAS to get firmwareVersion after retrying {0} times by every 60 seconds!!'.format(i)
                sys.exit(1)
            else:
                time.sleep(60)

    def compare(self, fw_given=None):     
        if self._compare_fw(fw_given=fw_given) and \
            self._compare_env(env_given=env_given, fw_given=fw_given) and \
            self._compare_variant(variant_given=variant_given):
            return True
        else:
            return False

    def _compare_fw(self, fw_given=None):
        if fw_given == self.fw_device:
            self.log.info('DUT firmware[version] is the same as given value.')
            return True
        else:
            self.log.warning('DUT firmware[version] is different from given value.')
            return False

    def _compare_env(self, env_given=None, fw_given=None):
        if env_given == 'dev1':
            check = 'dev1'
        elif env_given == 'qa1':
            check = 'qa1'
        else:
            check = 'https://config.mycloud.com'
        if check in self.env_device:
            self.log.info('DUT firmware[cloud environment] is the same as given value.')
            return True
        else:
            self.log.warning('DUT firmware[cloud environment] is different from given value.')
            return False

    def _compare_variant(self, variant_given=None):
        if variant_given == 'user':
            check = '[ro.build.type]: [user]'
        elif variant_given == 'userdebug':
            check = '[ro.build.type]: [userdebug]'
        elif variant_given == 'engr' or variant_given == 'eng':
            check = '[ro.build.type]: [eng]'
        if check == self.variant_device:
            self.log.info('DUT firmware[variant] is the same as given value.')
            return True
        else:
            self.log.warning('DUT firmware[variant] is different from given value.')
            return False

    def write_to_result(self, result=None, Jenkins_file=None):
        try:
            with open('/root/app/output/{}'.format(Jenkins_file), 'w') as f:
                f.write('FW_CHECK={0}\n'.format(result))
        except:
            with open(Jenkins_file, 'w') as f:
                f.write('FW_CHECK={0}\n'.format(result))



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='If the given fw version is the same as the device fw version, return "True", otherwise return "False".\n')
    parser.add_argument('--uut_ip', help='Test device IP address')
    parser.add_argument('--port', help='Destination port number', default='5555')
    parser.add_argument('--fw', help='the given fw version, ex. 4.0.0-249')
    parser.add_argument('--env', help='the given env, ex. dev1', default='dev1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('--variant', help='the given variant, ex. userdebug', default='userdebug', choices=['user', 'userdebug', 'engr', 'eng'])
    parser.add_argument('--Jenkins_file', help='The file which stores environment variables for Jenkins, by default is "result.txt"', default='result.txt')
    parser.add_argument('--adbserver', help='Use public adbserver if using "--adbserver"', action='store_true')
    args = parser.parse_args()

    if not args.uut_ip:
        print "\nPlease enter the test device IP address!\n"
        sys.exit(1)
    
    # Assign arguments to variables.
    uut_ip = args.uut_ip
    port = args.port
    fw_given = args.fw
    env_given = args.env
    variant_given = args.variant
    Jenkins_file = args.Jenkins_file
    adbserver = args.adbserver
    
    # Create an object.
    fwcheck_object = fwcheck(uut_ip=uut_ip, port=port, adbserver=adbserver)
    
    # Actions.
    result = fwcheck_object.compare(fw_given=fw_given)
    fwcheck_object.write_to_result(result=result, Jenkins_file=Jenkins_file)