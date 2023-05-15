# -*- coding: utf-8 -*-
# std modules
import datetime
import logging
import json
import os
import signal
import subprocess
import sys
import time
from argparse import ArgumentParser
# 3rd party modules
import colorlog
import jenkins
import requests
import xml.etree.ElementTree as ET
# jenkins scripts
imported_ui_log_parser = True
try:
    import ui_log_parser
except:
    imported_ui_log_parser = False


JOB_MINITOR_INTERVAL_TIME = 30
MAXIMUM_BUIILD_WAITING_TIME = 60*10
MAXIMUM_RETRY_BUIILDS = 10
RETRY_BUIILD_INTERVAL_TIME = 60*5
DELAY_BUIILD_TIME = 30*60

POPCORN_JENKINS_URL = 'http://10.92.234.110:8080'
POPCORN_JENKINS_JOB = 'Tools/upload_results_to_popcorn'
POPCORN_JENKINS_JOB_TOKEN = 'Automation'


class JobRunner:

    def __init__(self, parser):
        # Params
        self.config_path = parser.execute_config
        self.server_url = parser.server_url
        self.target_time = parser.target_time
        self.target_build = parser.target_build
        self.target_pass_build = parser.target_pass_build
        self.target_iteration = parser.target_iteration
        self.target_pass = parser.target_pass
        self.username = parser.username
        self.password = parser.password
        self.stop_all = parser.stop_all
        self.build_gate_time = self.gate_time = parser.gate_time
        self.rest_time = parser.rest_time
        self.print_html_report_urls = parser.print_html_report_urls
        self.disable_parser = parser.disable_parser
        self.parse_with_suite_name = parser.parse_with_suite_name
        self.disable_punish_fail_test = parser.disable_punish_fail_test
        self.upload_target = parser.upload_target
        self.parser_type = parser.parser_type
        self.upload_to_popcorn = parser.upload_to_popcorn
        self.separate_upload = parser.separate_upload
        self.ui_suit = parser.ui_suit
        self.use_tc_json_string = parser.use_tc_json_string

        # Instances
        self.authorized = False
        self.running = True
        self.config = None
        self.server = jenkins.Jenkins(self.server_url, username=self.username, password=self.password)
        log.info(f'Connect to {self.server_url}.')
        self.jobs = []
        self.additional_tasks = []
        self.overall = OverallInfo()
        self.push_server = None
        self.sub_tests = None # dict, key is ticket ID, record for print summary

        # Handle library
        if imported_ui_log_parser: ui_log_parser.print_log = log.debug
        else:
            log.warning(f'Cannot import ui_log_parser, set disable_parser to True')
            self.disable_parser = True
        # Check pararms
        if not self.target_time and not self.target_build and not self.target_pass_build and \
                not self.target_iteration and not self.target_pass:
            raise RuntimeError('Need to specify a target')
        if self.disable_parser and (self.target_iteration or self.target_pass):
            raise RuntimeError('Target iterations cannot with --disable-parser')
        if not self.username or not self.password:
            if self.stop_all:
                raise RuntimeError('Need username and password to enable stop_all.')
            log.warning(f'Since no username and password, all the Jenkins jobs will keep running even abosrt this script. ')
        else:
            self.authorized = True
        # Load JSON file.
        with open(self.config_path, 'r') as f:
            self.config = json.loads(f.read())
        # Check configs
        for index, job_config in enumerate(self.config["jobs"], 1):
            if 'job_name' not in job_config or not job_config['job_name']:
                raise RuntimeError(f'#{index} job has not "job_name"')
            #if 'job_token' not in job_config:
            #    raise RuntimeError(f'#{index} job has not "job_token"')
            self.jobs.append(JobInfo(exec_info=job_config, runner_params=job_config.get('runner_params')))
        log.info(f'Loaded {len(self.config["jobs"])} jobs.')

        signal.signal(signal.SIGINT, self.exit_handler)
        signal.signal(signal.SIGTERM, self.exit_handler)

    def exit_handler(self, signum, frame):
        self.running = False
        log.warning('Script aborted, now stopping jobs...')
        for index, job in enumerate(self.jobs, 0):
            self.stop_build(job_index=index)

    def stoppable_sleep(self, secs):
        start = 0
        while self.running:
            time.sleep(1)
            start += 1
            if start >= secs: break

    def main(self):
        # Launch jobs.
        for index, job in enumerate(self.jobs, 0):
            log.info(f'Launching #{index} {self.job_display_msg(job_index=index)}...')
            self.build_job_with_retry(job_index=index)

        self.add_rest_time()

        # Mointor and keep running job until reach target.
        while not self.reach_target():
            for index, job in enumerate(self.jobs, 0):
                if self.is_job_completed(job_index=index):
                    self.summarize_job(job_index=index)
                    self.summarize(print_out=False, print_out_one_line=True)
                    if self.reach_target(): break
                    self.build_job_with_retry(job_index=index)

            self.exec_additional_tasks()

            self.stoppable_sleep(JOB_MINITOR_INTERVAL_TIME)

        log.info('Now handle existing jobs...')
        # Handle jobs after reach target.
        for index, job in enumerate(self.jobs, 0):
            if self.is_job_completed(job_index=index):
                if not self.is_runner_status_summarized(job_index=index): self.summarize_job(job_index=index)
                continue
            if self.stop_all:
                self.stop_build(job_index=index)
            else:
                self.wait_for_job_completed(job_index=index)
                self.summarize_job(job_index=index)

        self.set_end_time()
        test_pass = self.summarize()
        self.handle_ui_report_urls()
        if self.upload_target: self.upload_log_file_server()
        return test_pass

    def exec_additional_tasks(self):
        queue_list = self.additional_tasks
        self.additional_tasks = [] # clean up list.
        for task, kargs in queue_list:
            task(**kargs)

    def add_rest_time(self):
        # Increase interval waiting time for trying rest test devices to make automation more stable.
        self.build_gate_time += self.rest_time

    def set_end_time(self):
        self.overall['end_time'] = time.time()

    def retry(self, func, *args, **kdargs):
        for infex in range(10):
            try:
                return func(*args, **kdargs)
            except Exception as e:
                log.debug(e, exc_info=True)
                self.stoppable_sleep(10)
                log.debug(f'{infex+1} times failed, now retry...')

    # Basic Jenkins API.
    def jenkins_build_job(self, *args, **kdargs):
        if not self.running: raise StopScript('Script stopped.')
        log.debug(f'Make a call to build job...')
        ret = self.server.build_job(*args, **kdargs)
        self.overall['last_trigger_time'] = time.time()
        return ret

    def jenkins_get_job_info(self, *args, **kdargs):
        return self.retry(self.server.get_job_info, *args, **kdargs)

    def jenkins_get_build_info(self, *args, **kdargs):
        # add more retry for issue: https://bugs.launchpad.net/python-jenkins/+bug/1818808
        ret = self.retry(self.retry, self.server.get_build_info, *args, **kdargs)
        if ret: return ret
        return {}

    def jenkins_get_build_env_vars(self, *args, **kdargs):
        # NOTE: it may return empty!!
        ret = self.retry(self.server.get_build_env_vars, *args, **kdargs)
        if ret: return ret
        return {}

    def jenkins_stop_build(self, *args, **kdargs):
        if not self.authorized:
            log.warning('Not authorized to stop job.')
            return
        return self.retry(self.server.stop_build, *args, **kdargs)

    def jenkins_get_build_console_output(self, *args, **kdargs):
        # Note: Very big size string
        # If we want to run it on small memory device, then rewrite it with requests.
        ret = self.retry(self.server.get_build_console_output, *args, **kdargs)
        if ret: return ret.split('\n')
        return []

    def jenkins_get_build_test_report(self, *args, **kdargs):
        ret = self.retry(self.server.get_build_test_report, *args, **kdargs)
        if ret: return ret
        return {}

    def wait_for_gate_time(self, job_index):
        total_gate_time = self.build_gate_time + self.jobs[job_index]['additional_gate_time']
        if total_gate_time and total_gate_time > time.time() - self.overall['last_trigger_time']:
            if self.overall['last_trigger_time'] == 0: # First trigger.
                sleep_time = total_gate_time
            else:
                sleep_time = total_gate_time - (time.time() - self.overall['last_trigger_time'])
            log.debug(f'Next build need to wait a gate time: {sleep_time} secs...')
            self.stoppable_sleep(sleep_time)

    def build_job(self, job_index):
        log.debug('Creating a new  build...')
        job_config = self.jobs[job_index]['exec_info']
        job_info = self.get_job_info(job_index)

        if self.jobs[job_index]['pending_build_number']:
            # Continue to wait pending job.
            next_build_number = self.jobs[job_index]['pending_build_number']
        else: # Build a new job and wait it start.
            """ Consider Cases:
            1. No build in queue with 1 running build/completed build.
            2. 1 build in queue with 1 running build. (won't with 1 completed build because it has gate time)
            """
            if job_info['inQueue']:
                self.delay_build(job_index)
                raise StopRetryBuild('Delay build')
            next_build_number = job_info['nextBuildNumber']
            # Create a job build.
            try:
                # Gate time handler
                self.wait_for_gate_time(job_index)
                # Create build
                self.jenkins_build_job(name=job_config['job_name'], parameters=job_config.get('job_params'), token=job_config.get('job_token'))
            except StopScript:
                log.warning(f'Catch StopScript during creating job: {e}', exc_info=True)
                raise
            except Exception as e:
                log.error(e, exc_info=True)
                log.error(f'Failed to create a build, now check any new build generated for {MAXIMUM_BUIILD_WAITING_TIME} secs...')

        # Wait for job creation.
        start_check_time = time.time()
        while True:
            try:
                if self.jenkins_get_build_info(job_config['job_name'], next_build_number):
                    break
                raise RuntimeError('Build not found') # Keep retrying in case of slow jenkins creation.
            except (jenkins.JenkinsException, RuntimeError):
                log.debug(f'Build: {next_build_number} not found.')
                if time.time() - start_check_time >= MAXIMUM_BUIILD_WAITING_TIME:
                    log.warning(f'Fail to find new build over {MAXIMUM_BUIILD_WAITING_TIME} sec, please check Jenkins!')
                    self.set_pending_build(job_index, waiting_build=next_build_number)
                    raise StopRetryBuild('Keep waiting for build creation')
                time.sleep(5)

        # Update build information.
        self.set_runner_status_to_created(job_index)
        self.jobs[job_index]['current_build_number'] = next_build_number
        self.jobs[job_index]['pending_build_number'] = None
        self.jobs[job_index]['result']['total_job_builds'] += 1
        build = BuildInfo(build_number=next_build_number, url=f"{job_info['url']}{next_build_number}")
        self.jobs[job_index]['result']['builds'].append(build)
        self.overall['result']['builds'].append(build)
        log.info(f"{job_info['url']}{next_build_number} started")
        return True

    def delay_build(self, job_index):
        log.warning(f'Delay Job: {job_index} for {DELAY_BUIILD_TIME} secs by other build in queue...')
        self.jobs[job_index]['current_build_number'] = 0 # For skip.

        def _build_job(job_index):
            self.stoppable_sleep(DELAY_BUIILD_TIME)
            self.build_job_with_retry(job_index)

        self.additional_tasks.append([_build_job, {'job_index': job_index}])

    def set_pending_build(self, job_index, waiting_build):
        job_info = self.get_job_info(job_index)
        if job_info['nextBuildNumber'] == waiting_build or job_info['lastBuild']['number'] == waiting_build:
            self.jobs[job_index]['pending_build_number'] = waiting_build
            log.warning(f'Keep waiting for build: {waiting_build}...')
        else:
            self.jobs[job_index]['pending_build_number'] = None

    def build_job_with_retry(self, job_index, retry_times=MAXIMUM_RETRY_BUIILDS):
        try:
            while not self.build_job(job_index):
                log.debug(f'Retry after {RETRY_BUIILD_INTERVAL_TIME} secs...')
                self.stoppable_sleep(RETRY_BUIILD_INTERVAL_TIME)
        except StopScript:
            log.info(f'Cancel to create a new build.')
            return
        except StopRetryBuild as e:
            log.debug(f'Stop retrying build with {e}')
            return

    def reach_target(self):
        if not self.running: return True
        if self.target_time and time.time() - self.overall['start_time'] >= self.target_time:
            log.info(f'Reach the target time: {self.target_time} secs!!')
            return True
        if self.target_build and self.overall['result']['total_job_builds'] >= self.target_build:
            log.info(f'Reach the target builds: {self.target_build}!!')
            return True
        if self.target_pass_build and self.overall['result']['total_pass_job_builds'] >= self.target_pass_build:
            log.info(f'Reach the target pass builds: {self.target_pass_build}!!')
            return True
        if self.target_iteration and self.overall['result']['total_iterations'] >= self.target_iteration:
            log.info(f'Reach the target terations: {self.target_iteration}!!')
            return True
        if self.target_pass and self.overall['result']['total_pass_iterations'] >= self.target_pass:
            log.info(f'Reach the target pass terations: {self.target_pass}!!')
            return True
        return False

    def is_job_launched(self, job_index):
        if self.jobs[job_index]['current_build_number'] == 0:
            return False
        return True

    # Jenkins API wrapper.
    def is_job_completed(self, job_index):
        if not self.is_job_launched(job_index): return True
        build_info = self.get_build_info(job_index)
        log.debug(f"Job #{job_index} is building: {build_info.get('building')}   Status: {build_info.get('result')}")
        return not build_info.get('building') # Looks if build_info['result'] has a status, the job should be done.

    def get_job_info(self, job_index):
        return self.jenkins_get_job_info(self.jobs[job_index]['exec_info']['job_name'])

    def get_build_info(self, job_index):
        if not self.is_job_launched(job_index): return {}
        job = self.jobs[job_index]
        return self.jenkins_get_build_info(job['exec_info']['job_name'], job['current_build_number'])

    def get_build_env_vars(self, job_index):
        if not self.is_job_launched(job_index): return {}
        job = self.jobs[job_index]
        return self.jenkins_get_build_env_vars(job['exec_info']['job_name'], job['current_build_number'])

    def stop_build(self, job_index):
        if not self.is_job_launched(job_index): return
        job = self.jobs[job_index]
        log.info(f'Stopping #{job_index} job...')
        while not self.is_job_completed(job_index):
            self.jenkins_stop_build(job['exec_info']['job_name'], job['current_build_number'])
            time.sleep(5)

    def get_build_console_output(self, job_index):
        if not self.is_job_launched(job_index): return []
        job = self.jobs[job_index]
        return self.jenkins_get_build_console_output(job['exec_info']['job_name'], job['current_build_number'])

    def get_build_test_report(self, job_index):
        if not self.is_job_launched(job_index): return []
        job = self.jobs[job_index]
        return self.jenkins_get_build_test_report(job['exec_info']['job_name'], job['current_build_number'])
        
    def wait_for_job_completed(self, job_index):
        if not self.is_job_launched(job_index): return
        log.info(f'Waiting for #{job_index} job finish...')
        while not self.is_job_completed(job_index):
            time.sleep(15)

    def punish_fail_test(self, job_index):
        if self.disable_punish_fail_test:
            return
        continue_failing = 0
        job = self.jobs[job_index]
        for build in reversed(job['result']['builds']):
            if build.has_pass_itrs():
                job['additional_gate_time'] = 0
                return
            continue_failing += 1

        if continue_failing == 2:
            job['additional_gate_time'] = 1.5*60*60
        elif continue_failing >= 4:
            job['additional_gate_time'] = 24*60*60
        log.debug(f"Punish job #{job_index} to increase waiting time: {job['additional_gate_time']}")

    def summarize_job(self, job_index, print_out=True):
        if not self.is_job_launched(job_index): return
        self.set_runner_status_to_summarized(job_index)
        job = self.jobs[job_index]
        build_info = self.get_build_info(job_index)
        env_vars = self.get_build_env_vars(job_index).get('envMap', {}) # it may return empty!!
        build_record = job['result']['builds'][-1]

        if not self.disable_parser:
            total_itr, total_pass, sub_tests = self.parse_test_result(job_index)
            log.debug(f"Total Iterations: {total_itr}")
            job['result']['total_iterations'] += int(total_itr)
            build_record['iterations'] = int(total_itr)
            log.debug(f"Total Pass: {total_pass}")
            job['result']['total_pass_iterations'] += int(total_pass)
            build_record['pass_iterations'] = int(total_pass)
            if self.upload_to_popcorn:
                log.debug(f'sub_tests: {sub_tests}')
                if self.separate_upload and sub_tests:
                    if self.use_tc_json_string:
                        self.upload_sub_test_results_to_popcorn_with_json_string(job_index, sub_tests)
                    else:
                        self.upload_sub_test_results_to_popcorn(job_index, sub_tests)
                elif int(total_pass):
                    self.upload_pass_result_to_popcorn(job_index, int(total_pass))
        test_result = build_info.get('result')
        if not test_result:
            log.warning(f"=> {self.job_display_msg(env_vars, build_info)} has no build information!")
        elif test_result == 'SUCCESS':
            job['result']['total_pass_job_builds'] += 1
        else:
            job['result']['total_fail_job_builds'] += 1
        build_record['result'] = test_result

        self.punish_fail_test(job_index)

        if print_out:
            details_msg = ''
            if not self.disable_parser:
                details_msg = f" ({job['result']['total_pass_iterations']}/{job['result']['total_iterations']})"
            log.info(f"|-- {self.job_display_msg(env_vars, build_info)}: {test_result}{details_msg}")

        if not build_record.has_pass_itrs(): log.warning('|-> A bad test result, please check it!')

    def parse_test_result(self, job_index):
        """ Fetch results with given parser and return total_itr and total_pass.
        """
        return {
            'JUNIT': self.fecth_from_junit_report,
            'UI_LOG': self.get_console_log_and_parse
        }[self.parser_type](job_index)

    def fecth_from_junit_report(self, job_index):
        test_result = self.get_build_test_report(job_index)
        return len(test_result.get('suites', [{'cases': []}])[0]['cases']), test_result.get('passCount', 0), None

    def get_console_log_and_parse(self, job_index):
        logs = self.get_build_console_output(job_index)
        return ui_log_parser.parse_strs_and_summarize(
            logs, accept_failures=int(self.jobs[job_index]['runner_params'].get('accept_failures', 0)),
            debug=True, suite_name=self.parse_with_suite_name
        )

    def job_display_msg(self, env_vars=None, build_info=None, job_index=None):
        if env_vars and 'BUILD_URL' in env_vars:
            return env_vars['BUILD_URL']
        if build_info and 'url' in build_info:
            return build_info['url']
        if job_index is None:
            return 'Unknown build'
        build_msg = ''
        if self.jobs[job_index]['current_build_number']:
            build_msg = f"/{self.jobs[job_index]['current_build_number']}"
        return f"{self.jobs[job_index]['exec_info']['job_name']}{build_msg}"

    def summarize(self, print_out=True, print_out_one_line=False):
        overall_res = self.overall['result']

        total_iterations = 0
        total_pass_iterations = 0
        total_job_builds = 0
        total_pass_job_builds = 0
        total_fail_job_builds = 0

        for job in self.jobs:
            job_res = job['result']
            total_iterations += job_res['total_iterations']
            total_pass_iterations += job_res['total_pass_iterations']
            total_job_builds += job_res['total_job_builds']
            total_pass_job_builds += job_res['total_pass_job_builds']
            total_fail_job_builds += job_res['total_fail_job_builds']

        overall_res['total_iterations'] = total_iterations
        overall_res['total_pass_iterations'] = total_pass_iterations
        overall_res['total_job_builds'] = total_job_builds
        overall_res['total_pass_job_builds'] = total_pass_job_builds
        overall_res['total_fail_job_builds'] = total_fail_job_builds

        if print_out:
            log.info('-'*80)
            duration = datetime.timedelta(seconds=round(self.overall['end_time'] - self.overall['start_time']))
            log.info(f'* {"Duration":22}: {duration}')
            log.info(f'* {"Total Iterations":22}: {total_iterations}')
            log.info(f'* {"Total Pass Iterations":22}: {total_pass_iterations}')
            log.info(f'* {"Total Job Builds":22}: {total_job_builds}')
            log.info(f'* {"Total Pass Job Builds":22}: {total_pass_job_builds}')
            log.info(f'* {"Total Fail Job Builds":22}: {total_fail_job_builds}')
            if self.sub_tests:
                log.info(f'* {"Total Pass In Each Sub Test":22}:')
                for tn, sub_dict in self.sub_tests.items():
                    log.info(f'* - {tn}: {sub_dict["total_pass"]}')
            log.info('-'*80)

        iter_msg = ''
        if overall_res['total_iterations']:
            iter_msg = f"Iteration: {overall_res['total_pass_iterations']}/{overall_res['total_iterations']}  "
        one_line_msg = f"* {iter_msg}Job Builds: {overall_res['total_pass_job_builds']}/{overall_res['total_job_builds']}"
        
        if print_out_one_line:
            log.info(one_line_msg)
        else:
            log.debug(one_line_msg)

        if overall_res['total_fail_job_builds']:
            return False
        return True

    # Runner status
    def set_runner_status_to_created(self, job_index):
        self.jobs[job_index]['runner_status'] = 'CREATED'

    # TODO: not good plact to set RUNING.

    def set_runner_status_to_summarized(self, job_index):
        self.jobs[job_index]['runner_status'] = 'SUMMARIZED'

    def is_runner_status_summarized(self, job_index):
        return 'SUMMARIZED' in self.jobs[job_index]['runner_status']

    def handle_ui_report_urls(self): 
        has_pass = []
        no_pass = []
        for build in self.overall['result']['builds']:
            if build.has_pass_itrs():
                has_pass.append(self.gen_ui_report_url(build['url']))
            else:
                no_pass.append(self.gen_ui_report_url(build['url']))

        self.export_report_urls(has_pass, no_pass)

        if not self.print_html_report_urls: 
            return

        log.info('-'*80)
        log.info('| No-Pass HTML report/Console URLs:')
        for url in no_pass:
            log.info(f'|- {url} ')
        log.info('-'*80)
        log.info('| Has-Pass HTML report/Console URLs:')
        for url in has_pass:
            log.info(f'|- {url} ') 
        log.info('-'*80)

    def gen_ui_report_url(self, build_url):
        for post_str in ['HTML_20Report', 'console']:
            report_url = f"{build_url}/{post_str}"
            if self.url_exists(report_url):
                return report_url

    def url_exists(self, url):
        response = requests.get(url)
        if response.status_code == 200:
            return True
        return False

    def export_report_urls(self, has_pass, no_pass, filename='report_urls.txt'):
        with open(filename, 'w') as f:
            f.write(f'No-Pass:\n')
            for url in no_pass:
                f.write(f'{url}\n')
            f.write(f'Has-Pass:\n')
            for url in has_pass:
                f.write(f'{url}\n')

    def upload_log_file_server(self):
        log.info('Uploading automation log to file server...')
        subprocess.check_output(
            f'''curl --retry 40 --retry-delay 15 -u ftp:ftppw --ftp-create-dirs -T "{{$(echo *.txt | tr ' ' ',')}}" ftp://fileserver.hgst.com/ibi_stability_test_logs/{self.upload_target}/''',
            stderr=subprocess.STDOUT,
            shell=True
        )

    def upload_pass_result_to_popcorn(self, job_index, total_pass):
        try:
            popcorn_info = self.jobs[job_index]['exec_info'].get('runner_params', {}).get('popcorn')
            if not popcorn_info: return
            if not self.push_server: self.push_server = jenkins.Jenkins(POPCORN_JENKINS_URL)
            params = popcorn_info.copy()
            params['total_pass'] = total_pass
            self.retry_upload_popcorn(params)
            log.info(f'Uploaded {total_pass} pass to Popcorn server ({popcorn_info["test_id"]})')
        except Exception as e:
            log.error(e, exc_info=True)

    def upload_sub_test_results_to_popcorn(self, job_index, sub_tests):
        try:
            uploaded_tests = []
            popcorn_info = self.jobs[job_index]['exec_info'].get('runner_params', {}).get('popcorn')
            task_id_mapping = self.jobs[job_index]['exec_info'].get('runner_params', {}).get('task_id_mapping')
            if not task_id_mapping and self.ui_suit:
                task_id_mapping = read_task_id_mapping_from_suit_xml(self.ui_suit)
                log.debug(f'task_id_mapping: {task_id_mapping}')
            if not popcorn_info or not task_id_mapping: return
            if not self.push_server: self.push_server = jenkins.Jenkins(POPCORN_JENKINS_URL)
            for tn, v in sub_tests.items():
                try:
                    if tn not in task_id_mapping: continue
                    self.append_sub_test(task_id_mapping[tn], v) # record for print summary
                    params = popcorn_info.copy()
                    params['test_id'] = task_id_mapping[tn]
                    params['total_pass'] = v['total_pass']
                    uploaded_tests.append(f"{params['test_id']}: {params['total_pass']}")
                    if not v['total_pass']: continue
                    self.retry_upload_popcorn(params)
                except Exception as e:
                    log.info(f'Upload {tn} result failed')
                    log.error(e, exc_info=True)
            log.info('Uploaded to Popcorn server ({})'.format(' '.join(uploaded_tests)))
        except Exception as e:
            log.error(e, exc_info=True)

    def upload_sub_test_results_to_popcorn_with_json_string(self, job_index, sub_tests):
        try:
            uploaded_tests = []
            popcorn_info = self.jobs[job_index]['exec_info'].get('runner_params', {}).get('popcorn')
            task_id_mapping = self.jobs[job_index]['exec_info'].get('runner_params', {}).get('task_id_mapping')
            if not task_id_mapping and self.ui_suit:
                task_id_mapping = read_task_id_mapping_from_suit_xml(self.ui_suit)
                log.debug(f'task_id_mapping: {task_id_mapping}')
            if not popcorn_info or not task_id_mapping: return
            if not self.push_server: self.push_server = jenkins.Jenkins(POPCORN_JENKINS_URL)
            tcs = []
            for tn, v in sub_tests.items():
                if tn not in task_id_mapping: continue
                self.append_sub_test(task_id_mapping[tn], v) # record for print summary
                if not v['total_pass']: continue
                tcs.append({
                    'test_name': tn,
                    'test_id': task_id_mapping[tn],
                    'total': v['total_pass'],
                    'test_duration': popcorn_info.get('test_duration', 300)
                })
                uploaded_tests.append(f"{task_id_mapping[tn]}: {v['total_pass']}")
            try:
                params = popcorn_info.copy()
                params['tc_json_string'] = json.dumps(tcs)
                self.retry_upload_popcorn(params)
                log.info('Uploaded to Popcorn server ({})'.format(' '.join(uploaded_tests)))
            except Exception as e:
                log.info(f'Upload {tn} result failed')
                log.error(e, exc_info=True)
        except Exception as e:
            log.error(e, exc_info=True)

    def retry_upload_popcorn(self, params, retry_times=999, delay=5):
        for _ in range(retry_times):
            try:
                self.push_server.build_job(name=POPCORN_JENKINS_JOB, parameters=params, token=POPCORN_JENKINS_JOB_TOKEN)
                break
            except Exception as e:
                time.sleep(delay)

    def append_sub_test(self, test_id, v_dict):
        if not test_id or not v_dict: return
        if not self.sub_tests: self.sub_tests = {}
        try:
            if test_id not in self.sub_tests:
                self.sub_tests[test_id] = v_dict
            else:
                for k, v in v_dict.items():
                    if k not in self.sub_tests[test_id]:
                        self.sub_tests[test_id][k] = v
                    elif isinstance(v, int):
                        self.sub_tests[test_id][k] += v
        except Exception as e:
            log.error(e, exc_info=True)


