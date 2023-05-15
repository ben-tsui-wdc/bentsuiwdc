#! /usr/bin/env python
#
# (C) 2001-2015 Chris Liechti <cliechti@gmx.net>
#
# SPDX-License-Identifier:    BSD-3-Clause
"""\
Multi-port serial<->TCP/IP forwarder.
- RFC 2217
- check existence of serial port periodically
- start/stop forwarders
- each forwarder creates a server socket and opens the serial port
- serial ports are opened only once. network connect/disconnect
  does not influence serial port
- only one client per connection

20171103 (Estvan Huang):
- Added port history to fix port number for each USB slots.
"""
import json
import os
import select
import socket
import signal
import sys
import time
import threading
import traceback

import serial
import serial.rfc2217
import serial.tools.list_ports

import dbus

from servercli import run_server

DEFAULT_BAUD_RATE = 115200


# Try to import the avahi service definitions properly. If the avahi module is
# not available, fall back to a hard-coded solution that hopefully still works.
try:
    import avahi
except ImportError:
    class avahi:
        DBUS_NAME = "org.freedesktop.Avahi"
        DBUS_PATH_SERVER = "/"
        DBUS_INTERFACE_SERVER = "org.freedesktop.Avahi.Server"
        DBUS_INTERFACE_ENTRY_GROUP = DBUS_NAME + ".EntryGroup"
        IF_UNSPEC = -1
        PROTO_UNSPEC, PROTO_INET, PROTO_INET6 = -1, 0, 1


class ZeroconfService:
    """\
    A simple class to publish a network service with zeroconf using avahi.
    """

    def __init__(self, name, port, stype="_http._tcp",
                 domain="", host="", text=""):
        self.name = name
        self.stype = stype
        self.domain = domain
        self.host = host
        self.port = port
        self.text = text
        self.group = None

    def publish(self):
        bus = dbus.SystemBus()
        server = dbus.Interface(
            bus.get_object(
                avahi.DBUS_NAME,
                avahi.DBUS_PATH_SERVER
            ),
            avahi.DBUS_INTERFACE_SERVER
        )

        g = dbus.Interface(
            bus.get_object(
                avahi.DBUS_NAME,
                server.EntryGroupNew()
            ),
            avahi.DBUS_INTERFACE_ENTRY_GROUP
        )

        g.AddService(avahi.IF_UNSPEC, avahi.PROTO_UNSPEC, dbus.UInt32(0),
                     self.name, self.stype, self.domain, self.host,
                     dbus.UInt16(self.port), self.text)

        g.Commit()
        self.group = g

    def unpublish(self):
        if self.group is not None:
            self.group.Reset()
            self.group = None

    def __str__(self):
        return "{!r} @ {}:{} ({})".format(self.name, self.host, self.port, self.stype)


