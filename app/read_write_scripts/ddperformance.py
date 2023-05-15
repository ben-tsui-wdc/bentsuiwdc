__author__ = 'Kurt Jensen <kurt.jensen@wdc.com>'

import junit_xml
#from adb import adblib
from .. import adb
import argparse
import os
import time
import re
from glob import glob

class Test():
    def __init__(self):        

        example1 = '\n  python ddperformance.py -uut_ip 192.168.1.1 -port 22 -fpath /mnt/HD/HD_a2/testfile -fsize 1073741824 iter 5'
        
        # Create usages
        parser = argparse.ArgumentParser(description='*** dd testing on Realtek ***\n\nExamples:{0}'.format(example1),formatter_class=argparse.RawTextHelpFormatter)
        parser.add_argument('-uut_ip', help='Destination NAS IP address, ex. 192.168.1.45')        
        parser.add_argument('-port', help='Destination adb port, ex. 22')
        parser.add_argument('-fpath', help='Testfile filepath on Nas, ex. /mnt/HD/HD_a2/testfile')
        parser.add_argument('-fsize', help='Filesize in bytes, ex. 1073741824')
        parser.add_argument('-iter', help='Number of iterations per blocksize, ex. 5')
        args = parser.parse_args()

        #If user didn't enter ip,port, use os.environ['DEVICE_IP']
        if not args.uut_ip:
            print "DEVICE IP: ",os.environ['DEVICE_IP']
            self.uut_ip = os.environ['DEVICE_IP'] 
            print "SSH PORT: ",os.environ['SSH_PORT']
            self.port = int(os.environ['SSH_PORT']) 
        else:
            self.uut_ip = args.uut_ip
            self.port = int(args.port)

        if not args.fsize:
            self.filesize = 1073741824 # bytes or 1 GB
        else:
            self.filesize = int(args.fsize)
            
        self.uut_ip = self.uut_ip.split(':')[0]
        print "UUT_IP: ",self.uut_ip
        
        env = os.environ.get('CLOUD_SERVER')
        DEVICE_FW = os.environ.get('FW_VER')
        if not env:
            env = 'qa1'
        self.adb = adblib.ADB(uut_ip=self.uut_ip, port='5555')
        self.fpath = args.fpath
        self.iterations = int(args.iter) # number of iterations per blocksize
        self.command = 'adb shell dd' # direct output to stdout instead of stderr, and direct stdout to /dev/null
        self.properties = {'Device IP': self.uut_ip, 'Device adb port': self.port, 'CLOUD_ENV': env, 'DEVICE_FW': DEVICE_FW,'COMMAND': self.command, 'Filesize': self.filesize, 'Iterations': self.iterations}
        self.adb.connect()

    def run(self):
        start = time.time()
        testCases = []
        # initial block 512 bytes
        block = 512
        # loop until 64 MB block size
        while block < 67108865:
            # loop each block size 5 times to calculate mean read and write speeds
            write_sum = 0
            read_sum = 0
            for x in xrange(0,self.iterations):
                
                #calculate number of blocks for defined filesize
                count = self.filesize / block
                
                # if block size > filesize
                if count < 1:
                    count = 1
                    
                # write command
                self.command = 'adb shell dd if=/dev/zero of=' + self.fpath + ' bs='+ str(block) +' count=' + str(count) + ' 2>&1 1>/dev/null'
                dd_write_result = self.adb.executeCommand(cmd=self.command, timeout=1000)
                write_speed = self.parse_speed(dd_write_result)
                write_sum += self.parse_num(write_speed)
                print 'Blocksize(bytes): '+ str(block) + ' Write Speed: ' + write_speed
                
                # read command
                self.command = 'adb shell dd if=' + self.fpath + ' of=/dev/null bs='+ str(block)+ ' 2>&1 1>/dev/null'
                dd_read_result = self.adb.executeCommand(cmd=self.command, timeout=1000)
                read_speed = self.parse_speed(dd_read_result)
                read_sum += self.parse_num(read_speed)
                print 'Blocksize(bytes): '+ str(block) + ' Read Speed: ' + read_speed
                
                # remove testfile
                self.command = 'rm -f ' + self.fpath
                self.adb.executeCommand(cmd=self.command)
                
            # get mean write/read speed for defined number of iterations at this blocksize    
            mean_write_speed, mean_read_speed = self.get_mean(write_sum, read_sum)
            
            tc = junit_xml.TestCase(name=str(block), metrics=self.set_metric(mean_write_speed, mean_read_speed))
            testCases.append(tc)   
             
            print 'Blocksize(bytes): ' + str(block) + ' Mean Read Speed: ' + str(mean_read_speed)+ ' Mean Write Speed: ' +  str(mean_write_speed)
            print '\n'
            block = block * 2
        
        ts = junit_xml.TestSuite("dd perf tests", test_cases=testCases, properties=self.properties, timestamp=time.time())
        print junit_xml.TestSuite.to_xml_string([ts])
        
        with open('output.xml', 'w') as f:
            junit_xml.TestSuite.to_file(f, [ts], prettyprint=True)
                
        print "*** ddtest completed ***\n"    
        self.adb.disconnect()

    def set_metric(self, meanWrite = None, meanRead = None):
        metrics = [
            {"metric" : "meanWriteSpeed", "value" : str(meanWrite), "units" : "MBs"},
            {"metric" : "meanReadSpeed", "value" : str(meanRead), "units" : "MBs"}
        ]
        return metrics
            
    def get_mean(self, write = None, read = None):
        return write / self.iterations, read / self.iterations
        
    def parse_speed(self, result = None):
        result = re.search('[0-9.]+([MGk]?B|bytes)/s(ec)?', str(result))
        if result:
            speed = result.group(0)
            return speed
        else:
            return result
    
    def parse_num(self, speed = None):
        result = re.search('\d+\.\d+', speed)
        if result:
            num = result.group(0)
        return float(num)
            

test = Test()
test.run()