def read_task_id_mapping_from_suit_xml(suit_path):
    mapping = {}
    # read integration suite file.
    for root_elem in ET.parse(suit_path).getroot().iter('suite-file'):
        # read sub test suite file.
        root = ET.parse(f"{os.path.dirname(suit_path)}/{root_elem.attrib['path']}").getroot()
        # find jiraId and set it to mapping
        for elem in root.iter('parameter'):
            if 'jiraId' in elem.attrib['name'] and elem.attrib['value'] and root.attrib['name']:
                mapping[root.attrib['name']] = elem.attrib['value']
                break
    return mapping


class StopScript(RuntimeError):
    pass

class StopRetryBuild(RuntimeError):
    pass

class BuildInfo(dict):

    def __init__(self, build_number=None, url=None):
        super().__init__(**{
            'build_number': build_number,
            'url': url,
            'iterations': None,
            'pass_iterations': None,
            'result': None
        })

    def is_pass(self):
        if self['result'] == 'SUCCESS':
            return True
        return False

    def has_pass_itrs(self):
        if self['pass_iterations'] is not None:
            if self['pass_iterations'] > 0:
                return True
            return False
        return self.is_pass()

class JobInfo(dict):

    def __init__(self, exec_info=None, runner_params=None):
        super().__init__(**{
            'exec_info': exec_info,
            'runner_params': runner_params if runner_params else {},
            'runner_status': None,
            'current_build_number': 0,
            'pending_build_number': None,
            'start_time': time.time(),
            'additional_gate_time': 0,
            'result': {
                'builds': [],
                'total_iterations': 0, # per test iteration.
                'total_pass_iterations': 0,
                'total_job_builds': 0, # per Jenkins job.
                'total_pass_job_builds': 0,
                'total_fail_job_builds': 0
            }
        })

    def find_build(self, build_number):
        for build in self['result']['builds']:
            if build['build_number'] == build_number: return build
        return None