class Forwarder(ZeroconfService):
    """\
    Single port serial<->TCP/IP forarder that depends on an external select
    loop.
    - Buffers for serial -> network and network -> serial
    - RFC 2217 state
    - Zeroconf publish/unpublish on open/close.
    """

    def __init__(self, device, location, name, network_port, baudrate, on_close=None, log=None):
        ZeroconfService.__init__(self, name, network_port, stype='_serial_port._tcp')
        self.alive = False
        self.network_port = network_port
        self.on_close = on_close
        self.log = log
        self.location = location
        self.device = device
        self.serial = serial.Serial()
        self.serial.port = device
        self.serial.baudrate = baudrate
        self.serial.timeout = 0
        self.socket = None
        self.server_socket = None
        self.rfc2217 = None  # instantiate later, when connecting

    def __del__(self):
        try:
            if self.alive:
                self.close()
        except:
            pass  # XXX errors on shutdown

    def open(self):
        """open serial port, start network server and publish service"""
        self.buffer_net2ser = bytearray()
        self.buffer_ser2net = bytearray()

        # open serial port
        try:
            self.serial.rts = False
            self.serial.open()
        except Exception as msg:
            self.handle_serial_error(msg)

        self.serial_settings_backup = self.serial.get_settings()

        # start the socket server
        # XXX add IPv6 support: use getaddrinfo for socket options, bind to multiple sockets?
        #       info_list = socket.getaddrinfo(None, port, 0, socket.SOCK_STREAM, 0, socket.AI_PASSIVE)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            self.server_socket.getsockopt(
                socket.SOL_SOCKET,
                socket.SO_REUSEADDR
            ) | 1
        )
        self.server_socket.setblocking(0)
        try:
            self.server_socket.bind(('', self.network_port))
            self.server_socket.listen(1)
        except socket.error as msg:
            self.handle_server_error()
            #~ raise
        if self.log is not None:
            self.log.info("{}({})(baud rate: {}): Waiting for connection on {}...".format(
                self.device, self.location, self.serial.baudrate, self.network_port))

        # zeroconfig
        self.publish()

        if self.log is not None:
            self.log.info("Published: {}".format(self))

        # now we are ready
        self.alive = True

    def close(self):
        """Close all resources and unpublish service"""
        if self.log is not None:
            self.log.info("{}({})(baud rate: {}): closing port: {}...".format(
                self.device, self.location, self.serial.baudrate, self.network_port))
        self.alive = False
        self.unpublish()
        if self.server_socket:
            self.server_socket.close()
        if self.socket:
            self.handle_disconnect()
        self.serial.close()
        if self.on_close is not None:
            # ensure it is only called once
            callback = self.on_close
            self.on_close = None
            callback(self)

    def write(self, data):
        """the write method is used by serial.rfc2217.PortManager. it has to
        write to the network."""
        self.buffer_ser2net += data

    def update_select_maps(self, read_map, write_map, error_map):
        """Update dictionaries for select call. insert fd->callback mapping"""
        if self.alive:
            # always handle serial port reads
            read_map[self.serial] = self.handle_serial_read
            error_map[self.serial] = self.handle_serial_error
            # handle serial port writes if buffer is not empty
            if self.buffer_net2ser:
                write_map[self.serial] = self.handle_serial_write
            # handle network
            if self.socket is not None:
                # handle socket if connected
                # only read from network if the internal buffer is not
                # already filled. the TCP flow control will hold back data
                if len(self.buffer_net2ser) < 2048:
                    read_map[self.socket] = self.handle_socket_read
                # only check for write readiness when there is data
                if self.buffer_ser2net:
                    write_map[self.socket] = self.handle_socket_write
                error_map[self.socket] = self.handle_socket_error
            else:
                # no connection, ensure clear buffer
                self.buffer_ser2net = bytearray()
            # check the server socket
            read_map[self.server_socket] = self.handle_connect
            error_map[self.server_socket] = self.handle_server_error

    def handle_serial_read(self):
        """Reading from serial port"""
        try:
            data = os.read(self.serial.fileno(), 1024)
            if data:
                # store data in buffer if there is a client connected
                if self.socket is not None:
                    # escape outgoing data when needed (Telnet IAC (0xff) character)
                    if self.rfc2217:
                        data = serial.to_bytes(self.rfc2217.escape(data))
                    self.buffer_ser2net.extend(data)
            else:
                self.handle_serial_error()
        except Exception as msg:
            self.handle_serial_error(msg)

    def handle_serial_write(self):
        """Writing to serial port"""
        try:
            # write a chunk
            n = os.write(self.serial.fileno(), bytes(self.buffer_net2ser))
            # and see how large that chunk was, remove that from buffer
            self.buffer_net2ser = self.buffer_net2ser[n:]
        except Exception as msg:
            self.handle_serial_error(msg)

    def handle_serial_error(self, error=None):
        """Serial port error"""
        # terminate connection
        self.close()

    def handle_socket_read(self):
        """Read from socket"""
        try:
            # read a chunk from the serial port
            data = self.socket.recv(1024)
            if data:
                # Process RFC 2217 stuff when enabled
                if self.rfc2217:
                    data = b''.join(self.rfc2217.filter(data))
                # add data to buffer
                self.buffer_net2ser.extend(data)
            else:
                # empty read indicates disconnection
                self.handle_disconnect()
        except socket.error:
            if self.log is not None:
                self.log.exception("{}: error reading...".format(self.device))
            self.handle_socket_error()

    def handle_socket_write(self):
        """Write to socket"""
        try:
            # write a chunk
            count = self.socket.send(bytes(self.buffer_ser2net))
            # and remove the sent data from the buffer
            self.buffer_ser2net = self.buffer_ser2net[count:]
        except socket.error:
            if self.log is not None:
                self.log.exception("{}: error writing...".format(self.device))
            self.handle_socket_error()

    def handle_socket_error(self):
        """Socket connection fails"""
        self.handle_disconnect()

    def handle_connect(self):
        """Server socket gets a connection"""
        # accept a connection in any case, close connection
        # below if already busy
        connection, addr = self.server_socket.accept()
        if self.socket is None:
            self.socket = connection
            # More quickly detect bad clients who quit without closing the
            # connection: After 1 second of idle, start sending TCP keep-alive
            # packets every 1 second. If 3 consecutive keep-alive packets
            # fail, assume the client is gone and close the connection.
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, 1)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 1)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, 3)
            self.socket.setblocking(0)
            self.socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            if self.log is not None:
                self.log.warning('{}: Connected by {}:{}'.format(self.device, addr[0], addr[1]))
            self.serial.rts = True
            self.serial.dtr = True
            if self.log is not None:
                self.rfc2217 = serial.rfc2217.PortManager(self.serial, self, logger=log.getChild(self.device))
            else:
                self.rfc2217 = serial.rfc2217.PortManager(self.serial, self)
        else:
            # reject connection if there is already one
            connection.close()
            if self.log is not None:
                self.log.warning('{}: Rejecting connect from {}:{}'.format(self.device, addr[0], addr[1]))

    def handle_server_error(self):
        """Socket server fails"""
        self.close()

    def handle_disconnect(self):
        """Socket gets disconnected"""
        # signal disconnected terminal with control lines
        try:
            self.serial.rts = False
            self.serial.dtr = False
        finally:
            # restore original port configuration in case it was changed
            self.serial.apply_settings(self.serial_settings_backup)
            # stop RFC 2217 state machine
            self.rfc2217 = None
            # clear send buffer
            self.buffer_ser2net = bytearray()
            # close network connection
            if self.socket is not None:
                self.socket.close()
                self.socket = None
                if self.log is not None:
                    self.log.warning('{}: Disconnected'.format(self.device))


