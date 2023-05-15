# -*-coding: utf-8 -*-
""" Serial server client (telnetlib wrapper).

# Porting to Kamino and update features on Nov 23, 2017
# @author: Estvan Huang
"""
# std modules
import Queue
import socket
import sys
import telnetlib
import thread
import threading
import time
import re
import hashlib
# platform modules
import common_utils
from pyutils import decode_unicode_args, replace_escape_sequence, retry


serial_lock = threading.RLock()
lock_log = common_utils.create_logger(root_log='KAT.serial_lock')


def disable_daemon_logs(method):
    def wrapper(*args, **kwargs):
        self = args[0]
        org_flag = self.daemon_msg
        self.daemon_msg = False
        try:
            return method(*args, **kwargs)
        finally:
            self.daemon_msg = org_flag
    return wrapper

def pure_output_msg(method):
    def wrapper(*args, **kwargs):
        self = args[0]
        org_flag = self.daemon_msg
        self.pure_msg = True
        try:
            return method(*args, **kwargs)
        finally:
            self.pure_msg = org_flag
    return wrapper

def synchronize(func):
    def _synchronize(*args, **kwargs):
        try:
            #lock_log.debug('self:{} thead: {}| acquire'.format(args[0], threading.current_thread()))
            serial_lock.acquire()
            return func(*args, **kwargs)
        finally:
            serial_lock.release()
            #lock_log.debug('self:{} thead: {}| released'.format(args[0], threading.current_thread()))
    return _synchronize

def atomic(func):
    # Only protect for high level serail access.
    # It could make sure all the row data are complete (not interrupt by write) during method read, but not protect the data out of method read.
    def _atomic(*args, **kwargs):
        self = args[0]
        try:
            #lock_log.critical('thead: {}| atomic acquire'.format(threading.current_thread()))
            if self._atomic_lock: self._atomic_lock.acquire()
            return func(*args, **kwargs)
        finally:
            if self._atomic_lock: self._atomic_lock.release()
            #lock_log.critical('thead: {}| atomic released'.format(threading.current_thread()))
    return _atomic


