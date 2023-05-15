# -*- coding: utf-8 -*-
""" This script is used to collect test results from every buiulds then create a consolidated HTML table. 
"""
__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

import argparse
import ast
import json
import os
import requests


class FullStatReport():
    """docstring for ClassName"""
    def __init__(self, jenkins_url=None):
        self.jenkins_url = jenkins_url
        self.html_style = '<style>#report, th, td {border: 1px solid black;border-collapse: collapse;text-align: left;padding: 7px; font-family: "Arial"; font-size: 14px;}caption{font-weight: bold; text-align: left;padding: 5px; color: #555;text-transform: uppercase;} .report-name{width: 180px;text-align: center;line-height: 46px;font-weight: bold;} .nav{color: #fff;background-color: #1976D2;height: 48px;font-family: "Arial"; font-size: 14px; } .left-column{text-transform: uppercase;background-color: #1976D2;color: #fff;}.right-column{background-color: #fff;color: #1A231E;} table.details th{background-color: #1976D2;color: #fff;} .more-details th{background-color: black!important;border: 1px solid white!important;} .passed{color: #2E8B57;} .passrate{font-weight: bold;} .failed{background-color: #DC143C; color: white;} .skipped{color: #FF7F50;} .failed_style_2{color: red; font-weight: bold;} .passed_style_2{color: green; font-weight: bold;}</style>'
        self.html_head = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Performance Automation Summary Report</title>{}</head>'.format(self.html_style)
        self.html_table_id = '<table id="report" class="details">'


    def main(self, jen_job_list=None, num_build=None):

        for jen_job in jen_job_list.split(','):
            if 'autobackup' in jen_job:
                self._autobackup(jenkins_url=jenkins_url, jenkins_project=jenkins_project, jen_job=jen_job, num_build=num_build)


    def _autobackup(self, jenkins_url=None, jenkins_project=None, jen_job=None, num_build=None):

        html_table_td = ''

        build_url_list = get_build_url(jenkins_url=jenkins_url, jenkins_project=jenkins_project, jen_job=jen_job, num_build=num_build)
        
        for index, build_url in enumerate(build_url_list):
            print build_url
            try:
                temp_JsonReport = get_build_test_result(build_url=build_url)

                # There may be more than 1 iteration in one build
                test_speed_list = []
  
                for element in temp_JsonReport:
                    if element == 'suites':
                        for sub_item in temp_JsonReport.get('suites')[0].get('tests'):
                            #if sub_item.get('name') == 'ibi-mobile-automation-ab-verify-backup-completed-in-foreground-test':
                            # For iOS
                            if 'ab-verify-backup-completed-in-foreground-test' in sub_item.get('name'):
                                print sub_item.get('name')
                                for step in sub_item.get('testReports').get('ab-turn-on-and-wait-completion-positive').get('steps'):
                                    if step.get('stepTestName') ==  'waitAutobackupCompleted':
                                        #print '####' * 20
                                        #print step
                                        #print step.get('speed')
                                        test_speed_list.append(step.get('speed'))
                            # For Android
                            elif 'verify-ab-completed-in-minutes-in-foreground-test' in sub_item.get('name'):
                                print sub_item.get('name')
                                for step in sub_item.get('testReports').get('ab-turn-on-and-wait-completion-positive').get('steps'):
                                    if step.get('stepTestName') ==  'waitAutobackupCompletedInMinutes':
                                        #print '####' * 20
                                        #print step
                                        #print step.get('speed')
                                        test_speed_list.append(step.get('speed'))

                    # Get "total files count" and "total size of data (MB)" in additiotnalInfo
                    elif element == 'executionSummary':
                        test_additional_info = temp_JsonReport.get('executionSummary').get('additionalInfo')
                        # This is hard code because the value is null.
                        test_additional_info = test_additional_info.replace('<li>iOS Version:null</li>', '')
                    elif element == 'iterations':
                        test_itr = temp_JsonReport.get('iterations')
                    elif element == 'build':
                        test_app_build = temp_JsonReport.get('build')
                    elif element == 'version':
                        test_app_ver = temp_JsonReport.get('version')
                    # project is to show MCH/ibi
                    elif element == 'project':
                        test_project = temp_JsonReport.get('project')
                    # platform is to show Android/iOS
                    if element == 'platform':
                        test_mobile_platform = temp_JsonReport.get('platform')
                    # To show qa/dev
                    #elif element == 'testEnvironment':
                    #    print temp_JsonReport.get('testEnvironment')

                test_time_stamp = get_build_timestamp(build_url)

                test_device_fw = get_build_env_var(build_url).get("DEVICE_FW")
                '''
                print 'test_time_stamp: {}'.format(test_time_stamp)
                print 'test_device_fw: {}'.format(test_device_fw)
                print 'test_app: {}-{}'.format(test_app_ver, test_app_build)
                print 'test_additional_info: {}'.format(test_additional_info)
                print 'test_itr: {}'.format(test_itr)
                print 'test_speed_list: {}'.format(test_speed_list)
                '''
                # html table (content)
                #print '#######  test_speed_list  #######'
                #print test_speed_list
                #print '#######  test_speed_list  #######'
                if test_speed_list:
                    html_table_td += '<tr>'
                    # For Date
                    html_table_td += '<td><a href="{}" target="_blank" >{}</a></td>'.format(build_url, test_time_stamp)
                    # For reamining contents
                    for td in [test_project, test_device_fw, test_mobile_platform, '{}-{}'.format(test_app_ver,test_app_build), test_additional_info, test_itr, "%.2f"%(sum(test_speed_list)/len(test_speed_list))]:
                        html_table_td += '<td>{}</td>'.format(td)
                    html_table_td += '</tr>'
            except Exception as e:
                print '\n\n\n\n      ###########'
                print e
                print "Please check following Jenkins build. It didn't execute successfully or UI framework report format is changed."
                print build_url
                print '      ###########\n\n\n\n'

        # html table head(title)
        html_table_th = '<tr>'
        for th in ['Date', 'Project', 'Device FW', 'Mobile Platform', 'App Version', 'Additional Info', 'Iterations', 'Autobackup Speed (MB/s)']:
            html_table_th+='<th>{}</th>'.format(th)
        html_table_th+='</tr>'

        # Create html_table for every single jenkins job
        html_table_summary = html_table_th + html_table_td
        self.html_table(jen_job_name=jen_job, html_table_summary=html_table_summary)


    def html_table(self, jen_job_name=None, html_acronym='', html_table_summary=None):
        print '\n\n ### Generate a HTML report for {} ### \n\n'.format(jen_job_name)
        html = '\n\n\n' + self.html_head + '\n' + '<b><font size=5 color="#8000ff">{}</font></b>'.format(jen_job_name.split('/')[-1]) + '\n' + html_acronym + '\n'+ self.html_table_id + '\n' + html_table_summary + '</table>' + '<div>&nbsp;</div>'
        with open('full_stat_report_ui.html', 'a') as f:
            f.write(html)


