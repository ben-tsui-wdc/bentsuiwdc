# -*- coding: utf-8 -*-
""" Test cases to check device should register to ota cloud to the default yodaplus bucket.
"""
__author__ = "Vance Lo <vance.lo@wdc.com>"

# std modules
import sys
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase


class DefaultOTABucketCheck(TestCase):

    TEST_SUITE = 'Platform_BAT'
    TEST_NAME = 'Default OTA Bucket Check'

    def test(self):
        retry = 60
        while retry >= 0:
            response = self.uut_owner.admin_bearer_request(
                method='GET',
                url='{}/ota/v1/device/deviceId/{}'.format(self.uut_owner.cloud.ota_bucket_url, self.uut_owner.get_device_id()))
            if response.status_code != 200:
                raise self.err.TestFailure('Check device in OTA bucket failed, status code:{0}, error log:{1}'.
                                           format(response.status_code, response.content))
            else:
                self.log.debug(response.json())
                bucket_data = response.json()['data']
                if not bucket_data:
                    if retry == 0:
                        raise self.err.TestFailure("Reaching maxinum retries, failed to get check device in ota bucket!")
                    self.log.warning("Failed to get bucket info, retry after 60 secs, remaining {} retries".format(retry))

                    time.sleep(60)
                    retry -= 1
                else:
                    get_bucket_id = bucket_data['bucketId']
                    if get_bucket_id == "DEVICE_VERSION":
                        # If bucket id is "DEVICE_VERSION", that means device is even not in the default bucket,
                        # and beta users will not able to be ota forever
                        self.log.warning("{}".format(bucket_data))
                        raise self.err.TestFailure('Bucket_id is "DEVICE_VERSION", Test Failed !!!')
                    else:
                        self.log.info('Device Bucket ID: {}'.format(get_bucket_id))
                        break

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check default OTA bucket Script ***
        Examples: ./run.sh bat_scripts_new/default_ota_bucket_check.py --uut_ip 10.92.224.68\
        """)

    test = DefaultOTABucketCheck(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
