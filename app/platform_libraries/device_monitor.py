__author__ = 'Kurt Jensen <kurt.jensen@wdc.com>'

from adblib import ADB
import logging
import common_utils
import threading
import os
import csv
import time
import logstash
import logging

# ADB class to connect to device with ADB over TCP and execute commands
class AndroidDeviceMonitor(object):

    def __init__(self, adb=None, platform='monarch'):
        self.adb=adb
        if platform != 'monarch':
            self.platform = 'pelican'
        else:
            self.platform = 'monarch'
        self.isRunning=False
        common_utils.setupLogstashLogger(loggerName='AndroidDeviceMonitor', tags=self.adb.uut_ip, host='10.104.130.130')
        self.log = logging.getLogger('AndroidDeviceMonitor')
    def run(self, interval=60):
        self.isRunning = True
        self.t1 = threading.Thread(target=self.collectMetrics, args=(interval,))
        self.t1.start()

    def stop(self):
        self.isRunning = False
        self.t1.join()

    def collectMetrics(self, interval=30):
        while self.isRunning:
            self.logTemperature(socTemp=self.getSocTemp(), hddTemp=self.getHddTemp())
            self.logVmstat(vmstat=self.getVmstat())
            self.logMpstat(mpstat=self.getMpstat())
            time.sleep(interval)

    def getSocTemp(self):
        cmd = 'cat /sys/class/thermal/thermal_zone0/temp'
        stdout, stderr = self.adb.executeShellCommand(cmd, consoleOutput=False)
        return int(stdout.strip()) / 1000.0

    def getHddTemp(self, path=None):
        # changed as of build 27
        #cmd = "smartctl --attribute /dev/block/sataa | busybox grep Temperature_Celsius | busybox rev | busybox cut -d' ' -f1 | busybox rev"
        cmd = "smartctl --attribute /dev/block/sataa | busybox grep Temperature_Celsius | busybox awk '{print $10}'"
        stdout, stderr = self.adb.executeShellCommand(cmd, consoleOutput=False)
        return int(stdout.strip())

    def getVmstat(self):
        cmd = 'vmstat | tail -n 1'
        stdout, stderr = self.adb.executeShellCommand(cmd, consoleOutput=False)
        vmList = stdout.strip().split()
        vmstat = {'swpd':vmList[2], 'free':vmList[3], 'buff':vmList[4], 'cache':vmList[5]}
        return vmstat

    def getMpstat(self):
        cmd = 'busybox mpstat | tail -n 1'
        stdout, stderr = self.adb.executeShellCommand(cmd, consoleOutput=False)
        mpList = stdout.strip().split()
        mpstat = {'usr':mpList[2], 'nice':mpList[3], 'sys':mpList[4], 'iowait':mpList[5],'irq':mpList[6], 'soft':mpList[7], 'steal':mpList[8], 'guest':mpList[9], 'idle':mpList[10]}
        return mpstat

    def logTemperature(self, socTemp=None, hddTemp=None):
        extra = {'SOC' : self.getSocTemp(), 'HDD' : self.getHddTemp()}
        self.log.info('temperature', extra=extra)

    def logMpstat(self, mpstat=None):
        extra = {'usr' : float(mpstat['usr']), 'nice':float(mpstat['nice']), 'sys':float(mpstat['sys']), 'iowait':float(mpstat['iowait']), 'irq':float(mpstat['irq']), 'soft':float(mpstat['soft']), 'steal':float(mpstat['steal']), 'guest':float(mpstat['guest']), 'idle':float(mpstat['idle'])}
        self.log.info('mpstat', extra=extra)

    def logVmstat(self, vmstat=None):
        extra = {'swpd':int(vmstat['swpd']), 'free': int(vmstat['free']), 'buff':int(vmstat['buff']), 'cache':int(vmstat['cache'])}
        self.log.info('vmstat', extra=extra)

    def outputMpstat(self, timestamp, mpstat=None):
        fileExists = os.path.isfile('output/adb/mpstat.csv')
        with open ('output/adb/mpstat.csv', 'a') as csvfile:
            headers = ['Timestamp', 'usr', 'nice', 'sys', 'iowait', 'irq', 'soft', 'steal', 'guest', 'idle']
            writer = csv.DictWriter(csvfile, delimiter=',', lineterminator='\n', fieldnames=headers)
            if not fileExists:
                writer.writeheader()
            writer.writerow({'Timestamp':timestamp, 'usr':mpstat['usr'], 'nice':mpstat['nice'], 'sys':mpstat['sys'], 'iowait':mpstat['iowait'], 'irq':mpstat['irq'], 'soft':mpstat['soft'], 'steal':mpstat['steal'], 'guest':mpstat['guest'], 'idle':mpstat['idle']})

    def outputVmstat(self, timestamp=None, vmstat=None):
        fileExists = os.path.isfile('output/adb/vmstat.csv')
        with open ('output/adb/vmstat.csv', 'a') as csvfile:
            headers = ['Timestamp', 'swpd', 'free', 'buff', 'cache']
            writer = csv.DictWriter(csvfile, delimiter=',', lineterminator='\n', fieldnames=headers)
            if not fileExists:
                writer.writeheader()
            writer.writerow({'Timestamp':timestamp, 'swpd':vmstat['swpd'], 'free': vmstat['free'], 'buff':vmstat['buff'], 'cache':vmstat['cache']})

    def outputTemps(self, timestamp=None, socTemp=None, hddTemp=None):
        fileExists = os.path.isfile('output/adb/temperature.csv')
        with open ('output/adb/temperature.csv', 'a') as csvfile:
            headers = ['Timestamp', 'SOC', 'HDD']
            writer = csv.DictWriter(csvfile, delimiter=',', lineterminator='\n', fieldnames=headers)
            if not fileExists:
                writer.writeheader()
            writer.writerow({'Timestamp':timestamp, 'SOC':socTemp, 'HDD': hddTemp})