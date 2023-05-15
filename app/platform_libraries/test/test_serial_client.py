'''
#
# Created on Septempter 11, 2014
# @author: Jason Tran
# 
# This module contains the class and methods to validate SerialAPI methods.
#
# Porting to Kamino and update features on Nov 23, 2017
# @author: Estvan Huang
'''
# std modules
import unittest
import logging
import time

# platform modules
from platform_libraries.common_utils import create_logger
from platform_libraries.serial_client import SerialClient


log = create_logger(root_log='SerialClientUnitTest')

# Variables to use for unit testing
serial_server_ip = '10.92.224.62'
serial_port_mapping = 20000
command = 'free | grep Mem | awk \'{print $3/$2 * 100.0}\'' 
buff = 'ls\n'
mystring = '***'
mystring_2 = 'XXXX'
msg = 'hello'

#instantiate NetworkSharesAPI class
try:
    sc = SerialClient(serial_server_ip, serial_port_mapping)
except Exception,ex:
    log.info('Failed to instantiate SerialClient ' + str(ex))

class SerialUnitTest(unittest.TestCase):
    
    def setUp(self):
        sc.initialize_serial_port()
        time.sleep(3)
        log.info('Start executing %s', self._testMethodName)
        sc.serial_read_all(time_for_read=1)
        log.info('Clean previous message.')
         
    def tearDown(self):
        sc.close_serial_connection()
        log.info('Finished executing %s', self._testMethodName)
       
    def test_serial_is_connected(self):
        resp = sc.serial_is_connected()
        if not resp:
            log.error('Serial is not connected')
            raise RuntimeError('Return: {}'.format(resp))
        log.info('Serial is connected')

    def test_serial_write(self):
        sc.serial_write(command)

    def test_serial_write_bare(self):
        sc.serial_write_bare(buff)

    def test_serial_read(self):
        sc.serial_write(mystring)
        status = sc.serial_read()
        log.info('status: %s', status)
        if mystring not in status:
            raise RuntimeError('Read value not expected')
            
    def test_serial_readline(self):
        sc.serial_write(mystring)
        status = sc.serial_readline()
        log.info('status: %s', status)
        if mystring not in status:
            raise RuntimeError('Read value not expected')

    def test_serial_read_all(self):
        sc.serial_write(mystring)
        sc.serial_write(mystring_2)
        status = sc.serial_read_all(time_for_read=5)
        log.info('status: %s', status)
        output = ''.join(status)
        if mystring not in output or mystring_2 not in output:
            raise RuntimeError('Read value not expected')

    def test_serial_wait_for_string(self):
        sc.serial_write(mystring)
        status = sc.serial_wait_for_string(mystring)
        log.info('status: %s', status)
        if mystring not in status:
            raise RuntimeError('Read value not expected')

    def test_serial_wait_for_string_and_return_list(self):
        sc.serial_write(mystring_2)
        sc.serial_write(mystring)
        status = sc.serial_wait_for_string_and_return_list(mystring)
        log.info('status: %s', status)
        output = ''.join(status)
        if mystring not in output or mystring_2 not in output:
            raise RuntimeError('Read value not expected')

    def test_serial_wait_for_string_and_return_string(self):
        sc.serial_write(mystring_2)
        sc.serial_write(mystring)
        status = sc.serial_wait_for_string_and_return_string(mystring)
        log.info('status: %s', status)
        if mystring not in status or mystring_2 not in status:
            raise RuntimeError('Read value not expected')

    def test_serial_wait_for_filter_string(self):
        sc.serial_write(mystring)
        sc.serial_write(mystring)
        sc.serial_write(mystring)
        sc.serial_write(mystring)
        sc.serial_write(mystring)
        sc.serial_write(mystring_2)
        status = sc.serial_wait_for_filter_string(re_pattern=mystring_2)
        log.info('status: %s', status)
        if mystring_2 not in status:
            raise RuntimeError('Read value not expected')

    def test_serial_filter_read(self):
        sc.serial_write(mystring_2)
        sc.serial_write(mystring)
        sc.serial_write(mystring_2)
        status = sc.serial_filter_read(re_pattern=mystring_2)
        log.info('status: %s', status)
        output = ''.join(status)
        if output.count(mystring_2) != 1*2:
            raise RuntimeError('Read value not expected')

    def test_serial_filter_read_least_one(self):
        sc.serial_write(mystring)
        sc.serial_write(mystring_2)
        sc.serial_write(mystring)
        status = sc.serial_filter_read_least_one(re_pattern=mystring_2, timeout_for_each_read=5, time_for_read=5)
        log.info('status: %s', status)
        output = ''.join(status)
        if output.count(mystring_2) != 1*2:
            raise RuntimeError('Read value not expected')

    def test_serial_filter_read_all(self):
        sc.serial_write(mystring_2)
        sc.serial_write(mystring)
        sc.serial_write(mystring_2)
        sc.serial_write(mystring)
        status = sc.serial_filter_read_all(re_pattern=mystring_2, timeout_for_each_read=5, time_for_read=5)
        log.info('status: %s', status)
        output = ''.join(status)
        if output.count(mystring_2) != 2*2:
            raise RuntimeError('Read value not expected')

    def test_serial_debug(self):
        sc.serial_debug(msg)
        log.info('add debug message: %s', msg)

    def test_start_serial_port(self):
        sc.close_serial_connection()
        sc.start_serial_port()


if __name__ == '__main__':
    ## To run whole test suite
    unittest.main()
    

    '''
    ##specify test(s) to execute individual
    suite = unittest.TestSuite()
    #suite.addTest(SerialUnitTest("test_serial_is_connected"))
    suite.addTest(SerialUnitTest("test_serial_debug"))

    
    runner = unittest.TextTestRunner()
    unittest.TextTestRunner(verbosity=2).run(suite)

    '''