class TelnetPortManager(object):

    def __init__(self, base_port, portfile, log):
        self.base_port = base_port
        self.log = log
        self.portfile = portfile
        self.port_map = {}
        if not os.path.exists(self.portfile): open(self.portfile, 'a').close()
        self.load_existing_port_map()

    def load_existing_port_map(self):
        try:
            with open(self.portfile, 'r') as fp:
                self.port_map = json.load(fp)
        except:
            pass

    def save_port_map(self):
        with open(self.portfile, 'w') as fp:
            json.dump(self.port_map, fp)

    def register_usb(self, usb_location, commit=True):
        if usb_location in self.port_map:
            return self.port_map[usb_location]

        port = self.base_port
        ports_in_use = [idx for idx in self.port_map.values()]
        while port in ports_in_use:
            port += 1

        self.port_map[usb_location] = port
        log.info('port_map changed: {}'.format(self.port_map))
        if commit:
            self.save_port_map()
        return port

    def clear_unuse_port(self, brm):
        location_in_use = [d.location for d in serial.tools.list_ports.grep(args.ports_regex)]
        location_in_map = self.port_map.keys()
        for device_location in set(location_in_map).difference(location_in_use):
            port = self.port_map.get(device_location, None)
            self.log.info('remove: {} from rate map'.format(port))
            brm.remove_baud_rate(port)
            self.port_map.pop(device_location, None)
            self.log.info('remove: {} from port map'.format(device_location))
        log.info('port map changed: {}'.format(self.port_map))
        log.info('rate map changed: {}'.format(brm.baud_rate_map))
        self.save_port_map()
        brm.save_baud_rate_map()


class BaudRateManager(object):

    def __init__(self, baudratefile, log):
        self.log = log
        self.baudratefile = baudratefile
        self.baud_rate_map = {}
        if not os.path.exists(self.baudratefile): open(self.baudratefile, 'a').close()
        self.load_existing_baud_rate_map()

    def load_existing_baud_rate_map(self):
        try:
            with open(self.baudratefile, 'r') as fp:
                self.baud_rate_map = json.load(fp)
        except:
            pass

    def save_baud_rate_map(self):
        with open(self.baudratefile, 'w') as fp:
            json.dump(self.baud_rate_map, fp)

    def set_baud_rate(self, usb_port, baud_rate, commit=True):
        usb_port_str = str(usb_port)
        if baud_rate in [DEFAULT_BAUD_RATE, 0]:
            if usb_port_str in self.baud_rate_map: self.remove_baud_rate(usb_port)
        else:
            self.baud_rate_map[usb_port_str] = baud_rate
        log.info('Updated baud rate map: {}'.format(self.baud_rate_map))
        if commit:
            self.save_baud_rate_map()

    def get_baud_rate(self, usb_port, default):
        return self.baud_rate_map.get(str(usb_port), default)

    def remove_baud_rate(self, usb_port):
        return self.baud_rate_map.pop(str(usb_port), None)


