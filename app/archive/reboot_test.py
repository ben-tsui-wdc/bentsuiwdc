___author___ = 'Kurt Jensen <kurt.jensen@wdc.com>'

from platform_libraries.adblib import ADB
import time
import argparse
import threading 

class Reboot(object):
    def __init__(self, adb=None):
        self.adb = adb
        self.isRunning = False

    def run(self, iterations=1):
        self.t1 = threading.Thread(target=self.rebootTest, args=(iterations,))
        self.t1.start()
        self.isRunning = True

    def stop(self):
        self.isRunning = False
        print 'Waiting for reboot thread..'
        self.t1.join()
        self.adb.disconnect()

    def rebootTest(self, iterations=1):
        """ Connect to device, execute reboot, disconnect via adb and attempt to reconnect after reboot """
        self.adb.connect()
        for i in range(0, iterations):
            print 'Iteration: %i' %(i)
            stdout, stderr = self.adb.executeShellCommand('reboot', consoleOutput=False, timeout=15)
            time.sleep(2)
            self.adb.disconnect()
            time.sleep(45)
            for j in range(0, 10):
                print 'Attempt to connect %i' %(j)
                try:
                    self.adb.connect(timeout=10)
                except Exception:
                    print 'adb not connecting'
                    time.sleep(5)
                if self.adb.connected:
                    break
            if j > 8:
                print 'device not responding'
                break

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Reboot test')
    parser.add_argument('-uut_ip', help='Destination IP address, ex. 192.168.203.14')
    parser.add_argument('-port', help='Destination port number, ex. 5555 (default)')
    parser.add_argument('-iter', help='Number of iterations, ex. 100')
    args = parser.parse_args()

    uut_ip = args.uut_ip

    if args.port:
        port = args.port
    else:
        port = '5555'
    if args.iter:
        iterations = int(args.iter)
    else:
        iterations = 1

    adb = ADB(uut_ip=uut_ip, port='5555')

    reboot = Reboot(adb=adb)
    reboot.run(iterations=iterations)
    reboot.stop()


