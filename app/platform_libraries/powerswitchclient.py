import threading
import socket
import time
import common_utils
import sys
from dlipower import dlipower
from pyutils import retry


class PowerSwitchClient(object):

    def __init__(self, power_switch_ip, username='admin', password='1234', cycle_time=3, retry_counts=5, stream_log_level=None):
        self.log = common_utils.create_logger('KAT.powerswitchclient', stream_log_level=stream_log_level)
        self.power_switch_ip = power_switch_ip
        self.username = username
        self.password = password
        self.power_cycle_time = cycle_time
        # self.power_lock = threading.RLock()
        self.retry_counts = retry_counts

    def _power_command(self, power_switch_port=None, command=None, cycle_time=None):
        """
        Run the specified web power switch command.
        """
        if cycle_time is None:
            cycle_time = self.power_cycle_time

        #self.power_lock.acquire()
        try:
            retry = 0
            while True:
                try:
                    self.log.debug('Sending: "{0}" to port {1} on power switch: {2}'.
                                   format(command, power_switch_port, self.power_switch_ip))
                    power_switch = dlipower.PowerSwitch(cycletime=cycle_time,
                                                        hostname=self.power_switch_ip,
                                                        userid=self.username, password=self.password)
                    if power_switch_port:
                        return power_switch.command_on_outlets(command=command, outlets=[power_switch_port])
                    elif command == 'statuslist':
                        return power_switch.statuslist()
                    break
                except (socket.timeout, socket.error):
                    retry += 1
                    if retry >= self.retry_counts:
                        self.log.debug('Reach maximum retries: {}'.format(self.retry_counts))
                        raise
                    else:
                        self.log.debug('Retrying to connect power switch, {} times remaining...'.
                                       format(self.retry_counts - int(retry)))
                        pass
        except AttributeError:
            self.log.error('No power switch info found for this test unit')
        except Exception as e:
            self.log.error('Send power command failed. Error message:{}'.format(repr(e)))
        finally:
            time.sleep(5)
            #self.power_lock.release()

        self.log.debug('Finished cmd: "{0}" to port {1} on power switch {2}'.
                       format(command, power_switch_port, self.power_switch_ip))

    def power_cycle(self, power_switch_port, cycle_time=None):
        """Power cycle the given power switch IP and port"""
        self.log.info('Power cycle port: {}'.format(power_switch_port))
        self._power_command(power_switch_port, command='cycle', cycle_time=cycle_time)

    def power_on(self, power_switch_port):
        """Power on the a given power switch IP and port"""
        self.log.info('Power on port: {}'.format(power_switch_port))
        retry(
            func=self._power_command, power_switch_port=power_switch_port, command='on',
            excepts=(Exception), retry_lambda=lambda _: self.outlet_status(power_switch_port) != 'ON',
            delay=5, max_retry=12, log=self.log.warning
        )

    def power_off(self, power_switch_port):
        """ Turn off a power to an outlet. False = success, True = Fail """
        self.log.info('Power off port: {}'.format(power_switch_port))
        retry(
            func=self._power_command, power_switch_port=power_switch_port, command='off',
            excepts=(Exception), retry_lambda=lambda _: self.outlet_status(power_switch_port) != 'OFF',
            delay=5, max_retry=12, log=self.log.warning
        )

    def outlet_status(self, power_switch_port):
        """ Return the status of an outlet, returned value will be one of: ON,  OFF, Unknown """
        resp = self._power_command(power_switch_port, command='status')
        self.log.debug('Status: {}'.format(resp))
        if not resp:
            return None
        return resp.pop()

    def outlet_status_list(self):
        """ Return the status of all outlets in a list """
        return self._power_command(command='statuslist')

if __name__ == '__main__':
    print "### Running as a script, so running this code as a test ###\n"
    if len(sys.argv) < 2:
        print 'Please input the Power Switch IP Address. ex. python powerswitchclient.py 10.136.139.14'
        sys.exit(1)

    ps = PowerSwitchClient(sys.argv[1])
    print ps.outlet_status_list()
    print ps.outlet_status(4)
    # ps.power_off(4)
    # ps.power_on(4)
    # ps.power_cycle(4)