class OverallInfo(dict):

    def __init__(self, exec_info=None):
        super().__init__(**{
            'start_time': time.time(),
            'end_time': None,
            'last_trigger_time': 0,
            'last_build_number': {},
            'result': {
                'builds': [],
                'total_iterations': 0, # per test iteration.
                'total_pass_iterations': 0,
                'total_job_builds': 0, # per Jenkins job.
                'total_pass_job_builds': 0,
                'total_fail_job_builds': 0
            }
        })


def gen_log(filename='runner_log.txt', level=logging.NOTSET):
    log_inst = logging.getLogger()
    log_inst.setLevel(level)
    # Log file 
    file_handler = logging.FileHandler(filename=filename, mode='w')
    file_handler.setLevel(logging.NOTSET)
    file_formatter = logging.Formatter('%(asctime)-19s: %(levelname)-8s: %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)
    log_inst.addHandler(file_handler)
    # Screen log
    stream_handler = colorlog.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    stream_formatter = colorlog.ColoredFormatter('%(log_color)s%(levelname)-8s: %(message)s')
    stream_handler.setFormatter(stream_formatter)
    log_inst.addHandler(stream_handler)
    return log_inst

# Set up logging.
log = gen_log()


if __name__ == '__main__':

    parser = ArgumentParser("""\
        *** Run Jenkin jobs in parallel for a specific time/iteration. ***

        Config format:
            * "job_name" is unique and necessary field.
            * "job_token" is Authentication Token of the sub-job.
            * "job_params" is input parameters for running the sub-job.
            * "runner_params" is parameters for job runner.
              |- Support:
                 |- accept_failures: for log parser.
                 |- popcorn: fields to upload results to Popcorn. Field names refer to upload_results_to_popcorn.
                 |- task_id_mapping: test name & test id mapping, which name is UI test name for upload Popcorn seperately (can be replaced by --ui-suit).
        {
            "jobs": [
                {
                    "job_name": "job_1", "job_token": "token_1", "job_params": {"param_1": "val_1", "param_2": "val_2"}
                },
                {
                    "job_name": "job_2", "job_token": "token_2", "job_params": {"param_3": "val_3", "param_4": "val_4"}, "runner_params": {"accept_failures": "0"}
                }
            ]
        }
        """)

    parser.add_argument('-ec', '--execute-config', help='Job execute configs in JSON', metavar='PATH', required=True)
    parser.add_argument('-url', '--server-url', help='Jenkin server URL', metavar='URL', required=True)
    parser.add_argument('-tt', '--target-time', help='Run tests until specific time', metavar='SECS', type=int, default=None)
    parser.add_argument('-tb', '--target-build', help='Run tests until specific job build number', metavar='NUMBER', type=int, default=None)
    parser.add_argument('-tpb', '--target-pass-build', help='Run tests until specific passed job build number', metavar='NUMBER', type=int, default=None)
    parser.add_argument('-ti', '--target-iteration', help='Run tests until specific iteration number', metavar='NUMBER', type=int, default=None)
    parser.add_argument('-tp', '--target-pass', help='Run tests until specific pass number', metavar='NUMBER', type=int, default=None)
    parser.add_argument('-u', '--username', help='Jenkins user name', metavar='USERNAME', default='twa')
    parser.add_argument('-p', '--password', help='Jenkins password', metavar='PASSWORD', default='twa123')
    parser.add_argument('-sa', '--stop-all', help='Stop running builds after reach targets', action='store_true', default=False)
    parser.add_argument('-gt', '--gate-time', help='Gate time between jobs', metavar='SECS', type=int, default=120)
    parser.add_argument('-rt', '--rest-time', help='Rest time for each new builds', metavar='SECS', type=int, default=30*60)
    parser.add_argument('-phru', '--print-html-report-urls', help='Print out UI automation report URLs', action='store_true', default=False)
    parser.add_argument('-dpc', '--disable-parser', help='Disable to collect iterations via given parser', action='store_true', default=False)
    parser.add_argument('-pwsn', '--parse-with-suite-name', help='Suite name to split UI logs to iterations', metavar='SUITENAME', default=None)
    parser.add_argument('-dpft', '--disable-punish-fail-test', help='Disable punish fail test', action='store_true', default=False)
    parser.add_argument('-ut', '--upload-target', help='Target path of file server to upload log', metavar='PATH', default=None)
    parser.add_argument('-pt', '--parser-type', help='Parser type to fetch test results', metavar='TYPE', default='UI_LOG', choices=['JUNIT', 'UI_LOG'])
    parser.add_argument('-utp', '--upload-to-popcorn', help='Upload PASS result to Popcorn', action='store_true', default=False)
    parser.add_argument('-su', '--separate-upload', help='Upload PASS result to Popcorn for each sub test, not by cycle', action='store_true', default=False)
    parser.add_argument('-us', '--ui-suit', help='UI suit path for loading suit info', metavar='PATH', default=None)
    parser.add_argument('-utjs', '--use-tc-json-string', help='Upload popcorn result via test case JSON string', action='store_true', default=False)

    try:
        runner = JobRunner(parser.parse_args())
        if runner.main():
            sys.exit(0)
        sys.exit(1)
    except Exception as e:
        log.error(e, exc_info=True)
        sys.exit(1)

