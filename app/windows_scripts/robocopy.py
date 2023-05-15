__author__ = 'Kurt Jensen <kurt.jensen@wdc.com'

import shlex
import subprocess
import argparse
import subprocess32
import re
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__),'..'))
from platform_libraries import common_utils
from platform_libraries.adblib import ADB

class Robocopy(object):

    def init(self):
        self.log = common_utils.create_logger()

    def roboCopy(self, source=None, destination=None):
        cmd = 'robocopy "%s" "%s" /E /NP /TEE /R:1 /LOG+:robolog.txt'%(source, destination)
        stdout, stderr = common_utils.executeCommand(cmd, consoleOutput=True)
        match = re.search(r'Speed :\s(.*)', stdout)
        if match:
            result =  match.group(1)
            self.log.info(' Speed: ' + result.strip())
        else:
            self.log.info('No speed found, robocopy error')

    def deleteFolder(filepath=None):
        cmd = 'rmdir %s /s /q' %(filepath)
        common_utils.executeCommand(cmd, consoleOutput=True, shell=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Test script to automate robocopy on windows')
    parser.add_argument('-source', help='Source filepath')
    parser.add_argument('-dest', help='Destination filepath')
    parser.add_argument('-iter', help='Number of iterations')
    parser.add_argument('-uut_ip', help='Device IP')
    args = parser.parse_args()

    source = args.source
    destination = args.dest
    iterations = int(args.iter)
    uut_ip = args.args.uut_ip
    adb = ADB(uut_ip=uut_ip)
    robo = Robocopy()

    ##### WRITE #####
    # Write to destination, log speed
    #for i in range(iterations):
    for i in xrange(0, iterations):
        robo.roboCopy(source=source, destination=destination)
        robo.deleteFolder(filepath=destination)




