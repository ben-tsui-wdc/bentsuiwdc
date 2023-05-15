# -*- coding: utf-8 -*-
""" This script is used to collect test results from every buiulds then create a consolidated HTML table. 
"""
__author__ = "Jason Chiang <Jason.Chiang@wdc.com>"

import argparse
import ast
import os
import requests


class jen_job_inst():
    def __init__(self):
        self.name = None
        self.build_url_list = []
        self.pass_criteria_dict = {}
        self.fail_string_list = []


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
            resp = requests.get("{}artifact/html_table_tds_summary".format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
            #print resp.content
            if resp.status_code == 200:    
                build_url_list.append(build_url)
            index += 1
            if index == len(job_dict.get('builds')):
                break
        return build_url_list


    def get_build_test_result(self, build_url=None):
        html_acronym = ''
        html_table_th_summary = ''
        html_table_tds_summary = ''
        resp = requests.get('{}/artifact/html_acronym'.format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
        if resp.status_code == 200:
            html_acronym = resp.content.strip()
        resp = requests.get('{}/artifact/html_table_th_summary'.format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
        if resp.status_code == 200:
            html_table_th_summary = resp.content.strip()
        resp = requests.get('{}/artifact/html_table_tds_summary'.format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
        if resp.status_code == 200:
            html_table_tds_summary = resp.content.strip()
        return html_acronym, html_table_th_summary, html_table_tds_summary


    def get_build_timestamp(self, build_url):
        # eq: http://10.195.249.121:8080/job/up_login_only/8/buildTimestamp?format=yyyy/MM/dd
        resp = requests.get("{}/buildTimestamp?format=yyyy/MM/dd".format(build_url), auth=(jenkins_username, jenkins_password), timeout=30)
        return resp.content.strip()  # eq: 2019/02/24


class FullStatReport():
    """docstring for ClassName"""
    def __init__(self, jenkins_url=None):
        self.jenkins_url = jenkins_url
        self.html_style = '<style>#report, th, td {border: 1px solid black;border-collapse: collapse;text-align: left;padding: 7px; font-family: "Arial"; font-size: 14px;}caption{font-weight: bold; text-align: left;padding: 5px; color: #555;text-transform: uppercase;} .report-name{width: 180px;text-align: center;line-height: 46px;font-weight: bold;} .nav{color: #fff;background-color: #1976D2;height: 48px;font-family: "Arial"; font-size: 14px; } .left-column{text-transform: uppercase;background-color: #1976D2;color: #fff;}.right-column{background-color: #fff;color: #1A231E;} table.details th{background-color: #1976D2;color: #fff;} .more-details th{background-color: black!important;border: 1px solid white!important;} .passed{color: #2E8B57;} .passrate{font-weight: bold;} .failed{background-color: #DC143C; color: white;} .skipped{color: #FF7F50;} .failed_style_2{color: red; font-weight: bold;} .passed_style_2{color: green; font-weight: bold;}</style>'
        self.html_head = '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><title>Performance Automation Summary Report</title>{}</head>'.format(self.html_style)
        self.html_table_id = '<table id="report" class="details">'


    def main(self, jen_job_list=None, num_build=None):
        jen_job_dict = {}
        # Get info from different jenkins job respectively

        for jen_job in jen_job_list.split(','):
            # Creatre instance for every jenkins_job
            jen_job_dict[jen_job] = jen_job_inst()
            obj = jen_job_dict.get(jen_job)
            obj.name = jen_job

            obj.build_url_list = obj.get_build_url(jenkins_url=self.jenkins_url, jenkins_project=jenkins_project, jen_job=jen_job, num_build=num_build)

            # Get every build info from ONE Jenkins job
            # For every list, the scructure is like ['build_1_time', 'build_2_time', 'build_3_time', ...]
            html_table_th_summary = ''
            html_table_tds_summary = ''
            temp_html_table_th_summary = ''
            temp_html_table_tds_summary = ''
            for index, build_url in enumerate(obj.build_url_list):
                print build_url
                build_timestamp = obj.get_build_timestamp(build_url=build_url)
                temp_html_acronym, temp_html_table_th_summary, temp_html_table_tds_summary = obj.get_build_test_result(build_url=build_url)
                # Chooese newest html_table_th_summary as fixed html_table_th_summary 
                if index == 0:  # Use newest html_acronym and html_table_th_summary as fianl html_acronym and html_table_th_summary
                    html_acronym = temp_html_acronym
                    html_table_th_summary = '<tr><th>date</th>{}</tr>'.format(temp_html_table_th_summary)
                # Append the html_table_tds_summary
                html_table_tds_summary = html_table_tds_summary + '<tr><td><a href="{}" target="_blank" >{}</a></td>{}</tr>'.format(build_url, build_timestamp, temp_html_table_tds_summary)
            
            # Generate a HTML table
            self.html_table(jen_job_name=obj.name, html_acronym=html_acronym, html_table_summary=html_table_th_summary+html_table_tds_summary)


    def html_table(self, jen_job_name=None, html_acronym=None, html_table_summary=None):
        print '\n\n ### Generate a HTML report for {} ### \n\n'.format(jen_job_name)
        html = '\n\n\n' + self.html_head + '\n' + '<b><font size=5 color="#8000ff">{}</font></b>'.format(jen_job_name.split('/')[-1]) + '\n' + html_acronym + '\n'+ self.html_table_id + '\n' + html_table_summary + '</table>' + '<div>&nbsp;</div>'
        with open('full_stat_report.html', 'a') as f:
            f.write(html)


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
    object1.main(jen_job_list, num_build=num_build)