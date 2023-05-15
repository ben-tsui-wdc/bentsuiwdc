# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
import time
from time import sleep

# 3rd party modules
from appium import webdriver
from appium.webdriver.common.touch_action import TouchAction

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings
from bat_scripts_new.factory_reset import FactoryReset

class MobileChangeSSID(TestCase):

    TEST_SUITE = "Mobile Testing"
    TEST_NAME = "Wi-Fi change ssid test"

    SETTINGS = {
        # Disable all utilities.
        'disable_firmware_consistency': True,
    }


    def init(self):

        self.desired_caps = dict()
        self.desired_caps['platformName'] = self.mobile_platform
        self.desired_caps['platformVersion'] = self.mobile_version
        self.desired_caps['deviceName'] = self.mobile_device_name
        self.desired_caps['app'] = self.mobile_app
        self.desired_caps['appPackage'] = self.mobile_app_package
        self.desired_caps['appActivity'] = self.mobile_app_mainpage
        self.desired_caps['skipUnlock'] = True
        self.desired_caps['noReset'] = False
        self.desired_caps['fullReset'] = False

    def test(self):
        # Use for saving error snapshot
        directory = self.env.output_folder
        screenshot_name = 'screenshot.png'
        self.log.info("### Start running Wifi change SSID test ###")
        '''
            Appium will be hanged in the latest mobile app version,
            but it is not a bug for mobile app, use command line to change ip temporarily
        '''
        self._test_change_wifi_by_cmd()
        try:
            # Create the mobile webdriver object
            self.driver = webdriver.Remote(self.appium_server, self.desired_caps)
        except Exception as e:
            raise self.err.TestFailure('Appium WebDriver init failed! Stop the test!')

        try:
            self._test_agree_eula()
            self._test_sign_in_mycloud()
            self._test_wifi_is_changed()
            # self._test_change_device_ssid()
        except Exception as e:
            self.log.info("Try to catch the screenshot when failure")
            self.driver.save_screenshot(directory + screenshot_name)
            raise self.err.TestFailure('Mobile change Wi-Fi SSID failed! Error message:{}'.format(e))
        finally:
            self.log.info("Quit WebDriver after testing")
            self.driver.quit()

    def after_test(self):
        self.log.info("Run factory reset by rest api after testing")
        env_dict = self.env.dump_to_dict()
        factory_reset = FactoryReset(env_dict)
        factory_reset.no_rest_api = False

    # Todo: These wrapper functions should be moved to mobile library
    def EID(self, element_id):
        return self.driver.find_element_by_id(element_id)

    def EXPATH(self, element_xpath):
        return self.driver.find_element_by_xpath(element_xpath)

    def EAID(self, element_accessibility_id):
        return self.driver.find_element_by_accessibility_id(element_accessibility_id)

    def _test_change_wifi_by_cmd(self):
        old_wifi_status = self.serial_client.get_network(self.old_wifi_ssid)
        if '[CURRENT]' not in old_wifi_status:
            raise self.err.TestFailure('Wifi: {} was not connected!'.format(self.old_wifi_ssid))
        self.log.warning(old_wifi_status)
        self.serial_client.add_wifi(ssid=self.wifi_ssid, password=self.wifi_password, enable_wifi=False, connect_wifi=False)
        new_wifi_status = self.serial_client.get_network(self.wifi_ssid)
        self.log.warning(new_wifi_status)
        new_wifi_num = new_wifi_status[0]
        self.log.info("Start to switch wifi from {} to {}".format(self.old_wifi_ssid, self.wifi_ssid))
        self._enable_network_and_check(new_wifi_num, self.wifi_ssid)

    def _enable_network_and_check(self, network_num, ssid):
        self.adb.disconnect()
        self.serial_client.disconnect_WiFi()
        sleep(3)
        self.serial_client.connect_network(network_id=network_num)
        sleep(8)
        status = self.serial_client.get_network(ssid)
        if '[CURRENT]' not in status:
            raise self.err.TestFailure('Setup new Wi-Fi Failed!')

        wifi_state = self.adb.executeShellCommand('wpa_cli -i wlan0 -p /data/misc/wifi/sockets status | grep wpa_state')[0]
        if 'COMPLETED' not in wifi_state:
            raise self.err.TestFailure('Setup new Wi-Fi not complete!')

    def _test_agree_eula(self):
        self.EAID("link to sign into mycloud device").click()
        self.log.info("Click agree EULA")

    def _test_sign_in_mycloud(self):
        self.EAID("link to sign into mycloud device").click()
        self.log.info("Click sign in")
        self.EAID('input for email in login').set_value(self.env.username)
        self.EAID('input for password in login').set_value(self.env.password)
        self.EAID("Sign In").click()
        self.log.info("Input username and password, then sign in")

        self.EXPATH(
            '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/' +
            'android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup[2]/android.view.ViewGroup/' +
            'android.view.ViewGroup[2]/android.view.ViewGroup/android.widget.TextView'
        ).click()
        self.log.info("Click 'Skip' to skip auto backup setting")
        sleep(5)

    def _test_wifi_is_changed(self):
        self.EXPATH(
            '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/' +
            'android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/' +
            'android.view.ViewGroup[2]/android.view.ViewGroup[5]'
        ).click()
        self.log.info("Click settings")

        try:
            self.EXPATH(
                '(//android.view.ViewGroup[@content-desc=\"open wdtw\'s My Cloud Home Wireless device settings page\"])[1]' +
                '/android.view.ViewGroup/android.widget.TextView'
            ).click()
        except:
            self.log.warning("Xpath is not working, try to touch axises")
            self.TA.tap(x=237, y=633).perform()

        self.log.info("Click the registered device, wait 20 secs to show Wi-Fi status...")
        sleep(20)

        current_wifi_name = self.EXPATH(
            '(//android.view.ViewGroup[@content-desc=\"Network\"])[1]/android.view.ViewGroup/android.widget.TextView[2]'
        ).get_attribute('text')

        if current_wifi_name != self.wifi_ssid:
            raise self.err.TestFailure('Wifi ssid should be {} but it is {}!'.format(self.wifi_ssid, current_wifi_name))

    def _test_change_device_ssid(self):
        '''
            This test step is skipped temporarily
        '''
        self.EXPATH(
            '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/' +
            'android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/' +
            'android.view.ViewGroup[2]/android.view.ViewGroup[5]'
        ).click()
        self.log.info("Click settings")

        try:
            self.EXPATH(
                '(//android.view.ViewGroup[@content-desc=\"open wdtw\'s My Cloud Home Wireless device settings page\"])[1]' +
                '/android.view.ViewGroup/android.widget.TextView'
            ).click()
        except:
            self.log.warning("Try to touch axises")
            self.TA.tap(x=169, y=827).perform()

        self.log.info("Click the registered device, wait 10 secs to show Wi-Fi status...")
        sleep(10)

        self.EXPATH(
            '(//android.view.ViewGroup[@content-desc=\"Network\"])[1]/android.view.ViewGroup/android.widget.TextView[2]'
        ).click()
        self.log.info("Click the original ssid: {}".format(self.old_wifi_ssid))

        self.EXPATH(
            '(//android.view.ViewGroup[@content-desc=\"Network\"])[3]/android.view.ViewGroup/android.widget.TextView[2]'
        ).click()
        self.log.info("Click the original ssid: {} again".format(self.old_wifi_ssid))
        sleep(5)

        try:
            self.log.warning("Try EXPATH")
            self.EXPATH(
                '/hierarchy/android.widget.FrameLayout/android.widget.FrameLayout/android.widget.FrameLayout/' +
                'android.widget.LinearLayout/android.widget.ScrollView/' +
                'android.widget.LinearLayout/android.widget.Button[2]'
            ).click()
        except:
            self.log.warning("Try to touch axises")
            self.TA.tap(x=734, y=1103).perform()

        self.log.info("Click 'Continue' when asking if we're sure to change Wi-Fi")
        sleep(5)

        self.EID("com.android.packageinstaller:id/permission_allow_button").click()
        self.log.info("Click the allow permission button")

        self.log.info("Wait 45 secs for searching Wi-Fi...")
        sleep(45)
        self.log.info('Connected to original Wi-Fi, press Continue')

        # Todo: This step will be hanged in the latest mobile app version, it's not a bug but Appium will be disconnected

        '''
        try:
            self.log.warning("Try EXPATH")
            self.EXPATH(
                '(//android.view.ViewGroup[@content-desc=\"Continue\")]/android.widget.TextView'
            ).click()
        except:
            self.log.warning("Try Touch")
            self.TA.tap(x=522, y=1388).perform()
        '''
        self.TA.tap(x=522, y=1388).perform()
        self.log.info('Continue is pressed')
        sleep(30)

        router_found = False
        swipe = True
        swipe_times = 3
        last_device = ''
        retry = 0
        retry_times = 5
        index = 2
        wifi_name = ''
        self.log.info("### List available SSID ### ")
        self.driver.implicitly_wait(5)
        while retry <= retry_times:
            while index < 20:
                try:
                    wifi = self.EXPATH(
                         "/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/" +
                         "android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/" +
                         "android.view.ViewGroup/android.widget.ScrollView/android.view.ViewGroup/" +
                         "android.view.ViewGroup[{}]/android.widget.TextView".format(index)
                    )
                    wifi_name = wifi.get_attribute('text')
                    self.log.info(wifi_name)
                    if wifi_name == self.wifi_ssid:
                        router_found = True
                        break

                    index += 1
                except Exception as e:
                    if all([wifi_name, last_device, (wifi_name == last_device)]):
                        self.log.info("Already reach the page bottom")
                        break

                    if swipe:
                        if swipe_times <= 0:
                            self.log.error("Swipe {} times but not reach the page bottom, check if something wrong".format(swipe_times))
                            raise

                        self.log.info("Cannot find specified ssid, swipe page and retry")
                        self.TA.press(x=0, y=0).move_to(x=0, y=20).release().perform()
                        sleep(5)
                        swipe_times -= 1
                        index=1
                    else:
                        break

            if router_found:
                self.log.info("Found specified router!")
                wifi.click()
                self.log.info("Click ssid: {}".format(self.wifi_ssid))
                break
            else:
                # Refresh button
                self.EXPATH(
                    "/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/" +
                    "android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/" +
                    "android.view.ViewGroup[1]/android.view.ViewGroup/android.widget.ImageView"
                ).click()
                retry += 1
                # Reset the swipe flag/retry times and device name index
                swipe = True
                swipe_times = 5
                index = 1

        if not router_found:
            raise Exception("Cannot find specified router!")

        self.driver.implicitly_wait(30)

        self.EXPATH(
            '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/' +
            'android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/' +
            'android.view.ViewGroup[2]/android.widget.EditText'
        ).set_value(self.wifi_password)
        self.log.info("Enter Wi-Fi password")

        self.EXPATH(
            '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/' +
            'android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/android.view.ViewGroup/' +
            'android.view.ViewGroup[1]/android.view.ViewGroup[2]/android.widget.TextView'
        ).click()
        self.log.info("Join Wi-Fi")

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Mobile Onboarding Test Case ***
        """)
    parser.add_argument('--appium_server', help="", default='http://192.168.1.59:4723/wd/hub')
    parser.add_argument('--mobile_platform', help="", default='Android', choices=['Android', 'iOS'])
    parser.add_argument('--mobile_version', help="", default='7.0')
    parser.add_argument('--mobile_device_name', help="", default="Android Real Device")
    parser.add_argument('--mobile_app', help="", default="/Users/wd_tw/Downloads/app-release-978.apk")
    parser.add_argument('--mobile_app_package', help="", default='com.kamino.wdt')
    parser.add_argument('--mobile_app_mainpage', help="", default='com.kamino.wdt.MainActivity')
    parser.add_argument('--old_wifi_ssid', help="", default='integration_2.4G')
    parser.add_argument('--wifi_ssid', help="", default='integration_5G')
    parser.add_argument('--wifi_password', help="", default='automation')

    test = MobileChangeSSID(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)