# -*- coding: utf-8 -*-

__author1__ = "Ben Tsui <ben.tsui@wdc.com>"
__author2__ = "Jason Chiang <jason.chiang@wdc.com>"

# std modules
from datetime import datetime, timedelta
import re
import sys
import time
# platform modules
from middleware.arguments import KDPInputArgumentParser
from middleware.kdp_test_case import KDPTestCase
from platform_libraries.constants import KDP

class LEDCheckBootSequence(KDPTestCase):

    TEST_SUITE = "Led Test"
    TEST_NAME = "Led Boot Sequence Test"
    # Popcorn
    TEST_JIRA_ID = 'KDP-887'

    SETTINGS = {
        'uut_owner': False
    }

    def declare(self):
        pass

    def init(self):
        if self.uut['model'] in ['yodaplus2']:
            self.sys_seq_expect = ['(null)', 'Power up', 'Proxy Disconnected', 'Wlan0_Up', 'BLE Started','Wifi Connected', 'Ready', 'Network Configured', 'Data Transfer Completed', 'Local IP Registered in Cloud', 'Proxy Connected']
            self.led_seq_expect = ['Fast Breathing', 'Full Solid']

    def before_test(self):
        # To reboot device
        self.ssh_client.reboot_and_wait_for_boot_completed()

    def test(self):
        self.log.info("Wait 90 seconds after reboot finished for led logging commpleted.")
        time.sleep(90)
        if self.uut['model'] in ['monarch2', 'pelican2']:
            '''
            # led log example 1
            a = '2023-01-09T05:30:59.810430+00:00 di=2IJn34TUhd  info led_ctrl_server: {"msgid":"LedServer","reason":"Starting WD Led-Server Version 1.2.13"}\r\n \
2023-01-09T05:30:59.822552+00:00 di=2IJn34TUhd  info led_ctrl_server: {"msgid":"LedServer","reason":"initializing and starting the led-server"}\r\n \
2023-01-09T05:31:55.885313+00:00 di=2IJn34TUhd  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Slow Breathing)->(Full Solid)"}\r\n  \
2023-01-09T05:31:55.889817+00:00 di=2IJn34TUhd  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (Data Transfer Completed)"}\r\n  \
2023-01-09T05:32:00.646378+00:00 di=2IJn34TUhd  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Data Transfer Completed) -> (Ready)"}\r\n  \
2023-01-09T05:32:02.380931+00:00 di=2IJn34TUhd  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Data Transfer Completed) -> (Proxy Connected)"}\r\n \
2023-01-09T05:32:04.320720+00:00 di=2IJn34TUhd  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Ready) -> (System bootup finish)"}'
            '''
            '''
            # led log example 2
            a = '2023-01-09T04:56:49.971143+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"Starting WD Led-Server Version 1.2.13"}\r\n \
2023-01-09T04:56:49.983179+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"initializing and starting the led-server"}\r\n \
2023-01-09T04:56:55.322420+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Slow Breathing)->(Full Solid)"}\r\n \
2023-01-09T04:56:55.326625+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (Ethernet Connected)"}\r\n \
2023-01-09T04:56:56.341205+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Full Solid)->(Slow Breathing)"}\r\n \
2023-01-09T04:56:56.344869+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Ethernet Connected) -> (Power up)"}\r\n \
2023-01-09T04:57:50.790013+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Slow Breathing)->(Error Slow Breathing)"}\r\n \
2023-01-09T04:57:50.796819+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (System bootup finish)"}\r\n \
2023-01-09T04:57:51.120810+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (System bootup finish) -> (Data Transfer Completed)"}\r\n \
2023-01-09T04:57:57.221044+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (Ready)"}\r\n \
2023-01-09T04:58:02.844373+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Error Slow Breathing)->(Full Solid)"}\r\n \
2023-01-09T04:58:02.848672+00:00 di=i1MRbiXqPn  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (Proxy Connected)"}'
            '''
            '''
            # led log example 3
            a = '2023-01-06T05:41:03.975810+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"Starting WD Led-Server Version 1.2.13"}\r\n \
2023-01-06T05:41:03.987951+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"initializing and starting the led-server"}\r\n \
2023-01-06T05:41:09.327718+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Slow Breathing)->(Full Solid)"}\r\n \
2023-01-06T05:41:09.331769+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (Ethernet Connected)"}\r\n \
2023-01-06T05:41:10.346160+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Full Solid)->(Slow Breathing)"}\r\n \
2023-01-06T05:41:10.349793+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Ethernet Connected) -> (Power up)"}\r\n \
2023-01-06T05:41:48.423943+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (Data Transfer Completed)"}\r\n \
2023-01-06T05:41:54.768069+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"Switching Led state (Slow Breathing)->(Full Solid)"}\r\n \
2023-01-06T05:41:54.772179+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Power up) -> (Ready)"}\r\n \
2023-01-06T05:41:55.328652+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Ready) -> (Proxy Connected)"}\r\n \
2023-01-06T05:41:58.108967+00:00 di=GSlh4eIcPS  info led_ctrl_server: {"msgid":"LedServer","reason":"sys state change: (Ready) -> (System bootup finish)"}'
            '''        
            stdout, stderr = self.ssh_client.execute_cmd('grep -r led_ctrl_server /var/log/analyticpublic.log')
            led_log = stdout.splitlines()
            item_to_be_checked = []
            proxy_check_flag = True
            ready_check_flag = True
            full_solid_check_flag = True
            while led_log:
                # We collect the LATEST log entry of "-> (Proxy Connected)", "-> (Ready)" and "->(Full Solid)".
                # Their timestamp should be very close.
                temp = led_log.pop()
                if 'sys state change' in temp:
                    if '-> (Proxy Connected)' in temp and proxy_check_flag:
                        item_to_be_checked.append(temp)
                        proxy_check_flag = False
                    elif '-> (Ready)' in temp and ready_check_flag:
                        item_to_be_checked.append(temp)
                        ready_check_flag = False
                elif 'Switching Led state' in temp:
                    if '->(Full Solid)' in temp and full_solid_check_flag:
                        item_to_be_checked.append(temp)
                        full_solid_check_flag = False
                        if '(Slow Breathing)->(Full Solid)' in temp or '(Error Slow Breathing)->(Full Solid)' in temp:
                            pass
                        else:
                            raise self.err.TestFailure('The led state is not changed from (Slow Breathing) to (Full Solid). The actual log shows: {}'.format(temp))
                if not proxy_check_flag and not ready_check_flag and not full_solid_check_flag:
                    break
            self.log.warning('led logs to be checked:\r\n')
            for item in item_to_be_checked:
                self.log.info(item)
            if len(item_to_be_checked) != 3:
                raise self.err.TestFailure('Some necesary led logs isn\'t displayed.')
            time_string = re.search("\d+-\d+-\d+T\d\d\:\d\d\:\d\d", item_to_be_checked[0]).group()
            time_stamp_newest = datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S')
            time_string = re.search("\d+-\d+-\d+T\d\d\:\d\d\:\d\d", item_to_be_checked[-1]).group()
            time_stamp_oldest = datetime.strptime(time_string, '%Y-%m-%dT%H:%M:%S')
            diff = time_stamp_newest - time_stamp_oldest
            diff_sec = diff.total_seconds()
            if diff_sec < 11:
                self.log.info('The time gap between newest log and oldest log is {} seconds, which is less than 10 seconds. We regard it as the same event.'.format(diff_sec))
            else:
                raise self.err.TestFailure('The time gap between newest log and oldest log is {} seconds, which is more than 10 seconds. Please check the analyticpublic.log to confirm if it is an real issue.'.format(diff_sec))

        # The led log of yodaplus2 will be changed every time when device rebooted due to WiFi. Besides, some log formats are very different from MCH.
        # I have no choice but use separate script to parse the led log of yodaplus2. 
        elif self.uut['model'] in ['yodaplus2']:
            stdout, stderr = self.ssh_client.execute_cmd('grep -r led_ctrl_server /var/log/analyticpublic.log')
            led_log_list = stdout.splitlines()
            led_state_before = None
            led_state_after = None
            for i, line in enumerate(led_log_list):
                if 'sys_state received' in line and 'led_state turns to' in line:
                    received_state = re.search('sys_state received (.+), ', line).group(1)
                    led_state = re.search('led_state turns to (.+)"', line).group(1)
                    #self.log.warning('{}, turned into {}'.format(received_state, led_state))
                    if received_state in ['(null)', 'Power up', 'Proxy Disconnected', 'Wlan0_Up', 'BLE Started','Wifi Connected', 'Network Configured', 'Data Transfer Completed']:
                        if led_state != 'Fast Breathing':
                            raise self.err.TestFailure('led_state should be "Fast Breathing" due to {}. See log [{}]'.format(received_state, line))
                    elif received_state in ['Proxy Connected']:
                        if led_state != 'Full Solid':
                            raise self.err.TestFailure('led_state should be "Full Solid" due to {}. See log [{}]'.format(received_state, line))
                elif 'sys state change:' in line:
                    sys_state_before = re.search("\((.+)\).->.\((.+)\)", line).group(1)
                    sys_state_after = re.search("\((.+)\).->.\((.+)\)", line).group(2)
                    #self.log.warning('{} -> {}'.format(sys_state_before, sys_state_after))
                    if self.sys_seq_expect.index(sys_state_before) > self.sys_seq_expect.index(sys_state_after):
                        if sys_state_before == 'Proxy Connected' and sys_state_after == 'Ready':
                            pass
                        else:
                            raise self.err.TestFailure('The boot sequence is not as expected. See log [{}]'.format(line))

    def after_test(self):
        pass


if __name__ == '__main__':
    parser = KDPInputArgumentParser("""
        *** LED Check: Boot sequence on Kamino Android ***
        """)
    test = LEDCheckBootSequence(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)