def get_build_env_var(build_url):
    resp = requests.get("{}/injectedEnvVars/api/python".format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
    env_var_dict = ast.literal_eval(resp.content)
    return env_var_dict.get('envMap')


def get_build_timestamp(build_url):
    # eq: http://10.195.249.121:8080/job/up_login_only/8/buildTimestamp?format=yyyy/MM/dd
    resp = requests.get("{}/buildTimestamp?format=yyyy/MM/dd".format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
    return resp.content.strip()  # eq: 2019/02/24


def get_build_test_result(build_url=None):
    JsonReport = ''
    resp = requests.get('{}/artifact/JsonReport.json'.format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
    if resp.status_code == 200:
        JsonReport = json.loads(resp.content.strip())
        #print JsonReport
    return JsonReport


def get_build_url(jenkins_url=None, jenkins_project=None, jen_job=None, num_build=None):
    # "num_build" is total number of builds of Jenkins job that want to collect.
    # http://10.195.249.121:8080/job/ibi/job/device_performance/job/50GB_slurp_empty_dev_010/13/artifact/results/
    # JOB_URL
    # jenkins_job = '{0}-{1}'.format(os.getenv('JOB_NAME', ''), os.getenv('BUILD_NUMBER', '')) # Values auto set by jenkins.
    resp = requests.get('{}/job/{}/job/{}/api/python'.format(jenkins_url, jenkins_project, jen_job), auth=(jenkins_username, jenkins_password), timeout=30)
    
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
        resp = requests.get("{}artifact/JsonReport.json".format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
        #print resp.content
        if resp.status_code == 200:    
            build_url_list.append(build_url)
        index += 1
        if index == len(job_dict.get('builds')):
            break
    return build_url_list




if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Parse grafana_data_export.csv and create a simple table in HTML.\n')
    parser.add_argument('--jenkins_url', default='http://10.195.249.121:8080', help='http://10.195.249.121:8080')
    parser.add_argument('--jenkins_project', default='ibi', help='jenkins project name')
    parser.add_argument('--jenkins_username', default='admin', help='admin')
    parser.add_argument('--jenkins_password', default='Abcd1234!', help='Abcd1234!')
    parser.add_argument('--jen_job_list', default='up_login_only', help='Please check Jenkins projects')
    parser.add_argument('--num_build', default='7', help='number of builds')
    args = parser.parse_args()
    jenkins_url = args.jenkins_url
    jenkins_project = args.jenkins_project
    jenkins_username = args.jenkins_username
    jenkins_password = args.jenkins_password
    jen_job_list = args.jen_job_list
    num_build = args.num_build


    object1 = FullStatReport(jenkins_url=jenkins_url)
    #object1.main(jen_job_list, num_build=num_build)
    object1.main(jen_job_list, num_build=num_build)
