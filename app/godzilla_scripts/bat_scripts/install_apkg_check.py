# -*- coding: utf-8 -*-
""" Test case to check apkg can be installed
"""
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import time
import lxml.etree
# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase
from platform_libraries.godzilla import Godzilla
from platform_libraries.common_utils import execute_local_cmd


class InstallAPKGCheck(GodzillaTestCase):

    TEST_SUITE = 'Godzilla BAT'
    TEST_NAME = 'Install APKG Check'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-1804'
    PRIORITY = 'Blocker'
    COMPONENT = 'PLATFORM'
    ISSUE_JIRA_ID = None

    SETTINGS = {
        'uut_owner': False
    }

    ERROR_CODE = {
        "0": "NOT_REPLACE",
        "1": "UPLOAD_OK",
        "2": "HDD_NOT_READY",
        "3": "UPLOAD_FAIL",
        "4": "HAVE_INSTALL",
        "5": "HDD_NOT_ENOUGH_SIZE",
        "6": "MEMORY_NOT_ENOUGH_SIZE",
        "8": "SQUEEZE_CENTER_FILE_NOT_FOUND",
        "9": "3_PARTY",
        "10": "HAVE_INSTALL_3_PARTY",
        "11": "M_FIRMWARE_WRONG"
    }

    def declare(self):
        self.download_path = "ftp://ftp:ftppw@fileserver.hgst.com/GZA/restsdk/"
        self.apkg_name = "RestSDK-dev1"
        self.apkg_file = None

    def before_test(self):
        self.apkg_folder = "/usr/local/upload"
        self.apkg_install_status = "/tmp/upload_apkg_status"
        self.apkg_lists = "/var/www/xml/apkg_all.xml"
        self.gza = Godzilla(ip=self.env.ssh_ip)
        if not self.apkg_file:
            if self.env.model:
                self.model = self.env.model
            else:
                self.model = self.ssh_client.get_model_name()
            self.apkg_file = "MyCloud{}_RestSDK-dev1_2.0.0-999.bin".format(self.env.model)

    def test(self):
        if not self.ssh_client.check_hdd_ready_to_upgrade_fw():
            raise self.err.TestFailure('The HDD is not ready to update apkg!')
        else:
            self.log.info("HDD is ready to update apkg")

        # Download will be skipped if the image already existing and last modified time is the same
        self.log.info("Start downloading the apkg file")
        self.ssh_client.download_file("{}/{}".format(self.download_path, self.apkg_file), dst_path=self.apkg_folder)

        self.log.info("Start installing the APKG")
        self.ssh_client.execute_cmd("cd {0}; upload_apkg -t 2 -p {1}".format(self.apkg_folder, self.apkg_file),
                                    timeout=60*15)
        self.log.info("Install APKG script finished, wait for 30 seconds and check the status...")
        time.sleep(30)
        result = self.ssh_client.execute_cmd("cat {}".format(self.apkg_install_status))[0]
        if self.ERROR_CODE.get(result) != "UPLOAD_OK":
            if self.ERROR_CODE.get(result) == "HAVE_INSTALL":
                self.log.warning("The apkg was already installed before! Check if it's correct!")
            else:
                raise self.err.TestFailure("The install APKG script failed! Error message: {}".
                                           format(self.ERROR_CODE.get(result, "Unknown Error")))
        else:
            self.log.info("Install APKG script executed successfully")

        # App installed successfully will be listed in apkg_all.xml
        result = self.ssh_client.execute_cmd("cat {}".format(self.apkg_lists))[0]
        self.log.warning("Installed APKG lists: {}".format(result))

    def after_test(self):
        result = self.ssh_client.execute_cmd("cat {0} | grep {1}".format(self.apkg_lists, self.apkg_name))[0]
        if result:
            self.log.info("Uninstall the APKG by CGI temporarily")
            try:
                self.gza.login_device()
                self.gza.get_wd_xcsrf_token()
                cmd = "curl 'http://{0}/cgi-bin/apkg_mgr.cgi?cmd=cgi_apps_del&f_module_name={1}' -X GET " \
                      "-H 'X-CSRF-Token: {2}' -b '{3}'".format(self.env.ssh_ip, self.apkg_name,
                                                               self.gza.wd_xcsrf_token, self.gza.cookie_path)
                result = execute_local_cmd(cmd)[0]
                root = lxml.etree.fromstring(result)
                uninstall_status = root.findtext("result")
                if uninstall_status == "1":
                    self.log.info("Uninstall the APKG successfully!")
                else:
                    raise self.err.TestFailure("Failed to uninstall the APKG by CGI! Error code: {}".
                                               format(uninstall_status))
            except Exception as e:
                raise self.err.TestFailure("Failed to uninstall the APKG by CGI! Error: {}".format(repr(e)))
        else:
            self.log.info("Cannot find specified APKG: {}, skip uninstall steps!".format(self.apkg_name))


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser("""\
        *** Install APKG check test on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/bat_scripts/install_apkg_check.py --uut_ip 10.136.137.159 -model PR2100\
        """)
    parser.add_argument('--download_url', help='The download url for the APKG', default="ftp://ftp:ftppw@fileserver.hgst.com/GZA/restsdk/")
    parser.add_argument('--apkg_name', help='The APKG name', default="RestSDK-dev1")
    parser.add_argument('--apkg_file', help='The full APKG filename', default=None)
    test = InstallAPKGCheck(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
