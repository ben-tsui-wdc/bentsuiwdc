__author__ = 'Kurt Jensen <Kurt.Jensen@wdc.com'

from monsoon import Monsoon
import time
import threading
import os.path
import csv
import os
import errno
import common_utils
import requests 
import logging

# Wrapper for the monsoon.py library, should be imported for logging current and timestamp from connected device
class MonsoonWrapper(object):
    
    def __init__(self, device=None, serialno=None, prometheusDevice='monarch_pm'):
        common_utils.makeOutputDirectory(outputDir='output/power')
        self.mon = Monsoon(device=device)
        self.prometheusDevice = prometheusDevice
        print 'Connected to monsoon power monitor'
        self.mon._FlushInput()

    def startDataLogging(self, hz=5, prometheusUpload=False, logstashUpload=False):
        """ Start thread for data collection, default 1hz """
        self.prometheus = prometheusUpload
        self.logstashUpload = logstashUpload
        common_utils.setupLogstashLogger(loggerName='monsoon_logstash', tags='monsoon')
        self.log = logging.getLogger('monsoon_logstash')
        self.t = threading.Thread(target=self.collectAndLogData, args=(hz,))
        self.t.start()
        self.isRunning = True

    def stopDataLogging(self):
        """ End thread for data collection, set Vout=0, disable USBpassthrough and flush serial input """
        """ time.sleep(2) is necessary to wait for device to respond to serial communication """
        self.isRunning = False
        self.t.join()
        print 'End power data collection'
        self.mon._FlushInput()
        time.sleep(2)
        self.mon.StopDataCollection()
        time.sleep(2)
        self.setOutputValues(usb=0, vout=0)
        time.sleep(2)
        self.mon._FlushInput()
        time.sleep(2)
        if (self.prometheus):
            self.stopUploadToPrometheus(amps=0)

    def collectAndLogData(self, hz=5):
        """ Get monsoon device status, set Vout, begin data collection """
        """ Hz = 5, default 5 data points per second, usb=2 default auto usbpassthrough, 0=off, 1=on """
        if(hz == 1 and self.prometheus):
            self.prometheus = True
        else:
            self.prometheus = False
            print 'Not uploading to prometheus server'
        if(hz ==1 and self.logstashUpload):
            self.logstashUpload = True
        else:
            self.logstashUpload = False
        # Monsoon collects data at 5000hz
        native_hz = 5000.0
        self.mon.StartDataCollection()
        time.sleep(2)

        print 'Starting power data collection'

        collectedSamples = []
        while self.isRunning:
            samplesNeededForAverage = (native_hz) / hz
            samplesNeededForAverage = int(samplesNeededForAverage)
            if samplesNeededForAverage > len(collectedSamples):
                sample = self.mon.CollectData()
                if not sample:
                    break
                collectedSamples.extend(sample)
            else:
                thisSampleAverage = sum(collectedSamples[:samplesNeededForAverage]) / samplesNeededForAverage
                self.csvOutput(current=thisSampleAverage, time=(time.time()))
                if(self.prometheus):
                    self.uploadToPrometheus(amps=thisSampleAverage)
                if(self.logstashUpload):
                    self.log.info('monsoon', extra = {'amps':float(thisSampleAverage)})
                collectedSamples = []

    def setOutputValues(self, usb=2, vout=3.7, maxCurrent=8):
        """
        Set USB Passthrough, Vout, and Max Current values for connected Monsoon Power Monitor 
        usb=0 off, usb=1 on, usb=2 auto
        """
        if maxCurrent > 8:
            maxCurrent = 8
        self.mon.SetMaxCurrent(maxCurrent)
        time.sleep(2)
        self.mon.SetUsbPassthrough(usb)
        print 'USB Passthrough set: %f' %usb
        time.sleep(2)
        self.mon.SetVoltage(vout)
        print 'Voltage output set:  %f' %vout
        time.sleep(2)
        
    def getStatus(self):
        status = self.mon.GetStatus()
        return status

    def uploadToPrometheus(self, url='http://autometrics.wdmv.wdc.com:9091/metrics/job/powertest/device/', amps=0):
        postUrl = url + self.prometheusDevice
        data = 'amps ' + str(amps) + '\n' # RETURN CHARACTER REQUIRED FOR SUCCESSFULL POST, otherwise 500 error
        requests.post(url=postUrl, data=data)

    def stopUploadToPrometheus(self, url='http://autometrics.wdmv.wdc.com:9091/metrics/job/powertest/device/', amps=0):
        postUrl = url + self.prometheusDevice
        data = 'amps ' + str(amps) + '\n' # RETURN CHARACTER REQUIRED FOR SUCCESSFULL POST, otherwise 500 error
        requests.post(url=postUrl, data=data)
        # Delete data so it is no longer graphed
        requests.delete(url=postUrl)

    def csvOutput(self, current=None, time=None):
        fileExists = os.path.isfile('output/power/monsoon_output.csv')
        with open ('output/power/monsoon_output.csv', 'a') as csvfile:
            headers = ['Timestamp', 'Amps']
            writer = csv.DictWriter(csvfile, delimiter=',', lineterminator='\n', fieldnames=headers)
            if not fileExists:
                writer.writeheader()
            writer.writerow({'Timestamp': time, 'Amps' : current})

    def makeOutputDirectory(self, outputDir=None):
        try:
            os.makedirs(outputDir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise


        