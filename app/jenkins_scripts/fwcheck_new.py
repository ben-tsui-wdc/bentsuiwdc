# std modules
import sys


# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.restAPI import RestAPI


class FWCheck(TestCase):
    TEST_SUITE = 'jenkins_scripts'
    TEST_NAME = 'firmware verion check'

    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': True,
        'adb': True, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }
    
    def declare(self):
        self.firmware_version_given = None
        self.cloud_env_given = None
        self.cloud_variant_given = None
        self.fw_check_flag = True

    def init(self):
        self.env.disable_popcorn_report = True

    def test(self):
        # Turn off some irrelevant logs.
        self.env.disable_get_log_metrics = True
        self.env.dry_run = True
        self.env.disable_export_logcat_log = True
        self.env.disable_upload_logs = True
        self.env.disable_upload_logs_to_sumologic = True

        print "\r\n"
        print "## DUT firmware ##"
        print " {:<12}: {}".format("version", self.uut.get('firmware'))
        print " {:<12}: {}".format("environment", self.uut.get('environment'))
        print " {:<12}: {}".format("variant", self.uut.get('variant'))
        print "\r\n"
        print "## firmware given ##"
        print " {:<12}: {}".format("version", self.firmware_version_given)
        print " {:<12}: {}".format("environment", self.cloud_env_given)
        print " {:<12}: {}".format("variant", self.cloud_variant_given)
        print "\r\n"

        if not _compare(self.firmware_version_given, self.uut.get('firmware')):
            self.log.warning("DUT firmware[version] is different from given value.")
            self.fw_check_flag = False
        if not _compare(self.cloud_env_given, self.uut.get('environment')):
            self.log.warning("DUT firmware[environment] is different from given value.")
            self.fw_check_flag = False
        if not _compare(self.cloud_variant_given, self.uut.get('variant')):
            self.log.warning("DUT firmware[variant] is different from given value.")
            self.fw_check_flag = False

        _write_to_result(content='FW_CHECK={0}\n'.format(self.fw_check_flag), file_name=self.Jenkins_file)


class FWCheck_No_UUT_IP(TestCase):
    TEST_SUITE = 'jenkins_scripts'
    TEST_NAME = 'firmware verion check'

    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': True,
        'adb': False, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : False # Disbale restAPI.
    }

    def declare(self):
        self.firmware_version_given = None
        self.cloud_env_given = None
        self.cloud_variant_given = None
        self.fw_check_flag = True

    def init(self):
        self.env.disable_popcorn_report = True

    def before_test(self):
        self.uut['mac_address'] = self.mac_address


    def test(self):
        self.uut_owner = RestAPI(uut_ip=None, env=self.env.cloud_env, username=self.env.username, password=self.env.password, init_session=False, stream_log_level=self.env.stream_log_level)
        self.uut_owner.environment.update_service_urls()

        # Set socket timeout as 10 seconds
        self.uut_owner.set_global_timeout(timeout=30)
        # Set retry delay of http request: 1 second
        self.uut_owner.set_retry_delay(retry_delay=2)

        temp =  self.uut_owner.get_devices_info_per_specific_user()        
        if temp:
            for i in temp:
                if i.get("mac") == self.uut.get('mac_address').lower():
                    print i
                    self.uut['firmware'] = i.get('firmware').get('wiri')
                    self.uut['model'] = i.get('type')
                    self.uut['environment'] = self.env.cloud_env
                 
                    print "\n"
                    print 'firmware: {}'.format(self.uut['firmware'])
                    print 'model: {}'.format(self.uut['model'])
                    print 'mac_address: {}'.format(i.get("mac"))
                    print "\n"
                    break
        else:
            pass  # Need to do error handle

        print "\r\n"
        print "## DUT firmware ##"
        print " {:<12}: {}".format("version", self.uut.get('firmware'))
        print "\r\n"
        print "## firmware given ##"
        print " {:<12}: {}".format("version", self.firmware_version_given)
        print "\r\n"

        if not _compare(self.firmware_version_given, self.uut.get('firmware')):
            self.log.warning("DUT firmware[version] is different from given value.")
            self.fw_check_flag = False
        # Output the current actual firmware version on device
        _write_to_result(content='{}\n'.format(self.uut['firmware']), file_name=self.uut.get('mac_address').upper()+'_FW_VER')
        # Output the check result 
        _write_to_result(content='FW_CHECK={0}\n'.format(self.fw_check_flag), file_name=self.Jenkins_file)


def _compare(item_1, item_2):
    if item_1 == item_2:
        return True
    else:
        return False


def _write_to_result(content=None, file_name=None):
    try:
        with open('/root/app/output/{}'.format(file_name), 'w') as f:
            f.write(content)
    except:
        with open(file_name, 'w') as f:
            f.write(content)


if __name__ == "__main__":

    parser = InputArgumentParser("""\
        *** Firmware version check for Kamino ***
        Examples: ./run.sh jenkins_scripts/fwcheck.py --uut_ip 10.92.224.13 \
        --firmware_version 5.1.0-147 --cloud_env qa1 --cloud_variant user --debug_middleware --dry_run\
        """)
    parser.add_argument('-fw_given', '--firmware_version_given', help='The given firmware to check', default=None)
    parser.add_argument('-env_given', '--cloud_env_given', help='The given cloud environment to check', default=None)
    parser.add_argument('-var_given', '--cloud_variant_given', help='The given firmware variant to check', default=None)
    parser.add_argument('--Jenkins_file', help='The file which stores environment variables for Jenkins, by default is "result.txt"', default='result.txt')
    parser.add_argument('-no_uut_ip', '--no_uut_ip', help='check firmware_version without uut_ip', action='store_true')
    parser.add_argument('--mac_address', help='specify which device to be tested, mac_address is necessary if no_uut_ip is used.', default=None)
    args = parser.parse_args()


    if args.no_uut_ip:
        test = FWCheck_No_UUT_IP(parser)
    else:
        test = FWCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)

