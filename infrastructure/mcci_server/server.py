#!/usr/bin/python3.7
import logging
import os
import subprocess
from logging.handlers import RotatingFileHandler
from flask import Flask, request


BINARY_LOCATION = os.environ.get('MCCI_PATH', '')
MCCI_BINARY = 'mcci2101'
FULL_BINARY_PATH = os.path.join(BINARY_LOCATION, MCCI_BINARY)
SERVER_PORT = os.environ.get('SERVER_PORT', 8765)


def exec_mcci(args):
    return subprocess.run([FULL_BINARY_PATH] + args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)


app = Flask('MCCI')

MCCI_RESP_CODE = { # Since no docs for these status code, suppose they are unique and not change. 
    'detach': '06- 00',
    'hsattach': '03- 06',
    'ssattach': '05- 07'
}

def endpoint_response(stdout=None, stderr=None, returncode=None, success=None):
    return {
        'stdout': stdout, # Output in pretty format from command.
        'stderr': stderr, # Error message from command.
        'returncode': returncode, # Exit code form command.
        'success': success # set True/False to make sure this call is success or not.
    }

# Always return 200 OK, but with success=False and error message in stderr.
@app.errorhandler(Exception)
def handle_exception(error):
    if isinstance(error, subprocess.CalledProcessError):
        return endpoint_response(stderr=str(error), returncode=error.returncode, success=False)
    return endpoint_response(stderr=str(error), success=False)

@app.route('/mcci/listdevices')
def run_listdevices():
    r = exec_mcci(['-listdevices'])
    if 'No device Found' in r.stdout:
        return endpoint_response(stdout=[], returncode=r.returncode, success=True)
    return endpoint_response(
        stdout=[{v[0].strip(':'): v[1] for v in d} for d in [[[v.strip() for v in l.split(' ', 1)] for l in s.split('\n\t') if 'Device Found' not in l] for s in r.stdout.split('\n\n') if s]],
        stderr=None, returncode=r.returncode, success=True
    )

@app.route('/mcci/<cmd>')
def run_cmd(cmd):
    excepted_status = None # for check comnmand status code.
    args = ['-'+cmd]
    for k, v in request.args.items(): # append all the input parameters.
        args += ['-'+k, v]
        if not excepted_status:
            if k in MCCI_RESP_CODE:
                excepted_status = MCCI_RESP_CODE[k]
    r = exec_mcci(args)
    output = r.stdout.strip()
    return endpoint_response( # success always return True while client invoke a cmd not in MCCI_RESP_CODE.
        stdout=output.split('received: ').pop() if 'received: ' in output else output,
        returncode=r.returncode, success=True if not excepted_status or excepted_status == status else False
    )


if __name__ == "__main__":
    """ run example:
    SERVER_PORT=8765 MCCI_PATH=/home/user/Workspace/source/MCCI/MCCI2101-ConnectionExerciser-V1_18/linux python3.7 server.py 
    """
    '''
    # Access log are output direct to console, not to log, so we may no need log.
    handler = RotatingFileHandler('mcci_app.log', maxBytes=10000, backupCount=3)
    app.logger.setLevel(logging.DEBUG)
    app.logger.addHandler(handler)
    '''
    app.run(host='0.0.0.0', port=SERVER_PORT)
