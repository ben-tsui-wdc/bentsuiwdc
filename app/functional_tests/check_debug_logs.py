# -*- coding: utf-8 -*-
""" Test cases to check debug logs [KAM-21695]
"""
__author__ = "Vodka Chen <vodka.chen@wdc.com>"

# std modules
import sys
import urllib2
import os
import shutil
import zipfile
import stat
import time

# platform modules
from middleware.arguments import InputArgumentParser
from middleware.test_case import TestCase
from platform_libraries.compare import local_md5sum

class CheckDebugLogs(TestCase):

    TEST_SUITE = 'Functional Test'
    TEST_NAME = 'Check debug logs'
    # Popcorn
    TEST_JIRA_ID = 'KAM-21695'

    SETTINGS = {
        'uut_owner': False
    }

    def init(self):
        self.MAX_RETRIES = 5
        self.downloadURL = "http://" + self.env.uut_ip + ":33284/cgi-bin/logs.sh"
        self.downloadDir = os.getcwd() + "/debug_log"
        self.downloadFile = self.downloadDir + "/debug_logs.zip"
        self.logDir = '/data/wd/diskVolume0/debug_logs'

    def before_test(self):
        self.log.info('Check Debug Logs: Clear download folder')
        if os.path.exists(self.downloadDir):
            shutil.rmtree(self.downloadDir)
        os.makedirs(self.downloadDir)

        # To ensure logs are moved into /data/wd/diskVolume0/debug_logs
        self.adb.executeShellCommand("move_upload_logs.sh -a")
        self.adb.executeShellCommand("move_upload_logs.sh -n")

        self.log.info('Check if there are logs in "/data/wd/diskVolume0/debug_logs" in testing device.')
        stdout, stderr = self.adb.executeShellCommand('ls /data/wd/diskVolume0/debug_logs')
        if not stdout:
            raise self.err.TestFailure('There is not any log in "/data/wd/diskVolume0/debug_logs" in testing device.')

    def download_and_decompress_logs(self):
        self.log.info('Start to download log file (debug_logs.zip)... ')
        try:
            response = urllib2.urlopen(self.downloadURL)
            fh = open(self.downloadFile, "w")
            fh.write(response.read())
            fh.close()
        except urllib2.URLError as e:
            self.log.error('Check Debug Logs: Download log file (debug_logs.zip) fail')
            self.log.error(e)
            return False

        if os.path.isfile(self.downloadFile):
            try:
                with zipfile.ZipFile(self.downloadFile, "r") as zip_ref:
                    zip_ref.extractall(self.downloadDir)
            except zipfile.BadZipfile:
                self.log.error('File is not a zip file')
                return False
            except Exception as e:
                self.log.error(e)
                return False
        else:
            self.log.error('Check Debug Logs: log file (debug_logs.zip) missing')
            return False
        return True

    def test(self):
        self.log.info('downloadDir :{}'.format(self.downloadDir))
        self.log.info('downloadURL :{}'.format(self.downloadURL))
        # Download and decompress log file
        retry = 1
        while retry <= self.MAX_RETRIES:
            result = self.download_and_decompress_logs()
            self.log.info("iteration #{} download/decompress result :{}".format(retry, result))
            if not result:
                self.log.warning("Failed to download and decompress log file, remaining {} retries".format(retry))
                retry += 1
                time.sleep(60)
            else:
                break
        if not result:
            raise self.err.TestFailure('Failed to download/decompress debug_log file.')

        os.remove(self.downloadFile)

        # Check log directory content
        saveFiles = []

        for root, dirs, files in os.walk(self.downloadDir, topdown=False):
            for name in files:
                saveFiles.append(os.path.join(root, name))

        # Check log file permission and md5 checksum
        for logfile in saveFiles:
            mode = os.lstat(logfile)[stat.ST_MODE]
            # self.log.info(logfile)
            if not mode & stat.S_IROTH:
                self.log.error('Check Debug Logs: log file permission error')
                self.log.error(logfile)
                raise self.err.TestFailure('Check Debug Logs: log file permission error')
            sourceFile = logfile.split("/")
            arrLength = len(sourceFile)
            sourceFileFullPath = self.logDir + "/" + sourceFile[arrLength-2] + "/" + sourceFile[arrLength-1]
            # self.log.info('fullPath={}'.format(sourceFileFullPath))
            sourceFile_md5sum = self.adb.executeShellCommand('busybox md5sum {}'.format(sourceFileFullPath),
                                    consoleOutput=False)[0].strip().split()[0]
            downloadFile_md5sum = local_md5sum(logfile)
            # self.log.info('source_md5sum={}, downloadFile_md5sum={}'.format(sourceFile_md5sum, downloadFile_md5sum))
            if sourceFile_md5sum != downloadFile_md5sum:
                self.log.error('Check Debug Logs: Content md5sum is incorrect.')
                self.log.error(logfile)
                raise self.err.TestFailure('Check Debug Logs: Failed')

        #Check log file count
        saveLogCount = len(saveFiles)
        logCount = self.adb.executeShellCommand('find {0} -type f | wc -l '.format(self.logDir))[0]
        self.log.info('logCount:{}'.format(logCount))
        self.log.info('saveLogCount:{}'.format(saveLogCount))

        if saveLogCount != int(logCount):
            raise self.err.TestFailure('Check Debug Logs: log file count does not match.')

    def after_test(self):
        if os.path.exists(self.downloadDir):
            shutil.rmtree(self.downloadDir)
        self.log.info('Check Debug Logs: Clear download folder')

if __name__ == '__main__':
    parser = InputArgumentParser("""\
        *** Check debug logs Script ***
        Examples: ./run.sh functional_tests/check_debug_log.py --uut_ip 10.92.224.68 \
        """)

    test = CheckDebugLogs(parser)
    resp = test.main()
    print 'test response: {}'.format(resp)
    if resp:
        sys.exit(0)
    sys.exit(1)