def test():
    service = ZeroconfService(name="TestService", port=3000)
    service.publish()
    input("Press the ENTER key to unpublish the service ")
    service.unpublish()


def start_cmd_handler(forwarder_map, brm, log):
    server = run_server() # Fork a process. Use server.shutdown() to stop it.
    log.info('Command manager process start...')
    cmd_queue = server.get_queue()
    ce = CommandExector(cmd_queue, forwarder_map)
    # Fork a thread to handle commands.
    ce.start()
    return ce


class CommandExector(threading.Thread):

    def __init__(self, cmd_queue, forwarder_map):
        threading.Thread.__init__(self)
        self.running = True
        self.cmd_queue = cmd_queue
        self.forwarder_map = forwarder_map

    def run(self):
        log.info('execute_cmd thread start...')

        while self.running:
            try:
                cmd_done = False
                cmd_dict = self.cmd_queue.get()
                log.info('Receive command: {}'.format(cmd_dict))

                # Restart telnet connection by device port.
                if cmd_dict['cmd'] in 'restart_port':
                    port = cmd_dict['value']
                    # Find forwarder object by telnet port and restart it.
                    for forwarder in self.forwarder_map.itervalues():
                        if forwarder.network_port == port:
                            log.warning('Restart forwarder by telnet port: {}...'.format(port))
                            forwarder.close()
                            forwarder.open()
                            cmd_done = True
                            break
                    if not cmd_done:
                        log.warning('Command failed')

                # Restart telnet connection by device USB ID.
                elif cmd_dict['cmd'] in 'restart_id':
                    usb_id = cmd_dict['value']
                    # Find forwarder object by USB ID and restart it.
                    forwarder = self.forwarder_map.get(usb_id)
                    if not forwarder:
                        log.warning('Not found a forwarder by USB ID: {}...'.format(usb_id))
                        continue
                    log.warning('Restart forwarder by USB ID: {}...'.format(usb_id))
                    forwarder.close()
                    forwarder.open()

                # Reattach a ttyUSB node by device port.
                elif cmd_dict['cmd'] in 'reattach_port':
                    port = cmd_dict['value']
                    for forwarder in self.forwarder_map.itervalues():
                        if forwarder.network_port == port:
                            log.warning('Reattach ttyUSB node by telnet port: {}...'.format(port))
                            reattach_usbtty(usb_id=forwarder.location)
                            cmd_done = True
                            break
                    if not cmd_done:
                        log.warning('Command failed')

                # Reattach a ttyUSB node by device USB ID.
                elif cmd_dict['cmd'] in 'reattach_id':
                    usb_id = cmd_dict['value']
                    log.warning('Reattach ttyUSB node by USB ID: {}...'.format(usb_id))
                    reattach_usbtty(usb_id=usb_id)

                # Set baud rate to specifying USB port.
                elif cmd_dict['cmd'] in 'set_baud_rate':
                    port = cmd_dict['port']
                    rate = cmd_dict['value']

                    if rate in [DEFAULT_BAUD_RATE, 0]:
                        rate = DEFAULT_BAUD_RATE

                    for forwarder in self.forwarder_map.itervalues():
                        if forwarder.network_port == port:
                            log.warning('Set port: {} to baud rate: {}...'.format(port, rate))
                            forwarder.close()
                            forwarder.serial.baudrate = rate
                            forwarder.open()
                            brm.set_baud_rate(port, rate, commit=True)
                            cmd_done = True
                            break
                    if not cmd_done:
                        log.warning('Command failed')

            except Exception as e:
                log.exception(e)


# Tool functions
def reattach_usbtty(usb_id, driver_name='pl2303'):
    """ Need root permission. """
    dettach_usbtty(usb_id, driver_name)
    attach_usbtty(usb_id, driver_name)

def dettach_usbtty(usb_id, driver_name='pl2303'):
    os.system("echo -n '{}:1.0' > /sys/bus/usb/drivers/{}/unbind".format(usb_id, driver_name))

def attach_usbtty(usb_id, driver_name='pl2303'):
    os.system("echo -n '{}:1.0' > /sys/bus/usb/drivers/{}/bind".format(usb_id, driver_name))


