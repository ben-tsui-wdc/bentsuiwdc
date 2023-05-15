# -*- coding: utf-8 -*-

""" Test library for the Godzilla (OS3) devices
"""

__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import os
import shlex  # to split shell commands

# 3rd party modules
import lxml.etree
from subprocess32 import Popen, PIPE

# platform modules
import common_utils
from common_utils import execute_local_cmd


class Godzilla(object):

    def __init__(self, ip, username="admin", password="YWRtaW4=", cookie_path="/tmp/cookie.txt"):
        # Password is "admin" and encoded with base64
        self.log = common_utils.create_logger()
        self.device_ip = ip
        self.username = username
        self.password = password
        self.cookie_path = cookie_path
        self.wd_xcsrf_token = None

    def login_device(self):
        """ Result format: <config><logd_eula>1</logd_eula><res>1</res></config>
        """
        self.log.info("Login the device")
        cmd = "curl 'http://{0}/cgi-bin/login_mgr.cgi' --data 'cmd=wd_login&username={1}&pwd={2}' " \
              "-c '{3}' -v".format(self.device_ip, self.username, self.password, self.cookie_path)
        stdout, strerr = execute_local_cmd(cmd)
        root = lxml.etree.fromstring(stdout)
        eula_status = root.findtext("logd_eula")
        login_status = root.findtext("res")
        if eula_status != "1":
            raise RuntimeError("EULA status should be 1 but it's {}!".format(eula_status))
        if login_status != "1":
            raise RuntimeError("Login status should be 1 but it's {}!".format(login_status))

    def get_wd_xcsrf_token(self):
        self.log.info("Parser the WD-CSRF-TOKEN from {}".format(self.cookie_path))
        if not os.path.exists(self.cookie_path):
            raise RuntimeError("Please login the device before asking the tokens!")
        else:
            with open(self.cookie_path, 'r') as f:
                lines = f.readlines()
                for line in lines:
                    if "WD-CSRF-TOKEN" in line:
                        self.wd_xcsrf_token = line.split()[-1]
                        self.log.info("WD-CSRF-TOKEN: {}".format(self.wd_xcsrf_token))
                        break
                if not self.wd_xcsrf_token:
                    raise RuntimeError("Cannot find the WD-CSRF-TOKEN token information!")

    def get_ssh_status(self):
        cmd = "curl 'http://{0}/cgi-bin/system_mgr.cgi' -X POST -H 'X-CSRF-Token: {1}' " \
              "--data 'cmd=cgi_get_general' -b '{2}'".format(self.device_ip, self.wd_xcsrf_token, self.cookie_path)
        stdout, strerr = execute_local_cmd(cmd)
        root = lxml.etree.fromstring(stdout)
        ssh_status = root.find('device_info').findtext("ssh")
        if ssh_status == "1":
            self.log.info("SSH service status: Enabled")
            return True
        else:
            self.log.info("SSH service status: Disabled")
            return False

    def enable_ssh(self, ssh_password="d2VsYzBtZQ=="):
        """ The password is encoded with Base64 format
            d2VsYzBtZQ== <-> welc0me
        """
        self.log.info("Enable the SSH service")
        cmd = "curl 'http://{0}/cgi-bin/system_mgr.cgi' -X POST -H 'X-CSRF-Token: {1}' " \
              "--data 'cmd=cgi_ssh&ssh=1&pw={2}' -b '{3}'".format(self.device_ip, self.wd_xcsrf_token,
                                                                  ssh_password, self.cookie_path)
        execute_local_cmd(cmd)
        if not self.get_ssh_status():
            raise RuntimeError("Enable SSH service failed!")

    def disable_ssh(self):
        self.log.info("Disable the SSH service")
        cmd = "curl 'http://{0}/cgi-bin/system_mgr.cgi' -X POST -H 'X-CSRF-Token: {1}' " \
              "--data 'cmd=cgi_ssh&ssh=0' -b '{2}'".format(self.device_ip, self.wd_xcsrf_token, self.cookie_path)
        execute_local_cmd(cmd)
        if self.get_ssh_status():
            raise RuntimeError("Disable SSH service failed!")


if __name__ == '__main__':
    import sys

    print("### Run as a test script ###\n")
    if len(sys.argv) < 2:
        print('Please input the device IP Address. e.g. ./run.sh platform_libraries/godzilla.py 10.92.224.29')
        sys.exit(1)

    godzilla = Godzilla(sys.argv[1])
    godzilla.login_device()
    godzilla.get_wd_xcsrf_token()
    godzilla.get_ssh_status()
    godzilla.enable_ssh()
    godzilla.disable_ssh()
    godzilla.enable_ssh()