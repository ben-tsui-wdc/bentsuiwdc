# @ Author: Philip Yang <philip.yang@wdc.com>
# -*- coding: utf-8 -*-
# coding=utf-8

# std modules
import json
import os
import sys
import time
import urllib
import commands
import datetime
from itertools import count

# 3rd party modules
import requests
from pprint import pformat

# platform modules
import common_utils
from constants import GlobalConfigService as GCS
from platform_libraries.cloud_api import CloudAPI, HTTPRequester
from platform_libraries.constants import Kamino
from platform_libraries.pyutils import partial_read_in_chunks, read_in_chunks, retry

'''
Note:
    In sumologic forum, there has a talk when user query job result and receive 404 "Job not found".
    404 status is generated in these two situations:
        When cookies are disabled.
        When a query session is canceled.
'''

class sumologicAPI(HTTPRequester):


    def __init__(self, fixed_corid=None, stream_log_level=None):
        self.token = "c3U1NkRSSEJIYWV0eEs6cGF4Z3lKbHpVemxjZ0prN1k0U1Z3eTRzWWp0ZlY0SU1pbVFFRGIzdnRmQldVck40YmhtY3NtcWNKbG5pcUlVMA=="
        self.access_id = "su56DRHBHaetxK"
        self.access_key = "paxgyJlzUzlcgJk7Y4SVwy4sYjtfV4IMimQEDb3vtfBWUrN4bhmcsmqcJlniqIU0"
        self.log = common_utils.create_logger(stream_log_level=stream_log_level)
        #super(Environment, self).__init__(log_inst=self.log, fixed_corid=fixed_corid)
        self.fixed_corid = fixed_corid
        self.sumoURL = "https://api.us2.sumologic.com/api/v1/search/jobs"
        self.jobID = ""
        self.MAX_RETRIES = 5
        self.toTime = None
        self.fromTime = None

    def sendRQ(self, _adb_client=None, searching="_sourceCategory=qa1/device/yodaplus/LogUploader AND 1557195855_match_3729b869c1cfa1b1d5a838fb1dd368e0_093dfd14", relativeTime=10, timezone="GMT"):
        '''
        Send request to sumologic and recevie job ID.
        Attention: the searching string cannot be null. You would get 400 "No query parameter was provided."

        Standard format:
            POST https://api.us2.sumologic.com/api/v1/search/jobs

            header
                Authorization : Basic [base64 encoded Access_ID:access_key]
                Content-Type : Application/json
                Accept :  Application/json

            Body
                query : [sumologic searching method]
                timeZone : [timeZone] refer to wikipedia
                from : [fromTime]
                to : [toTime]

            Respond
                id : [job id] which job id would expired a few minutes.

        cURL format:
            curl -v -u 'su56DRHBHaetxK:paxgyJlzUzlcgJk7Y4SVwy4sYjtfV4IMimQEDb3vtfBWUrN4bhmcsmqcJlniqIU0' \
                -X POST -H "Content-Type: application/json" -H 'accept: application/json' \
                -d '{"query":"_sourceCategory=qa1/device/yodaplus/LogUploader", "from":"2019-04-30T02:49:50", "to":"2019-04-30T02:50:47", "timeZone": "GMT" }' \
                'https://api.us2.sumologic.com/api/v1/search/jobs'
        '''

        if self.toTime == None and self.fromTime == None:
            self.toTime = (_adb_client.executeShellCommand('date +"%Y-%m-%dT%H:%M:%S"', timeout=10)[0]).rstrip()
            timemachine = datetime.datetime.strptime(self.toTime, '%Y-%m-%dT%H:%M:%S') - datetime.timedelta(minutes=relativeTime)
            self.fromTime = timemachine.strftime("%Y-%m-%dT%H:%M:%S")
            self.log.info("fromTime: %s" %self.fromTime)
            self.log.info("toTime: %s" %self.toTime)

        #self.log.debug("Searching Rules = %s " %searching)

        try:
            myHeaders = {'Content-type': 'application/json', 'Accept': 'application/json'}
            payload = '{ "query" : "%s", \
                        "from" : "%s", \
                        "to":  "%s", \
                        "timeZone": "%s" }'%(searching, self.fromTime, self.toTime, timezone)

            data = json.loads(payload)
            self.log.debug("Searching rules: %s" %data["query"])

            res = requests.post(url=self.sumoURL, data=payload, auth=(self.access_id, self.access_key), headers=myHeaders)
            self.log.debug(res.status_code)
            if res.status_code == 202:
                res_data = res.json()
                self.log.debug("We got Job ID: %s"  %res_data["id"])
                self.jobID = res_data["id"]
                self.log.debug("Also we got URL: %s" %res_data["link"] )
                return res_data["id"]
            else:
                self.log.error("Failed to get Job ID.")
        except requests.RequestException:
            raise Exception('Failed to send a request in sendRQ steps.')

    def queryRQ(self, query_jobID):
        '''
        Auto parsing self.jobID is empty or not.
        When self.jobID is exist, we would pick it up prior to query_jobID.

        Standard format:
            GET https://api.us2.sumologic.com/api/v1/search/jobs/[job id]

            header
                Authorization : Basic [base64 encoded Access_ID:access_key]
                searchJobId [job id]  
                Accept :  Application/json

        cURL format:
            curl -v --trace-ascii - -b cookies.txt -c cookies.txt \
                -H 'Accept: application/json' -H 'searchJobId: 3BF540263DB5A350' \
                -u 'su56DRHBHaetxK:paxgyJlzUzlcgJk7Y4SVwy4sYjtfV4IMimQEDb3vtfBWUrN4bhmcsmqcJlniqIU0' \
                https://api.us2.sumologic.com/api/v1/search/jobs/3BF540263DB5A350

        '''

        if query_jobID == "":
            raise Exception('Please send a target ID to query_jobID which parameter cannot be empty.')
        else:
            self.jobID = query_jobID
        try:
            searchingURL = "https://api.us2.sumologic.com/api/v1/search/jobs/%s" %self.jobID
            self.log.debug(searchingURL)
            myHeaders = {'searchJobId': self.jobID, 'Accept': 'application/json'}

            self.log.debug("Search Job: %s" %myHeaders['searchJobId'])

            # self._touch_cookies() #create cookies.txt
            # res = requests.get(url=searchingURL, auth=(self.access_id, self.access_key), headers=myHeaders, cookies="./temp/cookies.txt")

            res = requests.get(url=searchingURL, auth=(self.access_id, self.access_key), headers=myHeaders)
            self.log.info("Job Status Code: %d"%res.status_code)

            res_data = res.json()
            self.log.info("Job State: %s"%res_data["state"])
            self.log.info("Job messagecount: %s" %res_data["messageCount"])

            return res_data
        except requests.RequestException as ex:
            raise Exception('Failed to send a request in sendRQ steps: {}'.format(ex))

    def searchRQ(self, _adb_client=None, searching="_sourceCategory=qa1/device/yodaplus/LogUploader AND 1557195855_match_3729b869c1cfa1b1d5a838fb1dd368e0_093dfd14", relativeTime=10, timezone="GMT", MAX_RETRIES=None):
        try:
            retry = 1
            if not MAX_RETRIES:
                MAX_RETRIES = self.MAX_RETRIES
            while retry <= MAX_RETRIES:
                jobID = self.sendRQ(_adb_client=_adb_client, searching=searching, relativeTime=relativeTime, timezone=timezone)
                self.log.info("jobID: %s" %jobID)
                self.log.debug("******************  Send Request Checked *****************")
                result = self.queryRQ(jobID)
                counter = int(result["messageCount"])
                self.log.info(result)
                self.log.debug("******************  Query Result Checked *****************")

                if not counter > 0:
                    self.log.warning("Failed to get message count, remaining {} retries".format(retry))
                    time.sleep(60)
                    retry += 1
                else:
                    break

            self.toTime = None
            self.fromTime = None
            return result
        except Exception as ex:
            self.log.error("Failed to send sumologic API: {}".format(ex))

    def _touch_cookies(self):
        basedir = os.path.dirname("./temp/")
        if not os.path.exists(basedir):
            os.makedirs(basedir)
        with open("./temp/cookies.txt", 'a'):
            os.utime("./temp/", None)


if __name__ == '__main__':
    test = sumologicAPI()
    test.queryRQ(test.sendRQ())