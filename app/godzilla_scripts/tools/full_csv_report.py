# -*- coding: utf-8 -*-
""" This script is used to collect test results from every buiulds then create a consolidated HTML table. 
"""
__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

import argparse
import ast
import os
import random
import requests
import string

class jen_job_inst():
    def __init__(self):
        self.name = None
        self.build_url_list = []


    def get_build_url(self, jenkins_url=None, jenkins_project=None, jen_job=None, num_build=None):
        # "num_build" is total number of builds of Jenkins job that want to collect.
        # http://10.195.249.121:8080/job/ibi/job/device_performance/job/50GB_slurp_empty_dev_010/13/artifact/results/
        # JOB_URL
        # jenkins_job = '{0}-{1}'.format(os.getenv('JOB_NAME', ''), os.getenv('BUILD_NUMBER', '')) # Values auto set by jenkins.
        # resp = requests.get('{}/job/ibi/job/{}/api/python'.format(jenkins_url, jen_job), timeout=30)

        resp = requests.get('{}/job/{}/{}/api/python'.format(jenkins_url, jenkins_project, jen_job), auth=(jenkins_username, jenkins_password), timeout=30)
        
        #print '{}/job/ibi/job/{}/api/python'.format(jenkins_url, jen_job)
        #print resp.content

        job_dict = ast.literal_eval(resp.content)
        # eq: build_url_list is like [http://10.195.249.121:8080/job/up_login_only/10/, ...]
        build_url_list = []
        index = 0
        while len(build_url_list) < int(num_build):
            # job_dict.get('builds') is a list
            if not job_dict.get('builds'):
                break
            build_url = job_dict.get('builds')[index].get('url')
            resp = requests.get("{}artifact/result.csv".format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
            #print resp.content
            if resp.status_code == 200:    
                build_url_list.append(build_url)
            index += 1
            if index == len(job_dict.get('builds')):
                break

        return build_url_list


    def get_build_test_result(self, build_url=None):
        result_csv = ''
        resp = requests.get('{}/artifact/result.csv'.format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
        if resp.status_code == 200:
            result_csv = resp.content.strip()

        return result_csv


    def get_build_timestamp(self, build_url):
        # eq: http://10.195.249.121:8080/job/up_login_only/8/buildTimestamp?format=yyyy/MM/dd
        resp = requests.get("{}/buildTimestamp?format=yyyy/MM/dd".format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
        return resp.content.strip()  # eq: 2019/02/24


class FullCsvReport():
    """docstring for ClassName"""
    def __init__(self, jenkins_url=None, csv_file_name=None):
        self.jenkins_url = jenkins_url
        self.csv_file_name = csv_file_name
        if head_csv != 'None' and head_csv != 'none':
            with open('{}'.format(self.csv_file_name), 'a') as f:
                f.write('{}\n'.format(head_csv))


    def main(self, jen_job_list=None, num_build=None):
        jen_job_dict = {}
        # Get info from different jenkins job respectively

        for jen_job in jen_job_list.split(','):
            if jen_job:
                # Creatre instance for every jenkins_job
                jen_job_dict[jen_job] = jen_job_inst()
                obj = jen_job_dict.get(jen_job)
                obj.name = jen_job

                obj.build_url_list = obj.get_build_url(jenkins_url=self.jenkins_url, jenkins_project=jenkins_project, jen_job=jen_job, num_build=num_build)

                # Get every build info from ONE Jenkins job
                # For every list, the scructure is like ['build_1_time', 'build_2_time', 'build_3_time', ...]
                for index, build_url in enumerate(obj.build_url_list):
                    print build_url
                    build_timestamp = obj.get_build_timestamp(build_url=build_url)
                    result_csv = obj.get_build_test_result(build_url=build_url)
                    print result_csv

                    # Generate a csv consolidated file
                    self.csv_table(jen_job_name=obj.name, result_csv=result_csv)


    def csv_table(self, jen_job_name=None, result_csv=None):
        print '\n\n ### Generate a csv table for {} ### \n\n'.format(jen_job_name)
        with open('{}'.format(self.csv_file_name), 'a') as f:
            f.write('{}\n'.format(result_csv))


def upload_popcorn_performance_report_to_server(file, popcorn_address='popcorn.wdc.com', release_name=None, project_name=None, jira_key=None):
    """The file is actually a csv file."""
    url = 'https://{0}/api/reports/performance'.format(popcorn_address)
    headers = {'X-POPCORN-KEY': randomString()}

    with open(file, "rb") as f:
        file_dict = {'files': (file, f)}
        data = {"releaseName": release_name,
                "projectName": project_name,
                "jiraKey": jira_key,
                }
        response = requests.post(url=url, files=file_dict, data=data, headers=headers)
        #response = requests.post(url=url, data=data, headers=headers)
        if not response.status_code == 200:
            print 'Upload csv fle to popcorn server failed !!!, response code:{0}, error log:{1}'.format(response.status_code, response.content)
        else:
            print 'Upload csv file to popcorn server successfully.'


def randomString(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse grafana_data_export.csv and create a simple table in HTML.\n')
    parser.add_argument('--jenkins_url', default='http://10.195.249.121:8080', help='http://10.195.249.121:8080')
    parser.add_argument('--jenkins_project', default='ibi', help='jenkins project name')
    parser.add_argument('--jenkins_username', default='admin', help='admin')
    parser.add_argument('--jenkins_password', default='Abcd1234!', help='Abcd1234!')
    parser.add_argument('--jen_job_list', default='up_login_only', help='Please check Jenkins projects')
    parser.add_argument('--num_build', default='7', help='number of builds')
    parser.add_argument('--head_csv', default='None', help='head for csv')
    parser.add_argument('--csv_file_name', default='consolidated_table.csv', help='file name of csv')
    parser.add_argument('--upload_csv_to_popcorn', help='upload csv file to popcorn', action='store_true')
    parser.add_argument('--popcorn_release_name', default=None, help='releaseName of firmware')
    parser.add_argument('--popcorn_project_name', default=None, help='projectName of Popcorn')
    parser.add_argument('--popcorn_jira_key', default=None, help='Jira test case')

    args = parser.parse_args()
    jenkins_url = args.jenkins_url
    jenkins_project = args.jenkins_project
    jenkins_username = args.jenkins_username
    jenkins_password = args.jenkins_password
    jen_job_list = args.jen_job_list
    num_build = args.num_build
    head_csv = args.head_csv
    csv_file_name = args.csv_file_name

    # For Popcorn
    upload_csv_to_popcorn = args.upload_csv_to_popcorn
    popcorn_release_name = args.popcorn_release_name
    popcorn_project_name = args.popcorn_project_name
    popcorn_jira_key = args.popcorn_jira_key

    object1 = FullCsvReport(jenkins_url=jenkins_url, csv_file_name=csv_file_name)
    object1.main(jen_job_list, num_build=num_build)

    
    if upload_csv_to_popcorn:
        upload_popcorn_performance_report_to_server(csv_file_name, release_name=popcorn_release_name, project_name=popcorn_project_name, jira_key= popcorn_jira_key)
    else:
        print "Don't upload csv file to Popcorn."