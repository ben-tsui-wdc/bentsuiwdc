# -*- coding: utf-8 -*-

__author__ = "Ben Tsui <ben.tsui@wdc.com>"

# std modules
import sys
import os
from time import sleep

# 3rd party modules
from appium import webdriver
from appium.webdriver.common.touch_action import TouchAction

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase, Settings
from platform_libraries.test_result import ELKTestResult
from bat_scripts_new.factory_reset import FactoryReset


class MobileOnboarding(TestCase):

    TEST_SUITE = "Mobile Testing"
    TEST_NAME = "Onboarding Test"

    SETTINGS = {
        # Disable all utilities.
        'disable_firmware_consistency': True,
        'adb': False,
        'uut_owner': False  # Disbale restAPI.
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

    def before_loop(self):
        pass 

    def before_test(self):
        self._test_check_status()

    def test(self):
        # Use for saving error snapshot
        directory = self.env.output_folder
        screenshot_name = 'screenshot.png'

        try:
            # Create the mobile webdriver object
            self.driver = webdriver.Remote(self.appium_server, self.desired_caps)
        except Exception as e:
            raise self.err.TestFailure('Appium WebDriver init failed! Stop the test!')

        try:
            self.log.info("### Start running onboarding test ###")
            self.log.info("Appium will reset app, it will take a while...")
            # Keep looking for specified element for 60 secs at most (default is 0)
            self.driver.implicitly_wait(60)
            # Use for touching (x,y) axis, some element cannot be clicked by id or xpath
            self.TA = TouchAction(self.driver)
            self._test_agree_eula()
            self._test_sign_in_mycloud()
            self._test_add_device()
            self._test_setup_device_wifi()
            self._test_device_first_time_setup_and_share_info()
        except Exception as e:
            self.log.info("Try to catch the screenshot when failure")
            self.driver.save_screenshot(directory + screenshot_name)
            raise self.err.TestFailure('Mobile onboarding failed! Error message:{}'.format(e))
        finally:
            self.log.info("Quit WebDriver after testing")
            self.driver.quit()

    def after_test(self):
        pass

    def after_loop(self):
        pass

    # Todo: These wrapper functions should be moved to mobile library
    def EID(self, element_id):
        return self.driver.find_element_by_id(element_id)

    def EXPATH(self, element_xpath):
        return self.driver.find_element_by_xpath(element_xpath)

    def EAID(self, element_accessibility_id):
        return self.driver.find_element_by_accessibility_id(element_accessibility_id)

    def _test_check_status(self):
        self.log.info("Run factory reset via command line to clear owner")
        self.serial_client.serial_write('busybox nohup factory_reset.sh')
        self.serial_client.wait_for_boot_complete(timeout=60*30)
        self.log.info("Wait 2 mins for device to complete boot up")  # We don't have IP address and cannot use adb to check it
        sleep(120)
        self.serial_client.serial_write('logcat -d | grep MyService | grep sn')
        try:
            self.serial_client.serial_wait_for_string('MyService:', timeout=60, raise_error=True)
        except:
            self.log.warning('Cannot see serial number information, try to reboot the device')
            self.serial_client.serial_write('busybox nohup reboot')
            self.serial_client.wait_for_boot_complete(timeout=60*30)
            self.log.info("Wait 2 mins for device to complete boot up")  # We don't have IP address and cannot use adb to check it
            self.serial_client.serial_write('logcat -d | grep MyService | grep sn')
            try:
                self.serial_client.serial_wait_for_string('MyService:', timeout=60, raise_error=True)
            except:
                raise self.err.TestFailure('Still cannot see serial number after reboot! Stop the test!')

        self.log.info('MyService keyword is found, ready to test')

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
        ).click()  # self.TA.tap(x=1464, y=132).perform()
        self.log.info("Click 'Skip' to skip auto backup setting")
        sleep(5)

    def _test_add_device(self):
        self.EXPATH(
            '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/' +
            'android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/' +
            'android.view.ViewGroup[2]/android.view.ViewGroup[5]'
        ).click()  # self.TA.tap(x=968, y=1987).perform()
        self.log.info("Click settings")
        self.EXPATH(
            "(//android.view.ViewGroup[@content-desc=\"open  device settings page\"])[1]/android.view.ViewGroup"
        ).click()  # self.TA.tap(x=121, y=721).perform()
        self.log.info("Click add device")

        # Todo: If there's only one device, it'll be found automatically

        self.EID("com.android.packageinstaller:id/permission_allow_button").click()  # self.TA.tap(x=1145, y=1101).perform()
        self.log.info("Allow My Cloud to access devices")
        self.log.info("Wait 30 secs for searching...")
        sleep(30)

        # Check which device is our device
        index = 1
        device_found = False
        swipe = True
        swipe_times = 30
        retry = 0
        retry_times = 10
        # Change wait time to 5 secs or it will take too much time on non-exist element
        self.driver.implicitly_wait(2)
        self.log.info("Searching for serial number: {}".format(self.serial_number))
        try_next = True  # Sometimes scroll will stop between 2 devices, try if the index start from 2
        while retry <= retry_times:
            """
                We need to swipe page to find testing device,
                if we see "I don't see my device" that means we already scroll to the bottom
            """
            try:
                if self.EAID("I don't see my device"):
                    swipe = False
            except:
                pass

            while index < 10:
                try:
                    # Device name
                    name = self.EXPATH(
                         "/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/" +
                         "android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup/" +
                         "android.view.ViewGroup/android.widget.ScrollView/android.view.ViewGroup/" +
                         "android.view.ViewGroup[{}]/android.widget.TextView[2]".format(index)
                    ).get_attribute('text')

                    if try_next:
                        try_next = False

                    self.log.info("### Device serial number: {} ###".format(name))

                    if name == 'XXXX-{}'.format(self.serial_number):
                        device_found = True
                        break

                    index += 1
                except:
                    if try_next:
                        self.log.info("Try next index")
                        index += 1
                        try_next = False
                    else:
                        if swipe:
                            if swipe_times <= 0:
                                self.log.error("Swipe several times but not reach the page bottom, check if something wrong")
                                raise

                            self.log.info("Cannot find specified device, swipe page and retry")
                            self.TA.press(x=500, y=1275).wait(1000).move_to(x=500, y=400).release().perform()
                            swipe_times -= 1
                            index=1
                            try_next = True
                            try:
                                if self.EAID("I don't see my device"):
                                    swipe = False
                            except:
                                pass
                        else:
                            self.log.info("Already reach the page bottom")
                            break

            if device_found:
                self.log.info("Found specified test device!")
                self.EXPATH('(//*[@content-desc="Device found!"])[{}]'.format(index)).click()
                break
            else:
                self.EAID('Back').click()
                self.EXPATH(
                    "(//android.view.ViewGroup[@content-desc=\"open  device settings page\"])[1]/android.view.ViewGroup"
                ).click()
                self.log.info("Cannot find specified device, click 'Back' and 'add device' again. {} retries remaining...".format(retry_times-retry))
                self.log.info("Wait 30 secs for searching...")
                sleep(30)
                retry += 1
                # Reset the swipe flag/retry times and device name index
                swipe = True
                swipe_times = 30
                index = 1

        if not device_found:
            raise Exception("Cannot find specified device name!")

        self.driver.implicitly_wait(60)

    def _test_setup_device_wifi(self):
        router_found = False
        swipe = True
        swipe_times = 30
        last_device = ''
        retry = 0
        retry_times = 10
        index = 1
        wifi_name = ''
        self.log.info("### List available SSID ### ")
        self.driver.implicitly_wait(2)
        self.log.info("Searching for Wi-FI SSID: {}".format(self.wifi_ssid))
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
                except:
                    if all([wifi_name, last_device, (wifi_name == last_device)]):
                        self.log.info("Already reach the page bottom")
                        break

                    if swipe:
                        if swipe_times <= 0:
                            self.log.error("Swipe {} times but not reach the page bottom, check if something wrong".format(swipe_times))
                            raise

                        self.log.info("Cannot find specified ssid, swipe page and retry")
                        self.TA.press(x=500, y=1275).wait(1000).move_to(x=500, y=400).release().perform()
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
                self.log.info("Wait for 15 secs to refresh the router list...")
                sleep(15)
                retry += 1
                # Reset the swipe flag/retry times and device name index
                swipe = True
                swipe_times = 30
                index = 1

        if not router_found:
            raise Exception("Cannot find specified router!")
        
        self.driver.implicitly_wait(60)

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

    def _test_device_first_time_setup_and_share_info(self):
        self.log.info("Wait 45 secs for setting first time use...")
        sleep(45)

        try:
            self.EAID("link-to-share-a11y").click()
            self.log.info("Click share info for product improvement")
        except:
            self.log.info("Setting first time to use might take longer..wait for 45 more secs")
            sleep(45)
            self.EAID("link-to-share-a11y").click()
            self.log.info("Click share info for product improvement")            

        self.EXPATH(
            '/hierarchy/android.widget.FrameLayout/android.widget.LinearLayout/android.widget.FrameLayout/' +
            'android.widget.FrameLayout/android.view.ViewGroup/android.view.ViewGroup[2]/android.view.ViewGroup/' +
            'android.view.ViewGroup[2]/android.view.ViewGroup/android.widget.TextView'
        ).click()
        self.log.info("Click 'Skip' to skip auto backup setting")
        sleep(5)

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
    parser.add_argument('--wifi_ssid', help="", default='integration_2.4G')
    parser.add_argument('--wifi_password', help="", default='automation')
    parser.add_argument('--serial_number', help="", default='WDTW-AUTO')

    test = MobileOnboarding(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)

