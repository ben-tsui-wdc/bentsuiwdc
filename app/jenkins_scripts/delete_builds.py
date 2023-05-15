# -*- coding: utf-8 -*-
# std modules
import logging
import json
import sys
from argparse import ArgumentParser
# 3rd party modules
import colorlog
import jenkins


class DeleteBuilds:

    def __init__(self, parser):
        # Params
        self.config_path = parser.execute_config
        self.server_url = parser.server_url
        self.username = parser.username
        self.password = parser.password
        if not self.username or not self.password:
            raise RuntimeError('Need username and password.')
        self.jobs = []

         # Load JSON file.
        with open(self.config_path, 'r') as f:
            self.config = json.loads(f.read())
        # Check configs
        for index, job_config in enumerate(self.config["jobs"], 1):
            if 'job_name' not in job_config or not job_config['job_name']:
                raise RuntimeError(f'#{index} job has not "job_name"')
            self.jobs.append(job_config)
        log.info(f'Loaded {len(self.config["jobs"])} jobs.')

        # Instances
        self.server = jenkins.Jenkins(self.server_url, username=self.username, password=self.password)
        log.info(f'Connect to {self.server_url}.')

    def main(self):
        for job in self.jobs:
            log.info(f"|- Handle for {job['job_name']}")
            for build in self.filter_builds(job['job_name'], job['max_to_keep']):
                try:
                    log.info(f"Delete {build.get('url')}")
                    self.server.delete_build(job['job_name'], build['number'])
                except Exception as e:
                    log.error(e, exc_info=True)

    def filter_builds(self, job_name, max_to_keep):
        try:
            builds = self.server.get_job_info(job_name, fetch_all_builds=True)['builds']
            log.info(f"Has {len(builds)} builds, now keep {max_to_keep} builds.")
            return sorted(builds, key=lambda b: b['number'], reverse=True)[max_to_keep:][::-1] # small number first.
        except Exception as e:
            log.error(e, exc_info=True)
            return []


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
        *** Delete old Jenkins builds ***

        Config format:
            * "job_name" is unique and necessary field.
            * "max_to_keep" is the number to keep Jenkins builds.
        {
            "jobs": [
                {
                    "job_name": "job_1", "max_to_keep": 120
                },
                {
                    "job_name": "job_2", "max_to_keep": 200
                }
            ]
        }

        """)

    parser.add_argument('-ec', '--execute-config', help='Job execute configs in JSON', metavar='PATH', required=True)
    parser.add_argument('-url', '--server-url', help='Jenkin server URL', metavar='URL', required=True)
    parser.add_argument('-u', '--username', help='Jenkins user name', metavar='USERNAME', default='twa')
    parser.add_argument('-p', '--password', help='Jenkins password', metavar='PASSWORD', default='twa123')

    try:
        DeleteBuilds(parser.parse_args()).main()
    except Exception as e:
        log.error(e, exc_info=True)
        sys.exit(1)
