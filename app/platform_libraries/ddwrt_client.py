# -*- coding: utf-8 -*-
""" Client libraries for DD-WRT based AP.
"""

__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"


# std modules
import time
# platform modules
import common_utils
from pyutils import retry
from ssh_client import SSHClient


def security_key_mapping(key):
    """
    WPA-PSK = WPA pre-shared key 
    WPA-EAP = WPA using EAP authentication
    IEEE8021X = IEEE 802.1X using EAP authentication and (optionally) dynamically generated WEP keys (WEP 802.1X)
    NONE = WPA is not used; plaintext or static WEP could be used 
    WPA-PSK-SHA256 = Like WPA-PSK but using stronger SHA256-based algorithms
    WPA-EAP-SHA256 = Like WPA-EAP but using stronger SHA256-based algorithms
    """
     # Not verify...
    return {
        'disabled': 'NONE',
        'psk': 'WPA-PSK',
        'psk2': 'WPA-PSK',
        'psk psk2': 'WPA-PSK',
        'wpa': 'WPA-EAP',
        'wpa2': 'WPA-EAP',
        'wpa wpa2': 'WPA-EAP',
        'radius': None, #??
        'wep': 'IEEE8021X'
    }.get(key)


class DDWRTClient(SSHClient):
    # Not support sudo command.
    def __init__(self, *args, **kwargs):
        super(DDWRTClient, self).__init__(*args, **kwargs)
        self.log = common_utils.create_logger(log_name='DDWRT_client', stream_log_level=kwargs.get('stream_log_level'))

    #
    # Basic Methods
    #
    def _response(self, command, stdin, stdout, stderr):
        stdin.close()
        output = str(stdout.read())
        error = str(stderr.read())
        if error:
            self.log.warning('Error: {}'.format(error))
        # Remove sudo message.
        output = self.linesep.join(line for line in output.split(self.linesep) if line not in self.remove_strings)
        self.log.debug('Response: {}'.format(output))
        return stdout.channel.recv_exit_status(), output.strip(), error.strip()

    def is_active(self):
        try:
            return self.client.get_transport().is_active()
        except:
            return False

    def __del__(self):
        if self.is_active():
            self.close()

    #
    # AP features
    #
    def security_key_mapping(self, key):
        return security_key_mapping(key)

    def show_nvram(self):
        return self.execute('nvram show')

    def get_nvram(self, name):
        return self.execute('nvram get {}'.format(name))
        
    def commit_nvram(self):
        return self.execute('nvram commit')

    def set_nvram(self, key, value):
        return self.execute('nvram set {}={}'.format(key, value))

    def set_nvram_with_apply(self, key, value, apply_it=True):
        self.set_nvram(key, value)
        self.commit_nvram()
        if apply_it:
            self.apply_setting()

    def apply_setting(self, apply_method=None):
        self.commit_nvram()
        if apply_method:
            return apply_method()
        return self.reboot_nas_service()

    def reboot_nas_service(self):
        self.execute('stopservice nas')
        self.wait_for_process_shutdown(name='nas')
        self.execute('startservice nas')
        self.wait_for_process_boot_up(name='nas')

    def check_process(self, name):
        grep_string = 'grep {}'.format(name)
        _, ret, _ = self.execute("ps | {0} | grep -v '{0}'".format(grep_string))
        if ret:
            return True
        return False

    def list_wifi_settings(self):
        self.log.info('Get AP settings...')
        s_2_4g = self.get_nvram('wl0_wds0')
        s_5g = self.get_nvram('wl1_wds0')
        return s_2_4g, s_5g

    def wait_for_process_boot_up(self, name, delay=5, max_retry=30):
        return retry(
            func=self.check_process, name=name,
            retry_lambda=lambda ret: not ret,
            excepts=(Exception), delay=delay, max_retry=max_retry, log=self.log.warning
        )

    def wait_for_process_shutdown(self, name, delay=5, max_retry=30):
        return not retry(
            func=self.check_process, name=name,
            retry_lambda=lambda ret: ret,
            excepts=(Exception), delay=delay, max_retry=max_retry, log=self.log.warning
        )
        
    def reboot(self, delay=10, max_retry=60):
        self.execute('reboot')
        self.wait_for_ap_shutdown(delay, max_retry)
        self.close()
        self.wait_for_ap_boot_up(delay, max_retry)
        self.connect()

    def wait_for_ap_boot_up(self, delay=10, max_retry=60):
        return retry(
            func=self.client.connect,
            hostname=self.hostname, username=self.username, password=self.password, port=self.port, timeout=5,
            excepts=(Exception), delay=delay, max_retry=max_retry, log=self.log.warning
        )

    def wait_for_ap_shutdown(self, delay=10, max_retry=60):
        return retry(
            func=self.is_active,
            retry_lambda=lambda ret: not ret,
            excepts=(Exception), delay=delay, max_retry=max_retry, log=self.log.warning
        )

    def disable_wan(self, time=60*5):
        # Backup plan: "WAN Connection Type" is Disable 
        # TODO: sometime "stopservice wan: may not work, but it work after "ifconfig vlan2 down".
        #self.execute('nohup ifconfig vlan2 down && nohup sleep {} && nohup ifconfig vlan2 up'.format(time))
        self.execute('nohup stopservice wan && nohup sleep {} && nohup startservice wan'.format(time))

    # Wireless features
    def set_2_4G_mode(self, mode, apply_it=True):
        """
        mode vs setting value:
            Disabled: "disabled"
            AP: "ap"
            Client: "sta"
            Client Bridge: "wet"
            ADhoc: "infra"
            Repeater: "apsta"
            Repeater Bridge: "apstawet"
        """
        self.set_nvram_with_apply(key='wl0_mode', value=mode, apply_it=apply_it)

    def set_5G_mode(self, mode, apply_it=True):
        self.set_nvram_with_apply(key='wl1_mode', value=mode, apply_it=apply_it)

    def set_2_4G_ssid(self, ssid, apply_it=True):
        self.set_nvram_with_apply(key='wl0_ssid', value=ssid, apply_it=apply_it)

    def set_5G_ssid(self, ssid, apply_it=True):
        self.set_nvram_with_apply(key='wl1_ssid', value=ssid, apply_it=apply_it)

    def set_2_4G_password(self, password, apply_it=True):
        self.set_nvram_with_apply(key='wl0_wpa_psk', value=password, apply_it=apply_it)

    def set_5G_password(self, password, apply_it=True):
        self.set_nvram_with_apply(key='wl1_wpa_psk', value=password, apply_it=apply_it)

    def set_2_4G_security_mode(self, security_mode, apply_it=True):
        """
        security mode vs setting value:
            Disabled: "disabled"
            WPA Personal: "psk"
            WPA Enterprise: "wpa"
            WPA2 Personal: "psk2"
            WPA2 Enterprise: "wpa2"
            WPA2 Personal Mixed: "psk psk2"
            WPA2 Enterprise Mixed: "wpa wpa2"
            Radius: "radius"
            WEP: "wep"
        """
        self.set_nvram(key='wl0_akm', value=security_mode) # May not need.
        self.set_nvram_with_apply(key='wl0_security_mode', value=security_mode, apply_it=apply_it)

    def set_5G_security_mode(self, security_mode, apply_it=True):
        """ security mode vs setting value: the same as 2.4G """
        self.set_nvram(key='wl1_akm', value=security_mode) # May not need.
        self.set_nvram_with_apply(key='wl1_security_mode', value=security_mode, apply_it=apply_it)

    # XXX: "disabled" not always available on AP.
    def set_2_4G_network_mode(self, network_mode, apply_it=True):
        """
        network mode vs setting value:
            Disabled: "disabled"
            Mixed: "mixed"
            BG-Mixed: "bg-mixed"
            B-Only: "b-only"
            G-Only: "g-only"
            NG-Mixed: "ng-only"
            N-Only: "n-only"
        """
        if network_mode == 'disabled':
            self.disable_action_service()
        else:
            self.enable_action_service()
        self.set_nvram_with_apply(key='wl0_net_mode', value=network_mode, apply_it=apply_it)

    def set_5G_network_mode(self, network_mode, apply_it=True):
        """ security mode vs setting value: the same as 2.4G """
        if network_mode == 'disabled':
            self.disable_action_service()
        else:
            self.enable_action_service()
        self.set_nvram_with_apply(key='wl1_net_mode', value=network_mode, apply_it=apply_it)

    def disable_action_service(self):
        # Disable Wi-Fi seem need it..., but both 2.4G & 5G will closed.
        # Need to more understatnd it.
        self.execute('nvram unset action_service')

    def enable_action_service(self):
        self.execute('nvram set action_service=wireless')

    def set_2_4G(self, ssid=None, password=None, security_mode=None, network_mode=None, apply_it=True):
        if ssid: self.set_2_4G_ssid(ssid, apply_it=False)
        if password: self.set_2_4G_password(password, apply_it=False)
        if security_mode: self.set_2_4G_security_mode(security_mode, apply_it=False)
        if network_mode: self.set_2_4G_network_mode(network_mode, apply_it=False)
        if apply_it:
            self.apply_setting()
        self.list_wifi_settings()

    def set_5G(self, ssid=None, password=None, security_mode=None, network_mode=None, apply_it=True):
        if ssid: self.set_5G_ssid(ssid, apply_it=False)
        if password: self.set_5G_password(password, apply_it=False)
        if security_mode: self.set_5G_security_mode(security_mode, apply_it=False)
        if network_mode: self.set_5G_security_mode(network_mode, apply_it=False)
        if apply_it:
            self.apply_setting()
        self.list_wifi_settings()

    def disable_network_interface(self, interface):
        self.execute('ifconfig {} down'.format(interface))

    def enable_network_interface(self, interface):
        self.execute('ifconfig {} up'.format(interface))

    def disable_2_4G_wifi(self):
        self.log.info('Disable 2.4G Wi-Fi')
        self.execute('ifconfig eth1 down')

    def enable_2_4G_wifi(self):
        self.log.info('Enable 2.4G Wi-Fi')
        self.execute('ifconfig eth1 up')

    def disable_5G_wifi(self):
        self.log.info('Disable 5G Wi-Fi')
        self.execute('ifconfig eth2 down')

    def enable_5G_wifi(self):
        self.log.info('Enable 5G Wi-Fi')
        self.execute('ifconfig eth2 up')
