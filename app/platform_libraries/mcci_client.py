"""
A library to access MCCI service.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import time
import sys
from argparse import ArgumentParser
# 3rd party modules
from requests import Request, Session
# platform modules
try:
    from common_utils import create_logger
    _log_inst = create_logger()
except:
    _log_inst = None


class MCCIAPI(object):

    def __init__(self, server_url, log_inst=None):
        # Handle parameters
        self.url = server_url
        if log_inst:
            self.logger = log_inst
        else:
            self.logger = _log_inst

        # Prepare connection
        self._session = Session()

    def log(self, msg):
        if not self.logger: return
        self.logger.info(msg)

    def rest_call(self, request):
        prepared_request = self._session.prepare_request(request)
        #prepared_request.headers = self.headers

        response = self._session.send(prepared_request)
        self.log("REST Call: {}".format(response.url))

        if response.status_code != 200:
            raise RuntimeError('status: {} content: {}'.format(response.status_code, response.content))

        json_response = response.json()
        self.log("JSON Response: {}".format(json_response))

        if 'success' in json_response and json_response['success'] != True:
            raise RuntimeError('stderr: {} stdout: {}'.format(json_response['stderr'], json_response['stdout']))

        return json_response

    def _device_paramter(self, serno, device):
        if serno:
            return 'serno={}'.format(serno)
        return 'device={}'.format(device)

    def list(self):
        self.log('List all devices')
        return self.rest_call(Request('GET', '{}/mcci/listdevices'.format(self.url)))

    def detach(self, serno=None, device=None):
        self.log('Detach USB on device: {}'.format(serno or device))
        return self.rest_call(Request('GET', '{}/mcci/detach?{}'.format(self.url, self._device_paramter(serno, device))))

    def attach_usb2(self, serno=None, device=None):
        self.log('Attach USB with 2.0 mode on device: {}'.format(serno or device))
        return self.rest_call(Request('GET', '{}/mcci/hsattach?{}'.format(self.url, self._device_paramter(serno, device))))

    def attach_usb3(self, serno=None, device=None):
        self.log('Attach USB with 3.0 mode on device: {}'.format(serno or device))
        return self.rest_call(Request('GET', '{}/mcci/ssattach?{}'.format(self.url, self._device_paramter(serno, device))))

    def reattach_usb2(self, serno=None, device=None):
        self.detach(serno, device)
        self.attach_usb2(serno, device)

    def reattach_usb3(self, serno=None, device=None):
        self.detach(serno, device)
        self.attach_usb3(serno, device)

if __name__ == '__main__':
    # Parameters
    parser = ArgumentParser(""" Control remote MCCI server  """)
    parser.add_argument('-u', '--url', help='Server URL', metavar='PATH', required=True)
    parser.add_argument('-l', '--list', help='List devices on remote server', action='store_true', default=False)
    parser.add_argument('-de', '--detach', help='Detach USB on remote server', action='store_true', default=False)
    parser.add_argument('-a2', '--attach-usb2', help='Attach USB with 2.0 mode on remote server', action='store_true', default=False)
    parser.add_argument('-a3', '--attach-usb3', help='Attach USB with 3.0 mode on remote server', action='store_true', default=False)
    parser.add_argument('-ra2', '--rattach-usb2', help='Reattach USB with 2.0 mode on remote server', action='store_true', default=False)
    parser.add_argument('-ra3', '--rattach-usb3', help='Reattach USB with 3.0 mode on remote server', action='store_true', default=False)
    parser.add_argument('-s', '--serno', help='Serail number of MCCI device', metavar='serno', default=None)
    parser.add_argument('-d', '--device', help='Device number of MCCI device', metavar='device', default=None)
    input_args = parser.parse_args()

    mcci = MCCIAPI(input_args.url)
    try:
        if input_args.list:
            mcci.list()
        elif input_args.detach:
            mcci.detach(serno=input_args.serno, device=input_args.device)
        elif input_args.attach_usb2:
            mcci.attach_usb2(serno=input_args.serno, device=input_args.device)
        elif input_args.attach_usb3:
            mcci.attach_usb3(serno=input_args.serno, device=input_args.device)
        elif input_args.attach_usb3:
            mcci.reattach_usb2(serno=input_args.serno, device=input_args.device)
        elif input_args.attach_usb3:
            mcci.reattach_usb3(serno=input_args.serno, device=input_args.device)
        sys.exit(0)
    except Exception, e:
        mcci.log(msg=e)
        sys.exit(1)
