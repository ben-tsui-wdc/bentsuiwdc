# -*- coding: utf-8 -*-
__author__ = "Ben Tsui <Ben.Tsui@wdc.com>"

# std modules
import sys
import paramiko

# platform modules
from middleware.arguments import GodzillaInputArgumentParser
from middleware.godzilla_test_case import GodzillaTestCase


class CheckProxyConnectedDuringDBMigration(GodzillaTestCase):

    TEST_SUITE = 'Godzilla Sanity'
    TEST_NAME = 'Check proxyConnect is true when migration in progress'
    # Popcorn
    PROJECT = 'Godzilla'
    TEST_TYPE = 'Functional'
    TEST_JIRA_ID = 'GZA-8924'
    PRIORITY = 'Major'
    COMPONENT = 'Platform'

    SETTINGS = {
        'uut_owner': True
    }

    def init(self):
        self.old_restsdk_toml_path = '/usr/local/modules/restsdk/etc/restsdk-server.toml'
        self.new_restsdk_toml_path = '/shares/Public/restsdk-server.toml'
        self.ssh_restsdk = paramiko.SSHClient()
        self.ssh_restsdk.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh_restsdk.connect(hostname=self.env.uut_ip, username=self.env.ssh_user,
                                 password=self.env.ssh_password, port=self.env.ssh_port)
        self.transport = self.ssh_restsdk.get_transport()
        self.channel_restsdk = self.transport.open_session()
        self.channel_restsdk.get_pty()
        self.channel_restsdk.set_combine_stderr(True)

    def before_test(self):
        self.ssh_client.delete_file_in_device(self.new_restsdk_toml_path)

    def test(self):
        self._clone_restsdk_toml()
        self._restart_restsdk_with_new_toml()
        self._check_db_migration_in_progress()
        self._check_device_info()
        self._stop_special_restsdk_service()
        self._restart_restsdk_with_original_toml()

    def after_test(self):
        self.ssh_client.delete_file_in_device(self.new_restsdk_toml_path)

    def _clone_restsdk_toml(self):
        self.log.info('Clone the RestSDK toml file to public share folder and update the db migration delay')
        self.ssh_client.execute_cmd('cp {0} {1}'.format(self.old_restsdk_toml_path, self.new_restsdk_toml_path))
        self.ssh_client.execute_cmd('printf "[test]\\nmigrationDelay = 80\\n" >> {}'.format(self.new_restsdk_toml_path))

    def _restart_restsdk_with_new_toml(self):
        self.log.info('Stop RestSDK service and restart with new toml file')
        self.ssh_client.stop_restsdk_service()
        cmd = "export LD_LIBRARY_PATH=/usr/local/modules/restsdk/restsdklib;" \
              "/usr/local/modules/restsdk/bin/restsdk-server -configPath {}".format(self.new_restsdk_toml_path)
        self.channel_restsdk.exec_command(cmd)  # command will never exit
        self.ssh_client.execute_cmd("ps | grep restsdk")

    def _check_db_migration_in_progress(self):
        self.log.info('Check if the device is in migration progress')
        device_info = self.ssh_client.get_device_info()
        if "key" in device_info and device_info.get('key') == "migrating":
            self.log.info("Device is simulating db migration as expected")
        else:
            raise self.err.TestFailure("Device is not simulating the db migration!")

    def _check_device_info(self):
        self.log.info('Verify if the RestSDK can return device id during db migration')
        device_id = self.ssh_client.get_device_info(fields='id')
        if not device_id:
            raise self.err.TestFailure('Failed to get RestSDK device id during db migration!')

        self.log.info("Verify if proxy is connected during db migration")
        proxy_connect = self.ssh_client.get_device_info(fields='network.proxyConnected')
        if not proxy_connect:
            raise self.err.TestFailure('Failed to get proxyConnectd info during db migration!')
        elif not proxy_connect.get('network').get('proxyConnected'):
            raise self.err.TestFailure('proxyConnectd is not True during db migration!')

    def _stop_special_restsdk_service(self):
        self.channel_restsdk.close()  # close channel and let remote side terminate the process

    def _restart_restsdk_with_original_toml(self):
        self.log.info("Restart RestSDK service with default toml file after testing")
        self.ssh_client.stop_restsdk_service()
        self.ssh_client.start_restsdk_service()


if __name__ == '__main__':
    parser = GodzillaInputArgumentParser(""" \
        *** Add Public Share And Check Samba RW on Godzilla devices ***
        Examples: ./run.sh godzilla_scripts/functional_tests/check_proxy_connected_during_db_migration.py 
        --uut_ip 10.136.137.159 -env qa1 \
        """)
    test = CheckProxyConnectedDuringDBMigration(parser)
    resp = test.main()
    if resp:
        sys.exit(0)
    sys.exit(1)
