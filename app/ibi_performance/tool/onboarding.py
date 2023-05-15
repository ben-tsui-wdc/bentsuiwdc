import sys
#import time

#from platform_libraries import common_utils
#from platform_libraries.constants import GlobalConfigService as GCS

from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase



class OnBoarding(TestCase):
    TEST_SUITE = 'onboarding'
    TEST_NAME = 'onboarding'

    SETTINGS = { # Disable all utilities.
        'disable_firmware_consistency': True,
        'adb': False, # Disbale ADB and ignore any relevant input argument.
        'power_switch': False, # Disbale Power Switch.
        'uut_owner' : True # Disbale restAPI.
    }
    
    def declare(self):
        pass


    def test(self):
        pass


if __name__ == "__main__":

    parser = InputArgumentParser("""\
        *** Only for OnBoarding ***
        Examples: ./run.sh jenkins_scripts/onboarding.py  \
         --cloud_env qa1 --serial_server_ip 10.195.249.123 --serial_server_port 20001  \
         --ap_ssid MV-Warrior --ap_password gQJ2bQJt3MKSfH77sSNJ --disable_serial_server_daemon_msg\
        """)


    test = OnBoarding(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)