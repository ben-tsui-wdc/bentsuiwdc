___author___ = 'Vance Lo <vance.lo@wdc.com>'

import time
import argparse
import os, sys

from platform_libraries.adblib import ADB
from bat_scripts.fwUpdateUbootUtility import fwUpdateUbootUtility
from bat_scripts.junit_xml import TestCase
from platform_libraries.test_result import upload_to_logstash

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to test Firmware uboot update Stress Test')
    parser.add_argument('--uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('--port', help='Destination port number, ex. 5555 (default)', default='5555')
    parser.add_argument('--env', help='Target environment, ex. dev1 (default)')
    parser.add_argument('--variant', help='Build variant, ex. debug', default='debug')
    parser.add_argument('--iter', help='Number of iterations', default='1')
    parser.add_argument('--fw', help='Update firmware version, ex. 4.0.0-100')
    parser.add_argument('--uboot', help='Uboot version confirm, ex. 4.1.4')
    parser.add_argument('--logstash', help='Logstash server IP address', default='10.92.234.101')
    parser.add_argument('--dry_run', help='Test mode, will not upload result to logstash', action='store_true', default=False)
    parser.add_argument('--local_image', action='store_true', default=False,
                        help='Download ota firmware image from local file server')

    args = parser.parse_args()

    iterations = int(args.iter)
    deviceIp = args.uut_ip
    logstash_server = 'http://{}:8000'.format(args.logstash)
    dry_run = args.dry_run
    port = args.port
    variant = args.variant
    environment = args.env
    local_image = args.local_image
    version = args.fw
    uboot = args.uboot
    adb = ADB(uut_ip=deviceIp, port=port)

    for i in range(iterations):
        adb.stop_otaclient()
        ubootUpdateStressTest = fwUpdateUbootUtility(adb=adb, env=environment, version=version,
                                                     uboot=uboot, local_image=local_image, variant=variant)
        ubootUpdateStressTest.log.info('Iteration: {}'.format(i+1))
        build = ubootUpdateStressTest.adb.getFirmwareVersion()
        ubootUpdateStressTest.log.info('Build: {}'.format(build))
        test_result = ''

        try:
            ubootUpdateStressTest.run()
            # Execute command to check restsdk is running and device connected to localhost.
            while not ubootUpdateStressTest._is_timeout(ubootUpdateStressTest.total_timeout):
                grepRest = ubootUpdateStressTest.adb.executeShellCommand('ps | grep restsdk', timeout=10)[0]
                if 'restsdk-server' in grepRest:
                    ubootUpdateStressTest.log.info("Restsdk-server is running")
                    print '\n'
                    break
                time.sleep(3)

            while not ubootUpdateStressTest._is_timeout(ubootUpdateStressTest.total_timeout):
                curl_localHost = ubootUpdateStressTest.adb.executeShellCommand('curl localhost/sdk/v1/device', timeout=10)[0]
                if 'Connection refused' not in curl_localHost:
                    ubootUpdateStressTest.log.info("Successfully connected to localhost")
                    print '\n'
                    break
                time.sleep(3)

            if ubootUpdateStressTest._is_timeout(ubootUpdateStressTest.total_timeout):
                ubootUpdateStressTest.error('Device is not ready, timeout for {} minutes'.format(ubootUpdateStressTest.total_timeout/60))
            else:
                ubootUpdateStressTest.log.info('Uboot Update Stress Test! Test PASSED!!!!')
                testcase = TestCase(name='Uboot Update Stress Test', classname='Stress', elapsed_sec=time.time()-ubootUpdateStressTest.start_time)
            test_result = 'Passed'
        except Exception as ex:
            ubootUpdateStressTest.log.error('Uboot Update Stress Test failed! Error message: {}'.format(repr(ex)))
            test_result = 'Failed'

        if not dry_run:
            # Upload result to logstash server
            data = {'testSuite': 'Uboot_Update_Stress_Test',
                    'testName': 'Uboot_Update_Stress_Test',
                    'build': build,
                    'ubootUpdateStressResult': test_result}
            upload_to_logstash(data, logstash_server)
