# -*-coding: utf-8 -*-
"""  A client to control remote shielding box.
"""
# std modules
import time

# platform modules
import common_utils
from serial_client import SerialClient


class ShieldingBoxClient(SerialClient):

    def __init__(self, server_ip, uut_port, debug=False, daemon_msg=True, stream_log_level=None):
        super(ShieldingBoxClient, self).__init__(server_ip, uut_port, debug, daemon_msg, stream_log_level)
        self.logger = common_utils.create_logger(root_log='KAT.ShieldingBoxClient', stream_log_level=stream_log_level)

    def _retry_cmd(self, cmd, timeout=60*5, expect_ret_str=None):
        start = time.time()
        self.serial_read_all() # clean existing msg.
        while time.time() - start <= timeout:
            self.serial_write_bare(cmd+'\r')
            self.serial_readline() # read cmd line.
            ret = self.serial_readline() # read response.
            if 'Command Error' in ret:
                self.logger.info('Command is not correct. Try again...')
                continue
            elif 'TIMEOUT' in ret: # Wait for air pump.
                self.logger.info('Command timeour. Try again after 15s...')
                time.sleep(15)
            elif expect_ret_str and expect_ret_str not in ret:
                self.logger.info('Rsponse: {}. Try again...'.format(ret))
                continue
            return ret
        return None

    def open(self, timeout=60*5):
        self.logger.info('Open shielding box...')
        if self._retry_cmd('OPEN', timeout, 'OPEN READY') is None:
            return False
        return True

    def close(self, timeout=60*5):
        self.logger.info('Close shielding box...')
        if self._retry_cmd('CLOSE', timeout, 'CLOSE READY') is None:
            return False
        return True

    def status(self, timeout=30):
        """ Get status of box.
        Return: OPEN READY, CLOSE READY or None (cmd failed)
        """
        self.logger.info('Get status of shielding box...')
        return self._retry_cmd('STATUS', timeout)


if __name__ == '__main__':
    import argparse
    import sys
    # Arguments
    parser = argparse.ArgumentParser(description='Control remote shielding box')
    parser.add_argument('-ip', '--server-ip', help='Destination server IP', default='10.207.1.177')
    parser.add_argument('-port', '--serial-port', help='Serial port number', type=int, default='20001')
    parser.add_argument('-c', '--command', help='Command to control remote box', choices=['open', 'close', 'status'], required=True)
    args = parser.parse_args()

    sc = ShieldingBoxClient(server_ip=args.server_ip, uut_port=args.serial_port)
    sc.initialize_serial_port()
    try:
        ret = {
            'open': sc.open, 
            'close': sc.close, 
            'status': sc.status
        }.get(args.command)()
        if isinstance(ret, bool):
            sc.logger.info('Status: {}'.format(ret))
            if ret: sys.exit(0)
            sys.exit(1)
        else:
            sc.logger.info('Command Success: {}'.format(ret))
            if 'OPEN READY' in ret or 'CLOSE READY' in ret: sys.exit(0)
            sys.exit(1)
    finally:
        sc.close_serial_connection()