if __name__ == '__main__':  # noqa
    import logging
    import argparse

    VERBOSTIY = [
        logging.ERROR,      # 0
        logging.WARNING,    # 1 (default)
        logging.INFO,       # 2
        logging.DEBUG,      # 3
    ]

    parser = argparse.ArgumentParser(
        usage="""\
%(prog)s [options]
Announce the existence of devices using zeroconf and provide
a TCP/IP <-> serial port gateway (implements RFC 2217).
If running as daemon, write to syslog. Otherwise write to stdout.
""",
        epilog="""\
NOTE: no security measures are implemented. Anyone can remotely connect
to this service over the network.
Only one connection at once, per port, is supported. When the connection is
terminated, it waits for the next connect.
""")

    group = parser.add_argument_group("serial port settings")

    group.add_argument(
        "--ports-regex",
        help="specify a regex to search against the serial devices and their descriptions (default: %(default)s)",
        default='/dev/ttyUSB[0-9]+',
        metavar="REGEX")

    group = parser.add_argument_group("network settings")

    group.add_argument(
        "--tcp-port",
        dest="base_port",
        help="specify lowest TCP port number (default: %(default)s)",
        default=7000,
        type=int,
        metavar="PORT")

    group = parser.add_argument_group("daemon")

    group.add_argument(
        "-d", "--daemon",
        dest="daemonize",
        action="store_true",
        help="start as daemon",
        default=False)

    group.add_argument(
        "--pidfile",
        help="specify a name for the PID file",
        default=None,
        metavar="FILE")

    group = parser.add_argument_group("diagnostics")

    group.add_argument(
        "-o", "--logfile",
        help="write messages file instead of stdout",
        default=None,
        metavar="FILE")

    group.add_argument(
        "-q", "--quiet",
        dest="verbosity",
        action="store_const",
        const=0,
        help="suppress most diagnostic messages",
        default=1)

    group.add_argument(
        "-v", "--verbose",
        dest="verbosity",
        action="count",
        help="increase diagnostic messages")

    group.add_argument(
        "--portfile",
        help="specify a name for the port map file (default: %(default)s)",
        default='portfile',
        metavar="FILE")

    group.add_argument(
        "--clean-registry-per",
        help="specify a time for clear USB registry table (default: %(default)s)",
        default=None,
        type=int,
        metavar="Time")

    group.add_argument(
        "--baudratefile",
        help="specify a name for the baud rate map file (default: %(default)s)",
        default='baudratefile',
        metavar="FILE")

    group.add_argument(
        "--defaultbaudrate",
        help="Default bual rate (default: %(default)s)",
        default=DEFAULT_BAUD_RATE,
        type=int,
        metavar="BAUDRATE")

    args = parser.parse_args()

    # set up logging
    logging.basicConfig(level=VERBOSTIY[min(args.verbosity, len(VERBOSTIY) - 1)])
    log = logging.getLogger('port_publisher')

    DEFAULT_BAUD_RATE = args.defaultbaudrate
    log.info('Default baud rate: {}'.format(DEFAULT_BAUD_RATE))

    # redirect output if specified
    if args.logfile is not None:
        class WriteFlushed:
            def __init__(self, fileobj):
                self.fileobj = fileobj

            def write(self, s):
                self.fileobj.write(s)
                self.fileobj.flush()

            def close(self):
                self.fileobj.close()
        sys.stdout = sys.stderr = WriteFlushed(open(args.logfile, 'a'))
        # atexit.register(lambda: sys.stdout.close())

    if args.daemonize:
        # if running as daemon is requested, do the fork magic
        # args.quiet = True
        # do the UNIX double-fork magic, see Stevens' "Advanced
        # Programming in the UNIX Environment" for details (ISBN 0201563177)
        try:
            pid = os.fork()
            if pid > 0:
                # exit first parent
                sys.exit(0)
        except OSError as e:
            log.critical("fork #1 failed: {} ({})\n".format(e.errno, e.strerror))
            sys.exit(1)

        # decouple from parent environment
        os.chdir("/")   # don't prevent unmounting....
        os.setsid()
        os.umask(0)

        # do second fork
        try:
            pid = os.fork()
            if pid > 0:
                # exit from second parent, save eventual PID before
                if args.pidfile is not None:
                    open(args.pidfile, 'w').write("{}".format(pid))
                sys.exit(0)
        except OSError as e:
            log.critical("fork #2 failed: {} ({})\n".format(e.errno, e.strerror))
            sys.exit(1)

        if args.logfile is None:
            import syslog
            syslog.openlog("serial port publisher")

            # redirect output to syslog
            class WriteToSysLog:
                def __init__(self):
                    self.buffer = ''

                def write(self, s):
                    self.buffer += s
                    if '\n' in self.buffer:
                        output, self.buffer = self.buffer.split('\n', 1)
                        syslog.syslog(output)

                def flush(self):
                    syslog.syslog(self.buffer)
                    self.buffer = ''

                def close(self):
                    self.flush()
            sys.stdout = sys.stderr = WriteToSysLog()

            # ensure the that the daemon runs a normal user, if run as root
        # if os.getuid() == 0:
            #    name, passwd, uid, gid, desc, home, shell = pwd.getpwnam('someuser')
            #    os.setgid(gid)     # set group first
            #    os.setuid(uid)     # set user

    # init and load port map
    tpm = TelnetPortManager(base_port=args.base_port, portfile=args.portfile, log=log)
    log.info('port_map: {}'.format(tpm.port_map))
    brm = BaudRateManager(args.baudratefile, log)
    log.info('baud_rate_map: {}'.format(brm.baud_rate_map))
    # keep the published stuff in a dictionary
    published = {}
    # get a nice hostname
    hostname = socket.gethostname()

    def unpublish(forwarder):
        """when forwarders die, we need to unregister them"""
        try:
            del published[forwarder.location]
        except KeyError:
            pass
        else:
            log.info("unpublish: {}({})".format(forwarder, forwarder.location))

    if args.clean_registry_per:
        log.info("Time period for clean registry table: {}s".format(args.clean_registry_per))
    else:
        log.info("Not clean registry table")

    sch = start_cmd_handler(forwarder_map=published, brm=brm, log=logging.getLogger('cmd'))
    def stop_sch(sig, frame):
        sch.running = False
        sys.exit(0)
    signal.signal(signal.SIGINT, stop_sch)

    alive = True
    next_check = 0
    next_clear = args.clean_registry_per
    # main loop
    while alive:
        try:
            # if it is time, check for serial port devices
            now = time.time()
            if now > next_check:
                next_check = now + 5
                ld_map = {d.location: d.device for d in serial.tools.list_ports.grep(args.ports_regex)}
                # check map
                for k in ld_map.keys():
                    if k is None or not k or k == 'None':
                        log.warning("Unknown USB location found: {}({})".format(ld_map.get(k), k))
                        ld_map.pop(k, None)

                # Replace Device Path (d.device) by Device Location (d.location).
                connected = ld_map.keys()
                # Handle devices that are published, but no longer connected
                for device_location in set(published).difference(connected):
                    log.info("unpublish: {}({})".format(published[device_location], device_location))
                    unpublish(published[device_location])
                # Handle devices that are connected but not yet published
                for device_location in sorted(set(connected).difference(published)):
                    # Use registered port or find the first available port(starting from specified number)
                    port = tpm.register_usb(usb_location=device_location, commit=True)
                    # Read from "baudratefile" every time
                    baudrate = brm.get_baud_rate(port, DEFAULT_BAUD_RATE)
                    published[device_location] = Forwarder(
                        ld_map[device_location],
                        device_location,
                        "{}({}) on {}".format(ld_map[device_location], device_location, hostname),
                        port,
                        baudrate,
                        on_close=unpublish,
                        log=log)
                    log.warning("publish: {}({})".format(published[device_location], device_location))
                    published[device_location].open()

            if args.clean_registry_per and now > next_clear:
                next_clear = now + args.clean_registry_per
                log.warning("clean registry table...")
                tpm.clear_unuse_port(brm)

            # select_start = time.time()
            read_map = {}
            write_map = {}
            error_map = {}
            for publisher in published.values():
                publisher.update_select_maps(read_map, write_map, error_map)
            readers, writers, errors = select.select(
                read_map.keys(),
                write_map.keys(),
                error_map.keys(),
                5)
            # select_end = time.time()
            # print "select used %.3f s" % (select_end - select_start)
            for reader in readers:
                read_map[reader]()
            for writer in writers:
                write_map[writer]()
            for error in errors:
                error_map[error]()
            # print "operation used %.3f s" % (time.time() - select_end)
        except KeyboardInterrupt:
            alive = False
            sys.stdout.write('\n')
        except SystemExit:
            raise
        except:
            #~ raise
            traceback.print_exc()