class SerialClient(object):
    """
    This library wraps Python's telnetlib to provide access to a test unit's
    serial port via a serial server that forwards serial ports to telnet ports.
    """

    def __init__(self, server_ip, uut_port, debug=False, daemon_msg=True, stream_log_level=None,
                 device_type=None, password=None):
        self.server_ip = server_ip
        self.uut_port = uut_port
        self.debug = debug
        self.daemon_msg = daemon_msg
        # To do something for output msg or not.
        self.pure_msg = False

        self.common = None
        self.input_queue = Queue.Queue() # Queue to save debug message, and these message only created by our logic.
        self.logger = common_utils.create_logger(root_log='KAT.serialclient', stream_log_level=stream_log_level)
        self.logging_thread = None
        self.read_queue = None # Queue to save serial message from console.
        self.serial = None
        # thread lock used for telling serial reader thread to stop
        self.serial_connected = thread.allocate_lock()
        # Lock for atomic access.
        self._atomic_lock = threading.Lock()
        # priority to get device ip
        self.priority_wlan_first()
        # Reset command line
        self.device_type = device_type
        self.pre_password = None  # keep pre-password in case of it is changed
        self.password = password if password else ''
        # cmds
        self.end_cmd = '; PRE=FINI && echo "$PRE"SHED'
        self.exit_code_cmd = '; EXITCODE=$?'

    def error(self, msg, raise_error=True):
        if raise_error:
            raise RuntimeError(msg)
        self.logger.error(msg)

    def initialize_serial_port(self):
        if self.server_ip and self.uut_port:
            self.logger.debug('Initializing SerialPortLibrary')
            try:
                self._start_logging()
            except Exception as e:
                if 'Connection refused' in str(e):
                    self.logger.warning(
                        'Connection refused to serial port: {0}:{1}'.format(self.server_ip, self.uut_port))
                raise

    @synchronize
    def _connect(self):
        """Connect to the serial port (if it exists)."""
        # don't open up a new connection if we're not supposed to be connected
        if not self.serial_connected.locked():
            self.logger.warning('Tried to open serial connection but serial lock not acquired')
            return
        if self.serial:
            try:
                self.logger.debug('Open serial connection, but found existing connection, now close it...')
                self.serial.close()
            except Exception as e:
                self.logger.warning('Error closing serial port: {0}'.format(e))
        self.logger.debug('Connecting to serial server {0} port: {1}'.format(self.server_ip, self.uut_port))
        self.serial = telnetlib.Telnet(self.server_ip, self.uut_port, timeout=10)
        if self.debug: self.serial.set_debuglevel(1)
        self.check_connection_available()
        if not self.read_queue:
            self.read_queue = Queue.Queue()

    @synchronize
    def check_connection_available(self, raise_error=True):
        """ Chech connection with sending something harmless.
        """
        try:
            if not self.serial:
                raise RuntimeError('No telnetlib isntance')
            if not self.serial.sock:
                raise RuntimeError('No sock isntance')
            # Test connection
            # Here we duplicate and sleep are for case when we call this function immediately after establish connection,
            # which it will return succes somehow...
            self.serial.sock.send(telnetlib.IAC + telnetlib.NOP)
            time.sleep(0.5)
            self.serial.sock.send(telnetlib.IAC + telnetlib.NOP)
            time.sleep(0.5)
            self.serial.sock.send(telnetlib.IAC + telnetlib.NOP)
            return True
        except:
            self.logger.warning('No serial connection')
            if not raise_error:
                return False
            raise

    @synchronize
    def init_read_queue(self):
        self.logger.debug('Clean read queue.')
        self.read_queue = Queue.Queue()

    @synchronize
    def close_serial_connection(self):
        """
        Closes the serial connection
        """
        if self.serial_connected.locked():
            # release the lock so that the reader thread can stop
            self.logger.debug('Serial lock released.')
            self.serial_connected.release()
        if self.serial is not None:
            self.logger.debug('Closing serial connection...')
            self.serial.close()
            self.serial = None 
            self.read_queue = None
        if self.logging_thread:
            self.logger.debug('Waiting 60s for daemon exit...')
            self.logging_thread.join(timeout=60)

    def serial_is_connected(self, reset_command_line=False):
        """Returns True if the serial port is connected."""
        if self.serial is not None:
            if reset_command_line:
                self.reset_command_line()
            self.logger.debug('Connected to serial port: {0}'.format(self.server_ip, self.uut_port))
        else:
            self.logger.debug(
                'serial_server_ip={0}'.format(self.server_ip, self.uut_port))
            self.logger.warning('Serial port not connected.')
            import gc

            for obj in gc.get_objects():
                if isinstance(obj, SerialClient):
                    self.logger.debug('Instance of SerialClient: {0}'.format(obj))
        return self.serial is not None

    @synchronize
    def start_serial_port(self):
        """
        Starts the serial port, does nothing if it's already started
        """
        if self.serial is not None:
            self.logger.debug('Serial port is already started')
        elif not self.serial_connected.locked():
            self._start_logging()
        else:
            self.logger.debug('Serial lock acquired, release lock and wait 30s for closing daemon...')
            self.serial_connected.release()
            time.sleep(30)
            self._start_logging()

    @synchronize
    def _start_logging(self):
        """Set up a logger."""
        if not self.serial_connected.locked():
            self.logger.debug('Starting serial port logger.')

            # acquire the serial_connected lock so that the thread won't stop
            self.serial_connected.acquire()
            self.logger.debug('Serial lock acquired.')
            self._connect() # Connect here instead of by daemon, because the caller may invoke method before daemon connect. 
            self.logging_thread = threading.Thread(target=self._log_serial_messages)
            self.logging_thread.daemon = True
            self.logging_thread.start()
            self.reset_command_line()
        else:
            self.logger.debug('Starting serial port logger but serial lock not acquired.')

    def send_and_get_first_line(self, cmd, timeout=20):
        self.serial_write(cmd)
        try:
            self.serial_readline(3)  # consume sent cmd
            return self.serial_readline(timeout)
        except Exception as e:
            self.logger.warning('Waiting cmd response timeout')
            return ''

    def reset_command_line_kdp(self, timeout=60*2):
        self.serial_read_all()
        start = time.time()
        while time.time() - start < timeout:
            line = self.send_and_get_first_line('\x03')  # send ^c
            if line.startswith('root@') and line.endswith(' #'):  # normal line
                return
            elif line == '>':  # resolve unfinished string
                self.serial_read_all()
                line = self.send_and_get_first_line('"')  # finish string by "
                if line == '>':
                    self.send_and_get_first_line("'")  # finish string by '
                self.serial_read_all(3)
            else:  # trying to enter password
                if self.serial_wait_for_filter_string("Please press Enter", timeout=15):
                    self.serial_write("")
                    if self.serial_wait_for_filter_string("Password:", timeout=20):
                        self.serial_write(self.password)
                    self.serial_read_all(3)

    def reset_command_line_default(self):
        # for skip login or other broken cmd
        self.serial_write("")
        time.sleep(1)
        self.serial_write("")
        time.sleep(1)
        self.serial_write('\x03') # ^c
        # sometimes device slow on landing to login.
        if self.serial_wait_for_filter_string("'/bin/login'", timeout=15):
            self.serial_wait_for_filter_string("Password:", timeout=20)
        self.serial_write("")

    def generate_password(self, mac, serial):
        self.pre_password = self.password
        self.password = hashlib.sha256(mac + serial).hexdigest()[24: 40]
        self.logger.info('Console password changed from {} to {} in func "generate_password".'.format(self.pre_password, self.password))

    def use_pre_password(self):
        temp = self.pre_password
        self.pre_password = self.password
        self.password = temp
        self.logger.info('Console password changed from {} to {} in func "use_pre_password".'.format(self.pre_password, self.password))

    def reset_command_line(self):
        if self.device_type and 'kdp' in self.device_type:
            self.reset_command_line_kdp()
        else:
            self.reset_command_line_default()

    def _log_serial_messages(self):
        """Loop that runs inside self.logging_thread.

        Output string is split by "\n", each string is regarded as one single line.
        """
        def put_in_read_queue(msg):
            if data:
                if self.daemon_msg: self.logger.debug('READ SERIAL (Daemon): {0}'.format(data))
                self.read_queue.put(data, timeout=10)

        def get_msg_from_console():
            """ Read meesage from console and hanlde any exception case. """
            line = self.serial.read_until('\n', timeout=5)
            if not line:
                return line

            if self.pure_msg:
                return line

            # Filter out mssage like "[  270.971988] audit: rate limit exceeded"
            matched_strs = re.findall(r'\[[\t\s]*\d*.\d*\] [\S\s]*', line)
            if not matched_strs:
                return line
            # Remove exit code and remove BASH prompt string by the following fixed strings.
            # e.g. "255|root@yodaplus32_mini:/ # [   60.010688] type=1400 audit(1388534"
            cleaned_str = re.sub(r'\d+?\|', '', line).replace('root@yodaplus32_mini:/ #', ''). \
                replace('root@yoda32_mini:/ #', '').replace('root@monarch32_mini:/ #', ''). \
                replace('root@pelican32_mini:/ #', '').replace('/ #', '')
            # Check output string is break or not.
            if re.findall(r'^[\t\s]*\[[\t\s]*\d*.\d*\] [\S\s]*', cleaned_str): # Not break anything.
                return line
            # Now we consider the line is broken by a syslog, and we try to recover it.
            syslog = matched_strs[0]
            line_head_part = line.replace(syslog, '') # Broken head part.
            line_tail_part = self.serial.read_until('\n', timeout=5) # Broken tail part.
            self.logger.warning('Recover broken string from:')
            self.logger.warning(line)
            self.logger.warning('To:')
            if re.findall(r'\[[\t\s]*\d*.\d*\] [\S\s]*', line_tail_part):
                # The next line is syslog, that means this log not at middle of line. e.g.:
                # from "RX bytes:6346 TX bytes:6346 [   60.010688] type=1400 audit(1388534" 
                #      "[   64.393722] init: no such service 'bootanim'" 
                #  to  "RX bytes:6346 TX bytes:6346 "
                #      "[   60.010688] type=1400 audit(1388534"
                #      "[   64.393722] init: no such service 'bootanim'" 
                put_in_read_queue(line_head_part)
                put_in_read_queue(syslog)
                put_in_read_queue(line_tail_part)
                self.logger.warning(line_head_part)
                self.logger.warning(syslog)
                self.logger.warning(line_tail_part)
            else: # Recover messages. e.g.:
                # from "configURL = "https://qa[   60.010688] type=1400 audit(1388534" 
                #      "1.wdtest1.com"" 
                #  to  "configURL = "https://qa1.wdtest1.com"" 
                #      "[   60.010688] type=1400 audit(1388534"
                line = line_head_part + line_tail_part
                put_in_read_queue(line)
                put_in_read_queue(syslog)
                self.logger.warning(line)
                self.logger.warning(syslog)
            return ''

        self.logger.debug('Daemon started.')
        data = ''
        while self.serial_connected.locked():
            while not self.input_queue.empty():
                self.logger.debug(str(self.input_queue.get()))
            sys.stdout.flush()
            # if the lock is no longer locked, stop looping
            if not self.serial_connected.locked():
                self.logger.debug('Serial port logging thread exiting')
                return
            if not self.serial:
                self._connect()
            try:
                #print 'Wait for READ!'
                data = replace_escape_sequence(get_msg_from_console())
                #data = data.replace('\n', '\r\n') # Why Need this???
                put_in_read_queue(msg=data)
                #print 'GO Next READ!'
            except Exception as e:
                if self.serial_connected.locked():
                    self.logger.warning(
                        'Error reading from serial port: {0} at {1}'.format(str(e), time.asctime()), exc_info=True)
                    self.logger.debug('Reopening serial connection')
                    self._connect()
                else:
                    self.logger.debug('serial port logging thread exiting')
                    return
        self.logger.debug('Serial port logging thread exiting since exit the loop.')

    def serial_debug(self, msg):
        """
        Places a given message into the input queue
        """
        self.input_queue.put(msg)

    @synchronize
    @atomic
    def serial_read_all(self, time_for_read=1, debug_logs=True):
        """
        Reads everything from the read queue (Can read for a while)
        """
        if not self.read_queue:
            self.error('Cannot read all from serial port, serial port not connected')

        output = []
        # Wait few seconds to waiting for daemon read message into read_queue.
        start = time.time()
        while self.read_queue.empty() and (time.time() - start < time_for_read):
            time.sleep(1)

        while not self.read_queue.empty():
            out = self.read_queue.get()
            if debug_logs: self.logger.debug('READ SERIAL: {0}'.format(out))
            output.append(out)
        return output

    @synchronize
    @atomic
    def serial_read(self, timeout=None):
        """Return a chunk of data from the serial port.
        Notes: This is also read line.
        """
        if not self.read_queue:
            self.error('Cannot read from serial port, serial port not connected')

        output = self.read_queue.get(timeout=timeout)
        self.logger.debug('READ SERIAL: {0}'.format(output))
        return output

    def serial_readline(self, timeout=None):
        """Return a line from the serial port."""
        return self.serial_read(timeout)

    @synchronize
    def serial_write(self, buff, timeout=20, raise_error=True):
        """Write to the serial port and append a newline."""
        self.serial_write_bare('{0}\n'.format(buff), timeout, raise_error)

    @synchronize
    def serial_cmd(self, cmd, timeout=20, raise_error=True, wait_response=True, return_type='str', exit_code=True):
        # Separate string for avoid to find wrong line.
        self.serial_write(
            '{}{}{}'.format(cmd, self.exit_code_cmd if exit_code else '', self.end_cmd), timeout, raise_error)
        if wait_response:
            if return_type == 'str':
                return self.serial_wait_for_string_and_return_string('FINISHED', timeout=timeout)
            else:
                return self.serial_wait_for_string_and_return_list('FINISHED', timeout=timeout)

    def serial_cmd_and_get_resp(self, cmd, timeout=20, raise_error=True, return_type='str', exit_code=True):
        """ Send a command and return its response. """
        resp = self.serial_cmd(
            cmd=cmd, timeout=timeout, raise_error=raise_error, wait_response=True, return_type=return_type, exit_code=exit_code)
        if return_type == 'str':
            return resp[resp.find('"SHED')+6: resp.find('FINISHED')-1]
        else:
            cmd_end_dix = 0
            for idx, s in enumerate(resp):
                if s.endswith('"SHED'):
                    cmd_end_dix = idx
                    break
            return resp[cmd_end_dix+1: -1]

    def get_exit_code(self):
        output = self.serial_cmd_and_get_resp('echo $EXITCODE', exit_code=False)
        if output:
            return int(output.strip())

    @synchronize
    @atomic
    @decode_unicode_args
    def serial_write_bare(self, buff, timeout=20, raise_error=True):
        """Write to the serial port."""
        start = time.time()
        while self.serial:
            if time.time() - start > timeout:
                self.error('Write "{}" timeout {}s'.format(buff, timeout), raise_error)
                return
            try:
                self.logger.debug('WRITE SERIAL: {}'.format(buff))
                self.serial.write(buff)
                return
            except socket.error:
                self._connect()
            time.sleep(1)
        self.error('Cannot write "{0}" to serial port, serial port not connected'.format(buff), raise_error)

    @synchronize
    @decode_unicode_args
    def serial_wait_for_string_and_return_list(self, string, timeout=5, raise_error=True):
        """Wait for the given string and return all message in list or for the timeout (in seconds, default 5)."""
        if not self.read_queue:
            self.error('Cannot wait for "{0}" from serial port, serial port not connected'.format(string))

        self.logger.debug('Waiting for string: {0}'.format(string))
        if not string:
            return self.serial_read()
        output = []
        start = time.time()
        while True:
            buff = None
            if time.time() - start > timeout:
                self.error('Wait for string "{}" timeout {}s'.format(string, timeout), raise_error)
                return [] # We may return output here.
            try:
                buff = self.read_queue.get(timeout=5)
            except Queue.Empty:
                time.sleep(1)
            if not buff:
                continue
            output.append(buff)
            if string in buff:
                return output

    def serial_wait_for_string_and_return_string(self, string, sep='\n', timeout=5, raise_error=True):
        """Wait for the given string and return all message in a string or for the timeout (in seconds, default 5)."""
        output = self.serial_wait_for_string_and_return_list(string, timeout, raise_error)
        if not output:
            return None
        return sep.join(output)

    def serial_wait_for_string(self, string, timeout=5, raise_error=True):
        """Wait for the given string and return the first message containing this string or for the timeout (in seconds, default 5)."""
        output = self.serial_wait_for_string_and_return_list(string, timeout, raise_error)
        if not output:
            return None
        return output[-1]

    def _serial_filter_read_for_seconds(self, re_pattern, timeout_for_each_read=1, time_for_read=20):
        """ Read output for time_for_read seconds and filter out all console string. """
        start = time.time()
        while time.time() - start < time_for_read:
            try:
                line = self.serial_readline(timeout_for_each_read)
                if line:
                    if re.findall(re_pattern, line):
                        yield line
                    else:
                        yield None # Treat as a ignored message.
            except Queue.Empty:
                pass

    def serial_wait_for_filter_string(self, re_pattern, timeout=5):
        """ Wait for the first matched string or for the timeout. """
        for msg in self._serial_filter_read_for_seconds(re_pattern, 1, timeout):
            if msg:
                return msg
        return None

    def serial_filter_read(self, re_pattern, timeout_for_each_read=10, time_for_read=20):
        """ Read all matched string and read until to the next string is not matched. """
        output = []
        for msg in self._serial_filter_read_for_seconds(re_pattern, timeout_for_each_read, time_for_read):
            if not msg:
                return output
            output.append(msg)
        return output

    def serial_filter_read_least_one(self, re_pattern, timeout_for_each_read=10, time_for_read=20):
        """ Read a least one matched string and read until to the next string is not matched. """
        output = []
        for msg in self._serial_filter_read_for_seconds(re_pattern, timeout_for_each_read, time_for_read):
            if not msg:
                if not output:
                    continue
                return output
            output.append(msg)
        return output

    def serial_filter_read_all(self, re_pattern, timeout_for_each_read=1, time_for_read=20):
        """ Read output for time_for_read seconds and filter out result. """
        return [msg for msg in self._serial_filter_read_for_seconds(re_pattern, timeout_for_each_read, time_for_read) if msg]

    #
    # Yoda Feature Area
    #
    def turn_ap_mode_off(self, timeout=60, raise_error=True):
        self.logger.info('Switch to client mode...')
        self.serial_write('am broadcast -a android.intent.action.FACTORY_CMD --es cmd ap_off', timeout, raise_error)
        self.serial_wait_for_string('Broadcast completed: result=0', timeout, raise_error)

    def scan_wifi_ap(self, list_network=False, timeout=60, raise_error=True):
        self.logger.info('Scan WiFi AP...')
        # Will resend command if we got 'FAIL-BUSY'.
        start = time.time()
        while time.time() - start < timeout:
            self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets scan', timeout, raise_error)
            output = self.serial_wait_for_filter_string(re_pattern='OK|FAIL-BUSY', timeout=timeout)
            if output and 'OK' in output:
                break
            time.sleep(3)
        if list_network:
            time.sleep(0.5)
            self.list_wifi_ap()

    def list_wifi_ap(self, filter_keyword=None, wait_timeout=5, raise_error=True):
        self.logger.info('List WiFi AP...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets scan_results', wait_timeout, raise_error)
        self.serial_wait_for_string('bssid / frequency / signal level / flags / ssid', wait_timeout, raise_error)
        ap_list = self.serial_filter_read_all(re_pattern=r'(?:[0-9a-fA-F]:?){12}', time_for_read=wait_timeout)
        if filter_keyword:
            return [ap for ap in ap_list if filter_keyword in ap]
        return ap_list

    def add_wifi(self, ssid, password, security_mode='WPA-PSK', enable_wifi=True, restart_wifi=True, connect_wifi=True, raise_error=True):
        network_id = self.add_network(raise_error)
        time.sleep(0.5)
        self.set_network_ssid(network_id, ssid, raise_error=raise_error)
        time.sleep(0.5)
        self.set_network_security_mode(network_id, security_mode, raise_error=raise_error)
        time.sleep(0.5)
        self.set_network_password(network_id, password, raise_error=raise_error)
        time.sleep(0.5)
        self.save_network_config(raise_error=raise_error)
        time.sleep(0.5)
        if enable_wifi: self.enable_network(network_id, raise_error=raise_error)
        if connect_wifi: self.connect_network(network_id, raise_error=raise_error)
        if enable_wifi and connect_wifi:
            self.save_network_config(raise_error=raise_error)
        if restart_wifi: self.restart_wifi()
        return network_id

    def add_network(self, timeout=30, raise_error=True):
        self.logger.info('Add network...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets add_network', timeout, raise_error)
        output = self.serial_wait_for_filter_string(re_pattern=r'^\d')
        if not output:
            self.error('Return an unknown network ID: {0}'.format(output), raise_error)
            return None
        return output

    def set_network_ssid(self, network_id, ssid, timeout=30, raise_error=True):
        self.logger.info('Set network ssid...')
        self.serial_write(r"""wpa_cli -i wlan0 -p /data/misc/wifi/sockets set_network {0} ssid '"{1}"'""".format(
            network_id, ssid), timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def set_network_security_mode(self, network_id, security_mode='WPA-PSK', timeout=30, raise_error=True):
        self.logger.info('Set network security_mode...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets set_network {0} key_mgmt {1}'.format(
            network_id, security_mode), timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def set_network_password(self, network_id, password, mode='psk', timeout=30, raise_error=True):
        self.logger.info('Set network password...')
        self.serial_write(r"""wpa_cli -i wlan0 -p /data/misc/wifi/sockets set_network {0} {1} '"{2}"'""".format(
            network_id, mode, password), timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def save_network_config(self, timeout=30, raise_error=True):
        self.logger.info('Save network config...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets save_config', timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def enable_network(self, network_id, timeout=30, raise_error=True):
        self.logger.info('Enable network...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets enable_network {}'.format(network_id), timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def disable_network(self, network_id, timeout=30, raise_error=True):
        self.logger.info('Disable network...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets disable_network {}'.format(network_id), timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def enable_wifi(self, wifi_interface='wlan0', timeout=60, raise_error=True):
        self.logger.info('Enable WiFi interface...')
        self.serial_write('svc wifi enable', timeout, raise_error)
        time.sleep(3) # Wait few seconds for decreasing retry.
        retry(
            func=self.serial_write, buff='ifconfig {}'.format(wifi_interface), timeout=timeout, raise_error=raise_error,
            retry_lambda=lambda _: not self.serial_wait_for_string('{}     Link '.format(wifi_interface), 1, raise_error),
            delay=1, max_retry=30, log=self.logger.warning
        )
        self.serial_read_all() # Make sure console is clear.

    def disable_wifi(self, wifi_interface='wlan0', timeout=60, raise_error=True):
        self.logger.info('Disable WiFi interface...')
        self.serial_write('svc wifi disable', timeout, raise_error)
        time.sleep(3) # Wait few seconds for decreasing retry.
        retry(
            func=self.serial_write, buff='ifconfig {}'.format(wifi_interface), timeout=timeout, raise_error=raise_error,
            retry_lambda=lambda _: not self.serial_wait_for_string('No such device', 1, raise_error),
            delay=1, max_retry=30, log=self.logger.warning
        )

    def restart_wifi(self, wifi_interface='wlan0', timeout=60, raise_error=True):
        self.disable_wifi(wifi_interface, timeout, raise_error)
        self.enable_wifi(wifi_interface, timeout, raise_error)

    def connect_network(self, network_id, timeout=60, raise_error=True):
        self.logger.info('Connect to network...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets select_network {}'.format(network_id), timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def list_network(self, filter_keyword=None, split_it=False, wait_timeout=60, read_timeout=5, raise_error=True, retry_times=10):
        ### Addrional fixes for list network may no reponse sometimes.
        if retry_times:
            return retry( # Only for timeout.
                func=self.list_network,
                filter_keyword=filter_keyword, split_it=split_it, wait_timeout=wait_timeout, read_timeout=read_timeout, raise_error=raise_error, retry_times=None,
                delay=10, max_retry=retry_times, log=self.logger.warning
            )
        ###
        self.logger.info('List network...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets list_network', wait_timeout, raise_error)
        self.serial_wait_for_string('network id / ssid / bssid / flags', wait_timeout, raise_error)
        network_list = self.serial_filter_read_all(re_pattern=r'^\d', time_for_read=read_timeout)
        if filter_keyword:
            network_list = [n for n in network_list if filter_keyword in n]
        return [n.split() for n in network_list] if split_it else network_list

    def get_network(self, ssid, wait_timeout=60, raise_error=True):
        for network in self.list_network(split_it=True, wait_timeout=wait_timeout, raise_error=raise_error):
            if ssid == network[1]:
                return network
        # Need raise_error?
        return None

    def remove_network(self, network_id, save_changes=True, timeout=30, raise_error=True, restart_wifi=True):
        self.logger.info('Remove network...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets remove_network {}'.format(network_id), timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)
        if save_changes: self.save_network_config()
        if restart_wifi: self.restart_wifi()

    def disconnect_WiFi(self, timeout=30, raise_error=True):
        self.logger.info('Disconnect WiFi...')
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets disconnect', timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def reconnect_WiFi(self, timeout=30, raise_error=True):
        self.logger.info('Reconnect WiFi...')
        self.disconnect_WiFi()
        self.serial_write('wpa_cli -i wlan0 -p /data/misc/wifi/sockets reconnect', timeout, raise_error)
        self.serial_wait_for_string('OK', timeout, raise_error)

    def remove_all_network(self, save_changes=True, restart_wifi=True, timeout=30, raise_error=True):
        self.disconnect_WiFi(timeout, raise_error)
        time.sleep(0.5)
        for network in self.list_network(split_it=True, wait_timeout=timeout, raise_error=raise_error):
            self.disable_network(network[0], timeout=timeout, raise_error=raise_error)
            time.sleep(0.5)
            self.remove_network(network_id=network[0], save_changes=save_changes, timeout=timeout, raise_error=raise_error, restart_wifi=restart_wifi)

    def re_enable_wifi(self, disable_all=True, timeout=30, raise_error=True):
        # Solution from Carol.
        self.logger.info('Re-enable Wi-Fi...')
        self.serial_write('svc wifi disable', timeout, raise_error)
        #self.serial_write('svc wifi enable', timeout, raise_error)
        if disable_all:
            # Remove driver and load drive.
            self.serial_write('cat /proc/modules | grep 8822 && rmmod -w 8822be', timeout, raise_error)
            self.serial_write('insmod /vendor/modules/8822be.ko ifname=wlan0 if2name=p2p0', timeout, raise_error)
            # Kill wpa_supplicant and run wpa_supplicant.
            self.serial_write('pgrep wpa_supplicant && pgrep wpa_supplicant | xargs kill', timeout, raise_error)
            self.serial_write('wpa_supplicant -iwlan0 -Dnl80211 -c/data/misc/wifi/wpa_supplicant.conf -O/data/misc/wifi/sockets &', timeout, raise_error)
        else:
            # Load drive if drive not found.
            self.serial_write('cat /proc/modules | grep 8822 || insmod /vendor/modules/8822be.ko ifname=wlan0 if2name=p2p0', timeout, raise_error)
            # Run wpa_supplicant if wpa_supplicant not found.
            self.serial_write('pgrep wpa_supplicant || wpa_supplicant -iwlan0 -Dnl80211 -c/data/misc/wifi/wpa_supplicant.conf -O/data/misc/wifi/sockets &', timeout, raise_error)
        self.serial_write('pgrep dhcpcd && pgrep dhcpcd | xargs kill', timeout, raise_error)
        self.serial_write('dhcpcd wlan0 -t 0 &', timeout, raise_error)
        time.sleep(5)
        # Clear nouse data.
        self.serial_read_all()

    def setup_and_connect_WiFi(self, ssid, password, security_mode='WPA-PSK', enable_client_mode=True, timeout=60*30,
            reboot_after=None, restart_wifi=True, raise_error=True):
        """ Setup a new WiFi configuraiton and connect to AP.

        [Arguments]
            timeout: int
                Seconds to wait for IP.
            reboot_after: int
                Seconds. Reboot device if the device still doesn't get IP after reboot_after seconds.
        """
        if enable_client_mode: self.enable_client_mode(raise_error=raise_error)
        self.remove_all_network(save_changes=True, restart_wifi=restart_wifi, timeout=60, raise_error=raise_error)
        time.sleep(0.5)
        self.scan_wifi_ap(raise_error=raise_error, list_network=True)
        time.sleep(0.5)
        self.add_wifi(ssid, password, security_mode, restart_wifi=restart_wifi, raise_error=raise_error)
        time.sleep(0.5)
        return self.wait_for_ip(ssid, timeout, reboot_after, raise_error)

    def connect_existing_network(self, ssid, enable_client_mode=False, timeout=60*30, reboot_after=None, raise_error=True):
        """ Connect WiFi with specific existing configuration.

        [Arguments]
            timeout: int
                Seconds to wait for IP.
            reboot_after: int
                Seconds. Reboot device if the device still doesn't get IP after reboot_after seconds.
        """
        if enable_client_mode: self.enable_client_mode(raise_error=raise_error)
        network = self.get_network(ssid)
        if not network:
            return False
        time.sleep(0.5)
        if not self.is_network_connect(network):
            time.sleep(0.5)
            self.connect_network(network_id=network[0], raise_error=raise_error)
        time.sleep(0.5)
        return self.wait_for_ip(ssid, timeout, reboot_after, raise_error)

    def is_network_connect(self, splited_network):
        """ Method utility for check splited network message. """
        return not (4 > len(splited_network) or 'CURRENT' not in splited_network[3])

    def connect_WiFi(self, ssid, password, security_mode='WPA-PSK', enable_client_mode=True, timeout=60*30,
            reboot_after=None, restart_wifi=True, raise_error=True):
        """ Connect WiFi with existing configuration or add new one.
        """
        if enable_client_mode: self.enable_client_mode(raise_error=raise_error)
        network = self.get_network(ssid)
        if network: # Found existing configuratio.
            return self.connect_existing_network(ssid, False, timeout, reboot_after, raise_error)
        self.setup_and_connect_WiFi(ssid, password, security_mode, False, timeout, reboot_after, restart_wifi, raise_error)

    def enable_client_mode(self, raise_error=True):
        """ Detect device mode by IP (192.168.X.1), and turn to client mode if device is in AP mode.
        """
        now_ip = self.get_ip()
        if not now_ip: # Client mode. (No)
            return
        elif now_ip == '192.168.43.1': # Soft AP mode
            self.logger.info('Device in Soft AP mode, switch to client mode...')
            self.turn_ap_mode_off(raise_error=raise_error)
            self.serial_write('disable_factory.sh', timeout=5, raise_error=raise_error)

    def priority_wlan_first(self):
        self.interfaces_to_get_ip = ['wlan', 'eth']

    def priority_eth_first(self):
        self.interfaces_to_get_ip = ['eth', 'wlan']

    def priority_wlan_only(self):
        self.interfaces_to_get_ip = ['wlan']

    def priority_eth_only(self):
        self.interfaces_to_get_ip = ['eth']

    def get_ip(self, timeout=30):
        """ Get current IP address by priority. """
        ip = None
        for interface in self.interfaces_to_get_ip:
            ip = self.get_ip_by_interface(timeout, interface=interface)
            if ip:
                break
        return ip

    def get_ip_by_interface(self, timeout=30, interface='wlan|eth'):
        """ Get current IP address. """
        self.logger.info('Get IP address...')
        filter_cmd = "| grep -E '{}' -A 1".format(interface) if interface else ""
        self.serial_write("ifconfig" + filter_cmd + " |  grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*'")
        ip = self.serial_wait_for_filter_string(re_pattern=r'^[0-9]+(?:\.[0-9]+){3}')
        if ip and '127.0.0.1' in ip:
            return None
        # Clear nouse data.
        self.serial_read_all()
        return ip

    def wait_for_ip(self, ssid=None, timeout=60*30, reboot_after=None, raise_error=True):
        """ Wait device to get IP. 

        [Arguments]
            ssid: string
                SSID to reconnect if WiFi is disconnect during waiting.
            timeout: int
                Seconds to wait for IP.
            reboot_after: int
                Seconds. Reboot device if the device still doesn't get IP after reboot_after seconds.
        """
        def reconnect(ssid):
            network = self.get_network(ssid)
            if not network:
                raise RuntimeError('Network not found.')
            if not self.is_network_connect(network):
                self.connect_network(network_id=network[0], raise_error=raise_error)

        start = time.time()
        ip = self.get_ip(timeout=5)
        while not ip:
            elapsed_time = time.time() - start
            # Timeout handle.
            if elapsed_time > timeout:
                self.error('Wait for IP timeout: {}s'.format(timeout), raise_error)
                return False
            # Reboot device for WiFI cannot connect sometime issue.
            if reboot_after and elapsed_time > reboot_after:
                self.logger.warning('WiFi still not works after {}s, reboot device...'.format(reboot_after))
                self.reboot_device(raise_error=raise_error)
                self.wait_for_boot_complete(raise_error=raise_error)
                reboot_after = None
            # Reconnect network if WiFi still doesn't work.
            if ssid:
                reconnect(ssid)
            # Get IP.
            time.sleep(5)
            self.logger.info('Wait for IP...')
            ip = self.get_ip(timeout=5)
        self.logger.info('Connected to AP. The IP address is {}'.format(ip))
        return True

    def reboot_device(self, timeout=60*5, raise_error=True):
        self.logger.info('Reboot device...')
        self.serial_write('reboot', timeout=30, raise_error=raise_error)
        if not self.serial_wait_for_string('stopping android', timeout):
            self.error('Wait for reboot device timeout: {}s'.format(timeout), raise_error)
            return False
        return True

    def wait_for_boot_complete(self, timeout=60*5, raise_error=True):
        # Only for yoda.
        self.logger.info('Wait for device boot complete...')
        self.logger.info('Find boot up messages to make sure device is rebooted...')
        retry( # To fine boot up msg like this: "[    4.707041] dcdc1: disabling" which time is less than 60s.
            func=self.serial_filter_read_all, re_pattern=r'^[\t\s]*\[[\t\s]*\d*.\d*\] ', time_for_read=1,
            retry_lambda=lambda msgs: False if msgs and float(msgs[-1].split(']')[0].strip(' \t[')) < 60 else True,
            excepts=(Exception), delay=5, max_retry=12, log=self.logger.info, not_raise_error=True
        )
        # wlan0 check logic.
        wlan0 = {'up': False}
        def _check_wlan0(wlan0):
            if self.serial_wait_for_string('wlan0     Link ', 1, True):
                wlan0['up'] = True
                return True
            return False
        # Check wlan0 is up by "ifconfig wlan0".
        self.logger.info('Wait for wlan0 up...')
        retry(
            func=self.serial_write, buff='ifconfig wlan0', timeout=timeout, raise_error=raise_error,
            retry_lambda=lambda _: not _check_wlan0(wlan0),
            delay=5, max_retry=int(timeout/5) if timeout else 60, log=self.logger.info
        )
        self.serial_read_all() # clean up console
        if not wlan0['up']: # Not up.
            self.error('Wait for boot complete timeout: {}s'.format(timeout), raise_error)
            return False
        # Wait for bluetooth is up and setup timeout value to 2mins.
        if not self.serial_wait_for_string('bluetooth_set_power: block=0', timeout=60*2, raise_error=False):
            self.logger.warning('Wait for bluetooth_set_power timeout...')
        self.logger.info('Device boot completed.')
        return True

    def get_led_logs(self, time_for_read=20, log_filter=None):
        led_list = []
        logcat_list = self.serial_cmd(cmd='logcat -d -b system | grep LedServer', timeout=60*5, wait_response=True, return_type='list')
        if log_filter:
            logcat_list = log_filter(logcat_list)
        # parse the led_list from raw format to dictionary format
        for line in logcat_list:
            if 'sys state change' in line:
                led_re = re.compile("\((.+)\).->.\((.+)\)")
                type = 'SYS'
            elif 'Switching Led state' in line:
                led_re = re.compile("\((.+)\)->\((.+)\)")
                type = 'LED'
            else:
                continue
            results = led_re.search(line)
            if results:
                string_split = line.split()
                led_dict = {
                    'date': string_split[0],
                    'time': string_split[1],
                    'type': type,
                    'before': results.group(1),
                    'after': results.group(2)
                }
                led_list.append(led_dict)
        return led_list

    def restart_adbd(self, timeout=30, raise_error=True):
        self.logger.info('Restart adbd...')
        self.serial_write('stop adbd; start adbd', timeout, raise_error)

    def get_wifi_logs(self):
        self.logger.info('List Wi-Fi logs...')
        logs = self.serial_cmd(cmd='logcat -d | grep MyService', timeout=60*5, wait_response=True)
        self.logger.info('Output: \n{}'.format(logs))

    def write_logcat(self, message, priority='V', tag='AutomationTest', buffer=None):
        self.logger.info('Write logcat: {}'.format(message))
        args = []
        if priority: args.append('-p {}'.format(priority))
        if tag: args.append("-t '{}'".format(tag))
        if buffer: args.append('-b {}'.format(buffer))
        self.serial_write("log {} '{}'".format(' '.join(args), message))
        self.serial_read_all() # clean up console.

    def debug_system_timestamps(self):
        self.logger.info('Show head of system buffer...')
        logs = self.serial_cmd(cmd='logcat -d -b system | head', timeout=60*5, wait_response=True)
        self.logger.info('Output: \n{}'.format(logs))

    @disable_daemon_logs
    @pure_output_msg
    def export_logcat(self, path, read_timeout=60*5):
        # Read logcat log from console and save to a file.
        self.serial_read_all()
        self.logger.info('Export logcat...')
        logs = self.serial_cmd(cmd='logcat -d', timeout=read_timeout, wait_response=True)

        # remove first line and end line.
        logs = logs[logs.find('\n')+1: logs.rfind('\n')]

        self.logger.info('Save logcat logs to {}...'.format(path))
        with open(path, 'a') as f:
            f.write(logs)

    def clean_logcat(self, buffer_name=None, timeout=30, raise_error=True):
        """ Clean logcat logs."""
        self.logger.info('Clean logcat logs.')
        buffer_str = ''
        if buffer_name:
            buffer_str = ' -b ' + buffer_name
        self.serial_write('logcat -c{}'.format(buffer_str), timeout, raise_error)

    def sampling_led(self, sampling_times=37, time_interval=0.1):
        self.logger.debug('Sampling LED lighting value {} times with time interval {}...'.format(sampling_times, time_interval))
        self.serial_cmd(cmd='''rm /tmp/led 2> /dev/null;for i in `seq 1 {}`; do cat /sys/devices/platform/980070d0.pwm/dutyRate1 | {} >> /tmp/led ; echo >> /tmp/led; sleep {}; done'''.format(
            sampling_times, "grep -Eo '[0-9]{1,3}'", time_interval), timeout=60*5, wait_response=True)

    def get_interval_counts(self, threshold=50):
        self.logger.debug('Calculate sampling counts with threshold {}...'.format(threshold))
        # clean up console.
        self.serial_write('')
        self.serial_read_all()
        # for debug.
        values = self.serial_cmd(cmd='cat /tmp/led', timeout=60*5, wait_response=True)
        """ Original Code:
        max_count=0;
        now_count=0;
        start_record=no;
        for lv in `cat /tmp/so`; do
            if [ $lv -lt 50 ]; then
                if [ $start_record == no ]; then
                    start_record=yes;
                fi;
                now_count=$((now_count+1));
            else
                if [ $start_record == yes ]; then
                    start_record=no;
                    if [ $max_count -lt $now_count ]; then
                        max_count=$now_count;
                    fi
                    now_count=0;
                fi;
            fi;
        done;
        if [ $start_record == yes ]; then
            if [ $max_count -lt $now_count ]; then
                max_count=$now_count;
            fi
        fi;
        echo $max_count;
        """
        output = self.serial_cmd(cmd='''m=0;n=0;s=n;for l in `cat /tmp/led`;do if [ $l -lt {} ];then if [ $s == n ];then s=y;fi;n=$((n+1));else if [ $s == y ];then s=n;if [ $m -lt $n ];then m=$n;fi;n=0;fi;fi;done;if [ $s == y ];then if [ $m -lt $n ];then m=$n;fi;fi;echo $m'''.format(threshold),
            timeout=60*5, wait_response=True, return_type='list')
        for line in output[::-1]:
            if isinstance(line, basestring) and line.isdigit():
                return int(line)
        return None

    def get_led_state(self):
        self.logger.info('Get LED state...')
        self.sampling_led()
        counts = self.get_interval_counts()
        self.logger.debug('Counts: {}'.format(counts))
        if counts is None:
            return None
        elif counts == 0:
            return 'Full Solid'
        elif 0 < counts < 10: # Should be 6~7. Time interval of LED value change is 1.2 sec.
            return 'Fast Breathing'
        elif 10 <= counts <= 20: # Should be 18~19. Time interval of LED value change is 3.7 sec.
            return 'Slow Breathing'
        else:
            return 'Half Solid'

    def get_led_enable(self):
        self.logger.debug("Get LED enable status...")
        self.serial_read_all()
        ret = self.serial_cmd_and_get_resp(cmd='cat /sys/devices/platform/980070d0.pwm/enable1', timeout=2)
        if '1' in ret: # LED is enabled
            return True
        return False

    def clear_reserve_wifi_config(self):
        self.logger.debug('Clear reserve Wi-Fi config...')
        # Clear up old AP settings to avoid test recovery when disconnect.(Only for platfrom site, not sure Android behaviros)
        wificonfig = '/data/data/com.wdc.mycloud.BTWifiConfigService/shared_prefs/wificonfig.xml'
        self.serial_write('test -e {0} && rm {0}'.format(wificonfig))
        self.serial_read_all() # clean console.


    def start_background_logcat(self, log_path='debug_logcat'):
        self.logger.debug("Start to record logcat at background")
        self.serial_write("busybox ps ef | grep {0} | grep logcat | grep -v grep > /tmp/cmd_resp".format(log_path))
        self.serial_write("test -s /tmp/cmd_resp || logcat -f /data/wd/diskVolume0/{0} &".format(log_path))
        self.serial_write('') # clean console.
        self.serial_read_all()

    def kill_background_logcat(self, log_path='debug_logcat'):
        self.logger.debug("kill background logcat")
        self.serial_write("busybox ps ef | grep %s | grep logcat | grep -v grep | busybox awk '{print $1}' | xargs kill -9 " % log_path)
        self.serial_read_all() # clean console.

    def get_migrated_info(self, timeout=20, raise_error=True):
        self.logger.info('Try to get db migrated information...')
        logs = self.serial_cmd(cmd='logcat -d | grep "migrated" | grep "Migrate" | grep -v "MigratedLocal"', timeout=timeout, wait_response=True)
        self.logger.info('Output: \n{}'.format(logs))
        return logs

    def turn_on_soft_ap_mode(self):
        # Will turn off after about 3 mins.
        self.logger.debug("Turn on SoftAP mode for few mins...")
        self.serial_write('/system/bin/reset_button.sh short_start &')
        self.serial_read_all(time_for_read=2)
        self.serial_write('/system/bin/reset_button.sh short &')
        self.serial_read_all()
        # Wait for Soft AP mode.
        start = time.time()
        while 30 > time.time() - start:
            time.sleep(3)
            if self.get_ip() == '192.168.43.1':
                return True
        return False

    def start_otaclient_service(self):
        self.serial_write("sudo -u restsdk otaclient.sh start")
        self.serial_read_all(time_for_read=2)

    def stop_otaclient_service(self):
        self.serial_write("otaclient.sh stop")
        self.serial_read_all(time_for_read=2)

    #
    # KDP Feature Area
    #
    def turn_ap_mode_off_kdp(self, timeout=60, raise_error=True):
        self.logger.info('Switch to client mode...')
        self.serial_write('echo -n "ap_off" | sudo nc -U -w 2 /var/run/onboarding.sock', timeout, raise_error)
        #self.serial_wait_for_string('Broadcast completed: result=0', timeout, raise_error)
        time.sleep(5) # TODO: instead of waiting some mesg while build is stable

    def turn_on_soft_ap_mode_kdp(self):
        # Will turn off after about 3 mins.
        self.logger.debug("Turn on SoftAP mode for few mins...")
        self.serial_write('echo -n "ap_on" | sudo nc -U -w 2 /var/run/onboarding.sock')
        time.sleep(5) # TODO: instead of waiting some mesg while build is stable
        self.serial_read_all()
        # Wait for Soft AP mode.
        start = time.time()
        while 30 > time.time() - start:
            time.sleep(3)
            if self.get_ip() == '192.168.43.1':
                return True
        self.serial_write("ifconfig")
        self.serial_read_all()
        return False

    def scan_wifi_ap_and_list_kdp(self, filter_keyword=None, timeout=60, raise_error=True):
        self.logger.info('Scan WiFi AP...')
        self.serial_write('echo -n "scan_results" | sudo nc -U -w 2 /var/run/onboarding.sock', timeout, raise_error)
        self.serial_wait_for_string('root@', timeout, raise_error)
        self.logger.info('List WiFi AP...')
        ap_list = self.serial_filter_read_all(re_pattern=r'(?:[0-9a-fA-F]:?){12}', time_for_read=timeout)
        if filter_keyword:
            return [ap for ap in ap_list if filter_keyword in ap]
        return ap_list

    def get_configured_ssid_kdp(self, raise_error=True):
        self.logger.info('Get configured SSID...')
        self.serial_write('wpa_cli status | grep ssid | grep -v bssid', raise_error)
        output = self.serial_wait_for_string('ssid=', 15, raise_error)
        if output:
            self.logger.info('Current SSID is {}'.format(output.split('=')[1]))
            return output.split('=')[1] # TODO:check again while build is stable
        return

    def connect_WiFi_kdp(self, ssid, password, timeout=60*30, raise_error=True, check_ssid=False):
        self.configure_ssid_kdp(ssid=ssid, password=password, timeout=timeout, raise_error=raise_error)
        self.wait_for_wpa_state_completed(timeout, raise_error)
        if check_ssid:
            time.sleep(10) # Wait for ssid display changed
            if not self.verify_ssid_is_match(ssid):
                self.error('SSID is not match!!', raise_error)
        return self.wait_for_ip_kdp(timeout, raise_error)

    def configure_ssid_kdp(self, ssid, password, timeout=60*30, raise_error=True):
        self.logger.info('Connect to {}...'.format(ssid))
        self.serial_write(
            "echo -n 'set_network {} {}' | sudo nc -U -w 2 /var/run/onboarding.sock".format(ssid, password), timeout,
            raise_error)

    def wait_for_wpa_state_completed(self, timeout=60*10, raise_error=True):
        return self.wait_for_wpa_state(status='COMPLETED', timeout=timeout, raise_error=raise_error)

    def wait_for_wpa_state(self, status, timeout=60 * 10, raise_error=True):
        self.logger.info('Wait for wpa_state is in {}...'.format(status))
        start = time.time()
        output = self.get_wpa_state(timeout=30, raise_error=raise_error)
        while status not in output:
            elapsed_time = time.time() - start
            # Timeout handle.
            if elapsed_time > timeout:
                self.error('Wait for wpa_state {} timeout: {}s'.format(status, timeout), raise_error)
                return False
            time.sleep(1)
            output = self.get_wpa_state(timeout=5, raise_error=raise_error)
        self.logger.info('{}'.format(output))
        return True

    def get_wpa_state(self, timeout=5, raise_error=True):
        self.serial_write('wpa_cli status | grep wpa_state', raise_error=raise_error)
        output = self.serial_wait_for_string('wpa_state=', timeout, raise_error)
        if 'wpa_state=' in output: return output[10:].strip()
        return output

    def is_ip_available_for_network(self, ip):
        return ip and ip not in '192.168.43.1' and not ip.startswith('169.254')

    def verify_ssid_is_match(self, ssid):
        current_ssid = self.get_configured_ssid_kdp()
        if ssid == current_ssid:
            return True
        else:
            self.logger.warning('ssid is not match, current ssid is {0}, but given is {1}'.format(current_ssid, ssid))
            return False

    def retry_for_connect_WiFi_kdp(self, ssid, password, try_time=10, interval_secs=30, raise_error=True):
        for times in xrange(try_time):
            try:
                current_ip = self.get_ip(timeout=5)
                if self.is_ip_available_for_network(current_ip) and self.verify_ssid_is_match(ssid=ssid):
                    return current_ip
                self.logger.info('#{} to set WiFi'.format(times+1))
                self.connect_WiFi_kdp(ssid, password, raise_error=raise_error, check_ssid=True)
            except Exception as e:
                if times + 1 == try_time:
                    raise e
                self.logger.error('Got an error: {}'.format(e))
                self.logger.error('Retry after {} secs'.format(interval_secs))
                time.sleep(interval_secs)

    def wait_for_ip_kdp(self, timeout=60*30, raise_error=True):
        # TODO: add reboot and reconnect if we need
        """ Wait device to get IP. 
        """
        start = time.time()
        ip = self.get_ip(timeout=5)
        while not ip:
            elapsed_time = time.time() - start
            # Timeout handle.
            if elapsed_time > timeout:
                self.error('Wait for IP timeout: {}s'.format(timeout), raise_error)
                return False
            # Get IP.
            time.sleep(5)
            self.logger.info('Wait for IP...')
            ip = self.get_ip(timeout=5)
        self.logger.info('Connected to AP. The IP address is {}'.format(ip))
        return True

    def wait_for_docker_up(self, timeout=60*10):
        def get_docker_interface(timeout):
            self.reset_command_line()
            self.logger.info('Get docker interface...')
            self.serial_write("ifconfig | grep docker")
            try:
                self.serial_wait_for_string('Ethernet', timeout, raise_error=True)
            except:
                return False
            return True

        start = time.time()
        while not get_docker_interface(timeout=30):
            elapsed_time = time.time() - start
            # Timeout handle.
            if elapsed_time > timeout:
                self.error('Wait for docker interface up timeout: {}s'.format(timeout), raise_error=True)
                return False
        self.logger.info('Docker interface is up')
        return True

    def reboot_device_kdp(self, timeout=60*5, raise_error=True):
        self.logger.info('Reboot device...')
        self.serial_write('do_reboot', timeout=30, raise_error=raise_error)
        if not self.serial_wait_for_string('The system is going down', timeout):
            self.error('Wait for reboot device timeout: {}s'.format(timeout), raise_error)
            return False
        return True

    def wait_for_boot_complete_kdp(self, timeout=60*5, raise_error=True):
        self.logger.info('Wait for device boot completed...')
        try:
            output = self.serial_wait_for_string('System Ready', timeout, raise_error)
        except Exception as e:
            if raise_error: raise e
            return False
        if not output:
            return False
        self.wait_for_docker_up() # not break anything
        time.sleep(60) # wait more time to let device prepare something we don't know...
        self.logger.info('Device is ready')
        return True

    def get_mac_from_boot_up_message(self, timeout=60, raise_error=True):
        # Be careful that sometimes EVT board has incorrect mac address in boot up message.
        # ethaddr = "00:00:C0:0B:76:A7";
        line = self.serial_wait_for_string('ethaddr = "', timeout, raise_error)
        return line.split('"')[1]

    def get_serial_from_boot_up_message(self, timeout=60, raise_error=True):
        # serial = "WXR1E97FYUZ3";
        line = self.serial_wait_for_string('serial = "', timeout, raise_error)
        return line.split('"')[1]

    def unlock_otaclient_service_kdp(self):
        self.serial_write("setprop persist.wd.ota.lock 0")
        self.serial_read_all(time_for_read=2)

    def lock_otaclient_service_kdp(self):
        self.serial_write("setprop persist.wd.ota.lock 1")
        self.serial_read_all(time_for_read=2)

    def check_ifplug_zombie_exist(self, raise_error=True):
        self.logger.info('Start to check ifplug zombie issue ...') # KDP-4812
        self.wait_for_wpa_state_completed()
        output = self.serial_cmd_and_get_resp("ps aux | grep ifplug | grep -v 'grep ifplug'")
        if 'Z' in output:
            self.logger.debug('Output: {}'.format(output))
            return True
        output = self.serial_cmd_and_get_resp("cat /var/log/daemon.log | grep ifplugd")
        if 'Temporary failure in name resolution' in output:
            self.logger.debug('Output: {}'.format(output))
            return True
        return False

    def get_model(self):
        self.logger.info('Get device model type ...')
        model = self.serial_cmd_and_get_resp("cat /etc/model")
        if model: return model

    def file_exists(self, path, raise_error=True):
        self.logger.debug('Checking {} exists'.format(path))
        output = self.serial_cmd_and_get_resp('test -e {} && echo EXIST || echo NOTEXIST'.format(path))
        if 'NOTEXIST' in output: return False
        elif 'EXIST' in output: return True
        if raise_error:
            raise RuntimeError('Unexpected response')
        self.logger.warning('Unexpected response')

    def process_exists(self, process_name, raise_error=True):
        self.logger.debug('Checking {} exists'.format(process_name))
        output = self.serial_cmd_and_get_resp(
            'ps ef | grep {} | grep -v grep && echo EXIST || echo NOTEXIST'.format(process_name))
        if 'NOTEXIST' in output: return False
        elif 'EXIST' in output: return True
        if raise_error:
            raise RuntimeError('Unexpected response')
        self.logger.warning('Unexpected response')

    def remount_usb(self, usb_path, max_retry=10, raise_error=True):
        self.logger.info("Remounting USB")
        self.serial_cmd("mount | grep USB | grep 'ro,'")
        status = self.get_exit_code()
        try_times = 0
        while status == 0:
            try_times+1
            self.serial_cmd("mount -o rw,remount {}".format(usb_path))
            time.sleep(3)
            self.serial_cmd("mount | grep USB | grep 'ro,'")
            status = self.get_exit_code()
            if status != 0 and try_times == max_retry:
                if raise_error: raise RuntimeError("Failed to remount USB")
                self.logger.error("Failed to remount USB")


if __name__ == '__main__':
    import argparse
    # Arguments
    parser = argparse.ArgumentParser(description='List all attached device information')
    parser.add_argument('-ip', '--server-ip', help='Destination server IP', default='fileserver.hgst.com')
    parser.add_argument('-port', '--serial-port', help='Serial port number', type=int, default='20000')
    parser.add_argument('-remove', '--remove-id', help='Network ID to remove before add new one', default=None)
    parser.add_argument('-ssid', '--ssid', help='SSID of new network', default=None)
    parser.add_argument('-password', '--password', help='Password of new network', default=None)
    parser.add_argument('-mode', '--security-mode', help='Security Mode of new network', default='WPA-PSK')
    parser.add_argument('-not_scan', '--not-scan-ap', help='Do not scan existing AP', action='store_false', default=True)
    parser.add_argument('-disconnect', '--disconnect-after-added', help='Disconnect WiFi after added the new one', action='store_true', default=False)
    parser.add_argument('-reconnect', '--reconnect-after-added', help='Reconnect WiFi after added the new one', action='store_true', default=False)
    args = parser.parse_args()

    # Test for WiFi auto connect.
    sc = SerialClient(server_ip=args.server_ip, uut_port=args.serial_port)
    sc.initialize_serial_port()
    #sc.start_serial_port()
    sc.enable_client_mode()
    if args.not_scan_ap:
        sc.scan_wifi_ap()
        sc.list_wifi_ap()
    if args.remove_id:
        sc.remove_network(network_id=args.remove_id)
    if args.ssid:
        network_id = sc.connect_WiFi(ssid=args.ssid, password=args.password, security_mode=args.security_mode)
        print 'New Network ID: ', network_id
        sc.list_network()
    if args.disconnect_after_added:
        sc.disconnect_WiFi()
        sc.list_network()
    if args.reconnect_after_added:
        sc.reconnect_WiFi()
        sc.list_network()
