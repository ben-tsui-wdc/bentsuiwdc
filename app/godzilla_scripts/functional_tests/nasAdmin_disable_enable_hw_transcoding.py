# -*- coding: utf-8 -*-
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class NasAdminDisableEnableHWTranscoding(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'nasAdmin Disable and Enable HW Transcoding'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-8763'
    PRIORITY = 'Critical'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': True
    }

    def test(self):
        self.log.info("Disable the HW Transcoding flag and check the status")
        data = {"features": {"hwTranscoding": False}}
        self.ssh_client.set_device_info(data=data)
        result = self.ssh_client.get_device_info()
        if result.get("features").get("hwTranscoding"):
            raise self.err.TestFailure('Failed to change the HW Transcoding flag!')

        self.log.info("Enable the HW Transcoding flag and check the status")
        data = {"features": {"hwTranscoding": True}}
        self.ssh_client.set_device_info(data=data)
        result = self.ssh_client.get_device_info()
        if not result.get("features").get("hwTranscoding"):
            raise self.err.TestFailure('Failed to change the HW Transcoding flag!')


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/nasAdmin_disable_enable_hw_transcoding.py.py --uut_ip 10.136.137.159 -env qa1 \
        """)
    test = NasAdminDisableEnableHWTranscoding(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
