# -*- coding: utf-8 -*-
""" Test Utils for KDP
"""
__author__ = "Estvan Huang <Estvan.Haung@wdc.com>"

# platform modules
from platform_libraries.nasadmin_client import NasAdminClient
from platform_libraries.restAPI import RestAPI
from platform_libraries.pyutils import retry


def reset_device(inst, wait_for_nasAdmin_ready=True):
    inst.log.info("Resetting device")
    inst.uut_owner.factory_reset()
    wait_for_device_reboot_completed(inst, wait_for_nasAdmin_ready)

def wait_for_device_reboot_completed(inst, wait_for_nasAdmin_ready=True):
    if not inst.ssh_client.wait_for_device_to_shutdown():
        raise inst.err.TestFailure('Device was not shut down successfully!')
    if inst.serial_client:
        inst.serial_client.wait_for_boot_complete_kdp()
        if 'yoda' in inst.uut['model']:
            if not connect_wifi(inst):
                raise inst.err.TestFailure('Failed to set WiFi')
        else:
            inst.env.check_ip_change_by_console()
    if not inst.ssh_client.wait_for_device_boot_completed():
        raise inst.err.TestFailure('Device was not boot up successfully!')
    inst.log.warning("Reset device is completed")
    if wait_for_nasAdmin_ready:
        inst.nasadmin.wait_for_nasAdmin_works()

def attach_user(inst):
    inst.log.info("Attaching user")
    inst.uut_owner.init_session(client_settings={'config_url': inst.uut['config_url']})
    inst.log.info("User attachment is completed")

def attach_2nd_user(inst, username, password, log_name=None, init_session=True):
    inst.log.info('Generating RestSDK client for 2nd user')
    rest_2nd = RestAPI(
        uut_ip=inst.env.uut_ip, env=inst.env.cloud_env, username=username,
        password=password, log_name=log_name, init_session=False,
        stream_log_level=inst.env.stream_log_level)
    rest_2nd.update_device_ip(inst.env.uut_ip)
    if init_session:
        if inst.env.cloud_env == 'prod':
            with_cloud_connected = False
        else:
            with_cloud_connected = True
        rest_2nd.init_session(
            client_settings={'config_url': inst.uut['config_url']}, with_cloud_connected=with_cloud_connected)
    return rest_2nd

def gen_nasAdmin_client(
        inst, rest_client=None, local_name="owner", local_password="password", log_name=None, uac_limiter=None):
    inst.log.info('Generating nasAdmin client')
    if not rest_client:
        rest_client = inst.uut_owner
    return NasAdminClient(
        ip=inst.env.uut_ip, rest_client=rest_client,
        local_name=local_name, local_password=local_password,
        log_name=log_name, stream_log_level=inst.env.stream_log_level,
        uac_limiter=uac_limiter
    )

def connect_wifi(inst):
    inst.log.info('Connecting device to WiF')
    if inst.serial_client:
        if inst.env.ap_ssid and inst.env.ap_password:
            inst.serial_client.retry_for_connect_WiFi_kdp(ssid=inst.env.ap_ssid, password=inst.env.ap_password)
            inst.env.check_ip_change_by_console()
            return True
        else:
            inst.log.warning('No ap_ssid or ap_password is provided')
            return False
    else:
        inst.log.warning('No serial_client exist')
        return False

def init_session_for_2nd_user(inst, user_2nd_inst):
    """ This util is for saving time of attaching 2nd users in massive user case.
    """
    user_2nd_inst.init_variables()
    user_2nd_inst.uut_ip = inst.uut_owner.uut_ip
    user_2nd_inst.port = inst.uut_owner.port
    user_2nd_inst.url_prefix = inst.uut_owner.url_prefix
    #  check user account
    get_user = user_2nd_inst.cloud.get_user_info_from_cloud(email=user_2nd_inst.username)
    if not get_user:
        user_2nd_inst.create_user(user_2nd_inst.username, user_2nd_inst.password)
    else:
        user_2nd_inst.log.debug('User: {0} exist, user info:{1}'.format(user_2nd_inst.username, get_user))
    if user_2nd_inst.retry_attach_user:  # retry 20 times.
        retry(func=user_2nd_inst.attach_user_to_device, delay=10, max_retry=20, log=user_2nd_inst.log.warning)
    else:
        user_2nd_inst.attach_user_to_device()
