# -*- coding: utf-8 -*-
""" Tool for fatory reset kamino device.
"""
# std modules
import logging
import sys
import time
from argparse import ArgumentParser

# platform modules
from platform_libraries.adblib import ADB
from platform_libraries.common_utils import create_logger
from platform_libraries.restAPI import RestAPI
from platform_libraries.serial_client import SerialClient
from platform_libraries.ssh_client import SSHClient


class DeviceNotBootUp(RuntimeError):
    exit_code = 1

class ParamsRequests(RuntimeError):
    exit_code = 2

class ResetFailed(RuntimeError):
    exit_code = 10

class ResetFailedByRestCall(RuntimeError):
    exit_code = 11

class ResetFailedByADB(RuntimeError):
    exit_code = 12

class ResetFailedBySerial(RuntimeError):
    exit_code = 13

class ResetFailedBySSH(RuntimeError):
    exit_code = 14

class RestCallFailedButOtherWorks(RuntimeError):
    exit_code = 21

class ADBFailedButOtherWorks(RuntimeError): # Not use
    exit_code = 22

class SerialFailedButOtherWorks(RuntimeError): # Not use
    exit_code = 23


class FactoryReset(object):

    def __init__(self, parser):
        # Inpu aprs
        self.device_ip = parser.ip
        self.serial_server_ip = parser.serial_server_ip
        self.serial_server_port = parser.serial_server_port
        self.username = parser.username
        self.password = parser.password
        self.cloud_env = parser.cloud_env
        self.no_wait = parser.no_wait
        self.waiting_time = parser.waiting_time
        self.success_if_resetted = parser.success_if_resetted
        self.kdp = parser.kdp
        self.ssh_user = parser.ssh_user
        self.ssh_password = parser.ssh_password
        self.ssh_port = parser.ssh_port

        # Utils
        self.adb = None
        self.serial_client = None
        self.ssh_client = None
        self.rest_api = None
        self.log = create_logger(overwrite=False, stream_log_level=logging.info)
        # Vars.
        self.reset_cmd_works = False
        self.device_boot_completed = False
        self.reset_cmds = []
        self.cmd_exceptions = []

        if self.waiting_time < 5*60:
            self.log.info('Set waiting_time to 5 mins.')
            self.waiting_time = 5*60

        if self.device_ip:
            if self.kdp:
                self.log.info('Init SSH connection...')
                self.ssh_client = SSHClient(self.device_ip, self.ssh_user, self.ssh_password, self.ssh_port)
                self.ssh_client.connect()
            else:
                self.log.info('Init ADB connection...')
                self.adb = ADB(uut_ip=self.device_ip, port=5555)
                self.adb.connect()
        elif self.serial_server_ip and self.serial_server_port:
            self.log.info('Init serail connection...')
            self.serial_client = SerialClient(self.serial_server_ip, self.serial_server_port, stream_log_level=logging.DEBUG)
            self.serial_client.initialize_serial_port()
        else:
            raise ParamsRequests('Need ip or serial args')

        if self.username and self.password:
            self.log.info('Init REST client...')
            if not self.cloud_env: self.check_env()
            if not self.device_ip: self.check_device_ip()
            if self.device_ip:
                try:
                    self.rest_api = RestAPI(
                        uut_ip=self.device_ip, env=self.cloud_env, username=self.username,
                        password=self.password, debug=False, init_session=False,
                        stream_log_level=logging.DEBUG
                    )
                except Exception as e:
                    self.log.error(e, exc_info=True)
                    self.cmd_exceptions.append(ResetFailedByRestCall)
                if self.adb: self.rest_api.set_adb_client(self.adb)
            else:
                self.log.warning('Seems device has no network connection')
                self.cmd_exceptions.append(ResetFailedByRestCall)

    def main(self):
        self.reset_device()
        if self.reset_cmd_works and not self.no_wait:
            self.wait_for_device_boot_completed()
        self.handle_failures()

    def check_env(self):
        if self.adb:
            self.cloud_env = self.adb.get_environment()
        elif self.serial_client: raise RuntimeError('Not implement yet')

    def check_device_ip(self):
        if self.serial_client:
            ip = self.serial_client.get_ip()
            if ip == '192.168.43.1':
                self.log.warning('Device is in softAP mode.')
            elif ip:
                self.device_ip = ip

    def reset_device(self):
        if self.rest_api:
            self.reset_cmds.append([self.reset_by_rest_call, ResetFailedByRestCall])
        if self.adb:
            self.reset_cmds.append([self.reset_by_adb, ResetFailedByADB])
        if self.ssh_client:
            self.reset_cmds.append([self.reset_by_ssh, ResetFailedBySSH])
        if self.serial_client:
            self.reset_cmds.append([self.reset_by_serial_write, ResetFailedBySerial])

        for reset_cmd, exception_cls in self.reset_cmds:
            try:
                self.log.info('Use {}...'.format(reset_cmd.__name__))
                reset_cmd()
                self.reset_cmd_works = True
                break
            except Exception as e:
                self.log.error(e, exc_info=True)
                self.cmd_exceptions.append(exception_cls)

    def reset_by_rest_call(self):
        self.rest_api.get_id_token()
        self.rest_api.factory_reset()

    def reset_by_adb(self):
        self.adb.executeShellCommand('busybox nohup reset_button.sh factory', _no_resend=True)

    def reset_by_ssh(self):
        self.ssh_client.execute_cmd('busybox nohup reset_button.sh factory')

    def reset_by_serial_write(self):
        self.serial_client.serial_write("")
        self.serial_client.serial_write("reset_button.sh factory")
        self.serial_client.logger.info('Expect device do rebooting...')
        if self.kdp:
            self.serial_client.serial_wait_for_string('The system is going down', timeout=60*35)
        else:
            self.serial_client.serial_wait_for_string('init: stopping android....', timeout=60*10)

    def wait_for_device_boot_completed(self):
        if self.adb: # Only for MCH
            self.adb.wait_for_device_to_shutdown(timeout=60)
            time.sleep(60*3)  # For MCH, wait for golden mode reboot
            if self.adb.wait_for_device_boot_completed(timeout=self.waiting_time - 4*60, time_calibration_retry=False):
                self.device_boot_completed = True
        elif self.serial_client: # Only for ibi
            if self.kdp: # lazy format may not work soemtimes
                if self.serial_client.wait_for_boot_complete_kdp(timeout=self.waiting_time if self.waiting_time > 30*60 else 30*60, raise_error=False):
                    self.device_boot_completed = True
            else:
                if self.serial_client.wait_for_boot_complete(timeout=self.waiting_time, raise_error=False):
                    self.device_boot_completed = True
        else:
            time.time(self.waiting_time)
            self.device_boot_completed = True

    def handle_failures(self):
        exception_to_raise = None

        if self.reset_cmd_works:
            if self.device_boot_completed:
                if self.cmd_exceptions and not self.success_if_resetted:
                    exception_to_raise = RestCallFailedButOtherWorks
            else:
                exception_to_raise = DeviceNotBootUp
        else:
            if len(self.cmd_exceptions) == 1:
                exception_to_raise = self.cmd_exceptions[0]
            else:
                exception_to_raise = ResetFailed

        if exception_to_raise: raise exception_to_raise()


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Factory Reset Script For Kamino ***

        It won't attach user to device.
        It won't set up network after reset.

        Command Ordering: REST call > ADB/Serial Server

        For ibi:
            1) Reset by serail console: -ss-ip + -ss-port
            2) Reset by REST call first: -env + -u + -p + -ss-ip + -ss-port
        For MCH:
            1) Reset by ADB: -ip
            2) Reset by REST call first: -u + -p + -ip
        For KDP ibi:
            1) Reset by serail console: -ss-ip + -ss-port + -kdp
            1) Reset by SSH: -ip  -kdp # not test yet
        """)
    parser.add_argument('-u', '--username', help='Kamino user name', metavar='USERNAME', default=None)
    parser.add_argument('-p', '--password', help='Kamino password', metavar='PASSWORD', default=None)
    parser.add_argument('-env', '--cloud-env', help='Kamino cloud env type', metavar='ENV', default=None)
    parser.add_argument('-ip', '--ip', help='Destination UUT IP address', metavar='IP')
    parser.add_argument('-ss-ip', '--serial-server-ip', help='Destination serial server IP address', metavar='IP', default=None)
    parser.add_argument('-ss-port', '--serial-server-port', help='Destination UUT serial port', metavar='PORT', default=None)
    parser.add_argument('-nw', '--no-wait', help="Don't wait for device boot up", action='store_true', default=False)
    parser.add_argument('-wt', '--waiting-time', help='Max time to wait for booting up', type=int, metavar='TIME', default=300)
    parser.add_argument('-sif', '--success-if-resetted', help="Return success if resetted the device", action='store_true', default=False)
    parser.add_argument('-kdp', '--kdp', help="For KDP device", action='store_true', default=False)
    parser.add_argument('-ssh_user', '--ssh-user', help='The username of SSH server', default="root")
    parser.add_argument('-ssh_password', '--ssh-password', help='The password of SSH server', metavar='PWD', default="")
    parser.add_argument('-ssh_port', '--ssh-port', help='The port of SSH server', type=int, metavar='PORT', default=22)

    test = FactoryReset(parser.parse_args())
    try:
        test.main()
        sys.exit(0)
    except RuntimeError as e:
        test.log.error('End with exception: {}  Exit Code: {}'.format(e.__class__.__name__, e.exit_code))
        sys.exit(e.exit_code)
    except Exception as e:
        test.log(e, exc_info=True)
        sys.exit(10)
