from multiprocessing.managers import BaseManager
import argparse
import Queue
import sys
import threading


# Default
ip = ''
port = 65432
authkey = '1qaz2wsx3edc'


def run_server(ip=ip, port=port):
    """ Fork a prcoess to maintain this QueueManager. """
    queue = Queue.Queue()
    class QueueManager(BaseManager): pass
    QueueManager.register('get_queue', callable=lambda:queue)
    server = QueueManager(address=(ip, port), authkey=authkey)
    # TODO: A more queue for respose to client.
    server.start()
    # server.get_queue()
    # server.shutdown()
    return server

def server_client(ip=ip, port=port):
    class QueueManager(BaseManager): pass
    QueueManager.register('get_queue')
    return QueueManager(address=(ip, port), authkey=authkey)



if __name__ == '__main__':
    # Arguments
    parser = argparse.ArgumentParser(description='Serial server command line interface')
    parser.add_argument('-ip', '--server-ip', help='Serial server IP', default='localhost')
    parser.add_argument('-rp', '--restart-port', help='Restart a device port by telnet port number. e.g., "20000"', type=int)
    parser.add_argument('-rid', '--restart-id', help='Restart a device port by USB ID. e.g., "2-1.2.1"')
    parser.add_argument('-rap', '--reattach-port', help='Reattach a ttyUSB node by telnet port number. e.g., "20000"', type=int)
    parser.add_argument('-raid', '--reattach-id', help='Reattach a ttyUSB node by USB ID. e.g., "2-1.2.1"')
    parser.add_argument('-sbr', '--set-baud-rate', help='Specify a baud rate to update the USB port. Need with -sbr. e.g., "115200"', type=int)
    parser.add_argument('-sp', '--set-port', help='Specify a port for updating baud rate. Need with -sp. Set 0 is to use default rate. e.g., "20000"', type=int)

    args = parser.parse_args()
    server_ip = args.server_ip
    restart_port = args.restart_port
    restart_id = args.restart_id
    reattach_port = args.reattach_port
    reattach_id = args.reattach_id
    set_baud_rate = args.set_baud_rate
    set_port = args.set_port
    if not restart_port and not restart_id and not reattach_port and not reattach_id and not set_port:
        print "No arguments are specified"
        sys.exit(1)

    cmd_dict = None
    if restart_port:
        cmd_dict = {'cmd': 'restart_port', 'value': restart_port}
    elif restart_id:
        cmd_dict = {'cmd': 'restart_id', 'value': restart_id}
    elif reattach_port:
        cmd_dict = {'cmd': 'reattach_port', 'value': reattach_port}
    elif reattach_id:
        cmd_dict = {'cmd': 'reattach_id', 'value': reattach_id}
    elif set_port:
        cmd_dict = {'cmd': 'set_baud_rate', 'port': set_port, 'value': set_baud_rate}

    client = server_client(server_ip, port)
    client.connect()
    queue = client.get_queue()
    queue.put(cmd_dict)
