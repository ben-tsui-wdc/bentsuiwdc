__author__ = 'Nick Yang <nick.yang@wdc.com>'

from DL_UL import DL_UL
from ToolAPI import Tool
from platform_libraries.restAPI import RestAPI
from datetime import datetime
from glob import glob
from platform_libraries.junit_xml import TestCase, TestSuite
import argparse
import os
import sys
import time
import threading
import commands
import shutil
import logging


class Test():
    def __init__(self):

        nfilepath = '/data/wd/diskVolume0/restsdk/userRoots/0000000052385efd015243e74eee0083/nick'
        nfolderpath = '/data/wd/diskVolume0/restsdk/userRoots/0000000052385efd015243e74eee0083/nick/'
        lfilepath = '/home/nick/'
        lfolderpath = '/home/nick'

        example1 = '\n  python.exe stressULDLtest.py -uut_ip 192.168.1.45 -port 5555 -u nick@wd.com -p Test1234'
        example2 = '\n  format of file Path on local: {0} \n  format of folder Path on local: {1}'.format(lfilepath,lfolderpath)
        example3 = '\n  format of file Path on NAS: {0} \n  format of folder Path on NAS : {1}'.format(nfilepath,nfolderpath)
        example4 = '\n  python.exe stressULDLtest.py 192.168.1.45 nick@wd.com Test1234 -uf lfilePath lfolderPath -ud nfolderpath'
        example5 = '\n  python.exe stressULDLtest.py 192.168.1.45 nick@wd.com Test1234 -uf lfilePath lfolderPath -ud nfolderpath -t 10'
        example6 = '\n  python.exe stressULDLtest.py 192.168.1.45 nick@wd.com Test1234 -df nfilePath nfolderPath -dd lfolderPath -t 10'
        example7 = '\n  python.exe stressULDLtest.py 192.168.1.45 nick@wd.com Test1234 -rud nfilePath nfolderPath'

        # Create usages
        parser = argparse.ArgumentParser(description='*** Stress Test for Download/Upload on Kamino ***\n\nExamples:{0}{1}{2}{3}{4}{5}{6}'.format(example1,example2,example3,example4,example5,example6,example7),formatter_class=argparse.RawTextHelpFormatter)

        parser.add_argument('-u_n', help='user number')
        parser.add_argument('-m_n', help='metrics name, ex: Throughput')
        parser.add_argument('-uut_ip', help='Destination NAS IP address, ex. 192.168.1.46')
        parser.add_argument('-port', help='Destination NAS Port, ex. 5555')
        parser.add_argument('-server_ip', help='Destination adb server IP address, ex. 192.168.203.14')
        parser.add_argument('-server_port', help='Destination adb server port number, ex. 5555 (default)')
        parser.add_argument('-u', help='Email user name')
        parser.add_argument('-p', help='Account password')
        parser.add_argument('-t', help='Total testing time (Minutes)  for single user use', metavar='timeout')
        parser.add_argument('-u_t', help='Total testing time (Minutes) for concurrent user use', metavar='timeout')
        parser.add_argument('-times', help='how many iteration want to testing, default is 1', metavar='times')
        parser.add_argument('-uf', help='Upload path from local, ex. dir: /home/erica/ , file: /home/erica', nargs='+', metavar='upload_from')
        parser.add_argument('-ud', help='Upload destination path on NAS', metavar='upload_dest')
        parser.add_argument('-dd', help='Download destination path on local', metavar="download_dest")
        parser.add_argument('-df', help='Download path from NAS', nargs='+', metavar="download_from")
        args = parser.parse_args()
        
        # If user didn't enter ip,port, use os.environ['uutip']
        self.properties = dict()
        if not args.uut_ip:
            self.uut_ip = os.environ['DEVICE_IP']
            self.port = int(os.environ['SSH_PORT'])
        else:
            self.uut_ip = args.uut_ip
            self.port = args.port

        if args.server_port:
            self.server_port = args.server_port
        else:
            self.server_port = None
        if args.server_ip:
            self.server_ip = args.server_ip
        else:
            self.server_ip = None

        if not args.u and not args.p:
            self.username = "nick0@test.com"
            self.password = "Test1234"
        elif args.u and args.p:
            self.username = args.u
            self.password = args.p
        else:
            raise Exception("Please enter both user email and password")

        self.env = os.environ.get('CLOUD_SERVER')
        
        if not self.env:
            self.env = 'qa1'
        
        self.userno = args.u_n
        if not self.userno:
            self.userno = 1

        self.metric_names = 'HTTP.DEBUG'
        self.tc_name = 'DEBUG'
        self.properties.update({'WAY': 'HTTP.DEBUG', 'TCTYPE': 'DEBUG', 'USER_NO': self.userno})

        if args.m_n:
            self.metric_names, self.tc_name = args.m_n.split('_')
            # HTTP.TP.Bi-Dir.Perf_${user_number}-user-${file_number}x${file_size}
            self.properties['WAY'] = '.'.join(self.metric_names.split('.')[0:3])
            self.properties.update({'FILE_SIZE': self.tc_name.split('-')[-1].split('x')[-1]})
            self.properties['TCTYPE'] = self.metric_names.split('.')[-1]
                                   
        if args.t:
            self.properties.update({'Time Out': args.t})
            self.timeout = args.t
        else:
            self.timeout = 0
        
        if args.u_t:
            self.properties.update({'Time out': args.u_t})
            self.user_timeout = args.u_t
        else:
            self.user_timeout = 0

        if self.timeout == 0 or self.user_timeout == 0:
            self.total_run = 1
            if args.times:
                self.total_run = int(args.times)

        self.log = logging.getLogger('MainStress')
        logging.basicConfig(filename='result.txt', format='%(asctime)s %(name)-6s %(threadName)-10s %(levelname)-4s %(message)s', level=logging.INFO, filemode='a', datefmt='%Y-%m-%d %H:%M:%S')

        self.password = "Test1234"
        self.upload_from = args.uf
        self.upload_dest = args.ud
        self.download_dest = args.dd
        self.download_from = args.df
        self.properties.update({'Device IP': self.uut_ip, 'CLOUD_SERVER': self.env, 'DEVICE_FW': os.environ.get('FW_VER')})
        self.upload_throughput_metrics = None
        self.download_throughput_metrics = None
        self.testCases = []
        self.ts = list()
        self.multi_ts = None
        self.exit_code = 0

    def run(self, user_no=1, iter=0, correct_userID=None):
        iteration = iter

        '''
        For upload report use
        '''
        if self.upload_from and self.upload_dest:
            upload_target = ''
            upload_file_no = 0
            upload_folder_no = 0

            for num, alist in enumerate(self.upload_from):
                folder, name = tool_list["rest_u{}".format(user_no)].file_or_folder(alist)

                if folder:
                    upload_folder_no += int(name.split('_')[1])
                else:
                    upload_file_no += 1
                upload_target += '{0} ;'.format(name)
            total_upload = upload_file_no + upload_folder_no
            self.properties.update({'Upload Target': '{0}'.format(upload_target)})       
            self.properties.update({'Upload files number': '{0}'.format(total_upload)})

        '''
        For download report use
        '''
        if self.download_dest and self.download_from:
            download_target = ''
            download_file_no = 0
            download_folder_no = 0
            for num, alist in enumerate(self.download_from):
                folder, name = tool_list["rest_u{}".format(user_no)].file_or_folder(alist)
                if folder:
                    download_folder_no += int(name.split('_')[1])
                else:
                    download_file_no += 1
                download_target += '{0} ;'.format(name)
            total_download = download_file_no + download_folder_no
            self.properties.update({'Download files number': '{0}'.format(total_download)})
            self.properties.update({'Download Target': '{0}'.format(download_target)})

        durations = int(self.timeout) * 60
        timedout = time.time() + durations

        if int(self.user_timeout) > 0:
            self.log_info("-----------duration: {0}".format(durations))

        stop_event = threading.Event()
        while not stop_event.isSet():
            thread_test = list()
            if self.upload_from and self.upload_dest:
                for loc, task in enumerate(self.upload_from):
                    w = threading.Thread(target=self.worker_ul, name='Upload-%s' % (user_no), args=(task, self.upload_dest, loc, user_no,))
                    thread_test.append(w)
                    w.start()
                    time.sleep(4)

            if self.download_dest and self.download_from:
                for j, download_from in enumerate(self.download_from):
                    if not self.upload_dest:
                        self.upload_dest = None
                    if not self.upload_from:
                        self.upload_from = [None]*len(self.download_from)

                    t = threading.Thread(target=self.worker_dl, name='Download-%s' % (user_no), args=(self.download_dest, download_from, j, user_no,))
                    thread_test.append(t)
                    t.start()
                    time.sleep(4)

            threadname = threading.currentThread().getName().replace('-','_')

            # Let the thread jobs all done, and proceed the throughput measurement
            map(threading.Thread.join, thread_test)

            if int(self.user_timeout) > 0:
                self.log_info("Time out be set (in Run)")
                if time.time() > timedout:
                    stop_event.set()
                    self.log_info("Stopping as you wish testing {0} minutes".format(self.user_timeout))
            elif iteration + 1 >= self.total_run:
                stop_event.set()
                if int(self.user_timeout) == 0:
                    self.log_info("Iteration be set")
                    self.log_info("Stopping as you wish testing {0} times".format(self.total_run))
                else:
                    self.log_info("Concurrent Time out be set (in Run)")

            # Generate each TestSuite for DL & UL
            self.ts = self.multiTestSuite(iteration=iteration)

            # Handle the case that self.download_dest folder will be wrong after threading actions
            if self.download_dest and self.download_from:
                temp_dfList = self.download_dest.split('/')
                foldername = temp_dfList[-2]
                self.download_dest = self.download_dest.replace(foldername,threadname)

            # Delete the file on NAS every time when upload job finishes
            if self.upload_from and self.upload_dest:
                upload_dest = tool_list["rest_u{}".format(user_no)].correct_userID_path(self.upload_dest, correct_userID)

                for loc, path in enumerate(self.upload_from):
                    dlul_list["rest_u{}".format(user_no)].delete_dir_files_on_nas(path, upload_dest)

            # Delete the file on local environment every time when download job finishes
            if self.download_dest and self.download_from:
                for loc, path in enumerate(self.download_from):
                    folder_or_file, name = tool_list["rest_u{}".format(user_no)].file_or_folder(path)
                    dl_path = os.path.join(self.download_dest, name)
                    self.log_info('deleted path : {}'.format(dl_path))
                    if os.path.exists(dl_path):
                        if not folder_or_file:
                            self.log_info('Delete the downloaded file on local: {0}'.format(dl_path))
                            os.remove(dl_path)
                        else:
                            shutil.rmtree(dl_path)
                    else:
                        self.log_info('Cannot delete {0} because it does not exist.'.format(dl_path))

            ''' Throughput related metric'''
            if self.upload_from and self.upload_dest:
                new_name = self.metric_names
                if self.properties.get('TCTYPE') == 'Perf':
                    new_name = self.metric_names.replace('HTTP.TP', 'TP')
                    user_number, user, total_size = self.tc_name.split('-')
                    file_number, file_size = total_size.split('x')
                    if new_name == 'TP.Bi-Dir.Perf':
                        new_name = new_name.replace('TP.Bi-Dir.Perf', 'TP.Bi-Dir.UL.Perf')
                    ul_metric = '%s.' % file_number
                    if int(file_number) > 1:
                        ul_metric += 'con.'
                    ul_metric += 'file'
                    new_name = new_name.replace('Perf', ul_metric)
                types, min_value, max_value, average_value = tool_list["rest_u{}".format(user_no)].get_throughput(dlul_list["rest_u{}".format(user_no)].ul_throughput, 'upload')
                self.upload_throughput_metrics = [['{0}.Avg'.format(new_name), '{0}'.format(average_value), 'kB/s'],
                                                  ['{0}.Min'.format(new_name), '{0}'.format(min_value), 'kB/s'],
                                                  ['{0}.Max'.format(new_name), '{0}'.format(max_value), 'kB/s']]

            if self.download_dest and self.download_from:
                new_name = self.metric_names
                if self.properties.get('TCTYPE') == 'Perf':
                    new_name = self.metric_names.replace('HTTP.TP', 'TP')
                    user_number, user, total_size = self.tc_name.split('-')
                    file_number, file_size = total_size.split('x')
                    if new_name == 'TP.Bi-Dir.Perf':
                        new_name = new_name.replace('TP.Bi-Dir.Perf', 'TP.Bi-Dir.DL.Perf')
                    dl_metric = '%s.' % file_number
                    if int(file_number) > 1:
                        dl_metric += 'con.'
                    dl_metric += 'file'
                    new_name = new_name.replace('Perf', dl_metric)

                types, min_value, max_value, average_value = tool_list["rest_u{}".format(user_no)].get_throughput(dlul_list["rest_u{}".format(user_no)].dl_throughput, 'download')
                self.download_throughput_metrics = [['{0}.Avg'.format(new_name), '{0}'.format(average_value), 'kB/s'],
                                                    ['{0}.Min'.format(new_name), '{0}'.format(min_value), 'kB/s'],
                                                    ['{0}.Max'.format(new_name), '{0}'.format(max_value), 'kB/s']]

            self.ts = self.multiTestSuite(self.tc_name, self.upload_throughput_metrics, self.download_throughput_metrics, iteration)
            iteration += 1

    def run_ul_test(self, src, dest, unum, user_no):
        error = False
        result = False
        output = commands.getoutput('du -sh %s' % src)
        size = output.split('\t')[0]
        file_type = tool_list["rest_u{}".format(user_no)].get_type(src)
        tname = 'UL_User{0}_{1}_{2}B_{3}'.format(user_no, file_type.upper(), size, unum)
        error_message = ''
        try:
            result = dlul_list["rest_u{}".format(user_no)].upload(src=src, dest=dest, userno=user_no, item_no=unum)
        except Exception as ex:
            print "***Exception: {0} with {1}".format(ex, sys.exc_info()[0])
            error_message = ex
            error = True
            self.exit_code = 1

        tc = TestCase(name=tname, classname='.'.join(['UL', self.properties.get('WAY')]))

        if not result or error:
            message = 'Failed to upload'
            if error:
                message += ' with Exception: {0} and sys_exe_info:{1}'.format(error_message, sys.exc_info()[0])
            tc.add_failure_info(message=message)

        return tc

    def run_dl_test(self, dd=None, df=None, dnum=0, user_no=1):
        error = False
        result = False
        error_message = ''
        # If user gives incorrect userID, provide the correct one and replace download_from with the correct one
        df = tool_list["rest_u{}".format(user_no)].correct_userID_path(df, dlul_list["rest_u{}".format(user_no)].correct_userID)

        file_type = tool_list["rest_u{}".format(user_no)].get_type(df)
        _, fname = tool_list["rest_u{}".format(user_no)].file_or_folder(df)
        file_exist, nas_info_dic, pa = tool_list["rest_u{}".format(user_no)].search_id(df)

        # Check if the folder is exists on NAS, if exists, then continue, else return
        if file_exist:
            try:
                result = dlul_list["rest_u{}".format(user_no)].download_dir_files(download_dest=dd, download_from=df)
            except Exception as ex:
                print "***Exception: {0} with {1}".format(ex, sys.exc_info()[0])
                error_message = ex
                error = True
                self.exit_code = 1

            download_size = os.path.getsize(dd+fname)
            tname = 'DL_User{0}_{1}_{2}MB_{3}'.format(user_no, file_type.upper(), download_size / (1024.0 * 1024.0), dnum)

        else:
            tname = 'DL_User{0}_{1}_{2}MB_{3}'.format(user_no, file_type.upper(), 0, dnum)
            error_message = 'There is no file on NAS'
            error = True
            self.exit_code = 1

        tc = TestCase(name=tname, classname='.'.join(['DL', self.properties.get('WAY')]))

        if not result or error:
            message = 'Failed to download'
            if error:
                message += ' with Exception: {0} and sys_exe_info:{1}'.format(error_message, sys.exc_info()[0])
            tc.add_failure_info(message=message)

        return tc

    ## UL Thread worker ##
    def worker_ul(self, uf_path, ud, i, user_no):
        ''' upload '''
        print 'start upload'
        self.testCases.append(self.run_ul_test(src=uf_path, dest=ud, unum=i, user_no=user_no))

    ## DL Thread worker ##
    def worker_dl(self, dd=None, df=None, dnum=0, user_no=1):
        ''' download '''
        print 'start download'
        self.testCases.append(self.run_dl_test(dd, df, dnum, user_no))

    def multiTestSuite(self, throughput_tc_name=None, upload_throughput_metrics=None, download_throughtput_metrics=None, iteration=0):
        TCTYPE = self.properties.get('TCTYPE')
        testcases = list()

        if upload_throughput_metrics is not None:
            testcases.append(TestCase(name=throughput_tc_name, classname='.'.join([self.properties.get('WAY'), 'UL']), metrics=upload_throughput_metrics))

        if download_throughtput_metrics is not None:
            testcases.append(TestCase(name=throughput_tc_name, classname='.'.join([self.properties.get('WAY'), 'DL']), metrics=download_throughtput_metrics))

        if testcases:
            if TCTYPE == 'Perf' or self.properties.get('WAY') == 'HTTP.DEBUG':
                self.ts.append(TestSuite(name='Perf-%s' % iteration, package='Stress Test', test_cases=testcases,
                                                   properties=self.properties, timestamp=get_timestamp()))
        
        elif (TCTYPE == 'Stress'and not self.user_timeout) or self.properties.get('WAY') == 'HTTP.DEBUG':
            self.ts.append(TestSuite(name='Stress-%s' % iteration, package='Stress Test',
                           test_cases=self.testCases, properties=self.properties, timestamp=get_timestamp()))
            self.testCases = []
        
        return self.ts

    def multi_user(self, user_no, origin_dd, iteration, correct_userID):
        try:
            if origin_dd is not None:
                self.download_dest = origin_dd + 'User_%s/' % user_no

            self.run(user_no, iteration, correct_userID)
        except Exception as ex:
            print "***Exception: {0} with {1}".format(ex, sys.exc_info()[0])
            self.exit_code = 1
        
        ts = TestSuite(name='iteration-%s' % iteration, package='Stress Test',
                                 test_cases=self.testCases, properties=self.properties, timestamp=get_timestamp())
        return ts
        
    def worker_multi_user(self, user_no, origin_dd, iteration, correct_userID):
        self.multi_ts = self.multi_user(user_no, origin_dd, iteration, correct_userID)

    def log_info(self, msg):
        '''
        Save info in log and print on the screen at the same time
        '''
        self.log.info(msg)
        print msg


    def log_error(self, msg):
        '''
        Save error in log and raise exception at the same time
        '''
        self.log.error(msg)
        raise Exception(msg)

def get_timestamp():
    return datetime.now().replace(microsecond=0).strftime('%Y%m%d%H%M%S')

'''
def delete_user_folder(uut_ip=None, port=None,server_ip=None, server_port=None):

    # adb object to connect to device and execute commands
    adb = ADB(uut_ip=uut_ip, port=str(port),adbServer=server_ip, adbServerPort=server_port)

    # Connect to device via defined ip address:port
    adb.connect()
    time.sleep(2)

    deleted_path = '/data/wd/diskVolume0/restsdk/userRoots/' + dlul.correct_userID + '/*'
    print 'Removing contents in %s' % deleted_path
    adb.executeShellCommand('rm -rf {0}'.format(deleted_path), consoleOutput=True)
    time.sleep(5)

    # Disconnect from device, and kill the running adb server on local environment
    #adb.disconnect()
    #adb.killServer()
'''

if __name__ == '__main__':

    origin_dd = None

    if '-dd' in sys.argv:
        dd_index = sys.argv.index('-dd')
        origin_dd = sys.argv[dd_index+1]

    if '-u_n' in sys.argv:
        index = sys.argv.index('-u_n')
        if '-t' in sys.argv and int(sys.argv[index+1]) > 1:
            sys.argv[sys.argv.index('-t')] = '-u_t'

    test = Test()

    '''
    # SCP upload the files first before downloading
    for user in xrange(int(test.userno)):
        #username = "Nick_%s@abc.com" % user

        if user == 1:
            username = "user0@test.com"
        else:
            username = "user4@test.com"

        if int(test.userno) == 1:
            username = test.username

        rest = RestAPI(uut_ip=test.uut_ip, username=username, password=test.password, env=test.env)
        tool = Tool(uut_ip=test.uut_ip, email=username, password=test.password, env=test.env,port=test.port,server_ip=test.server_ip,server_port=test.server_port)
        user_id = rest.get_user_id()
        if test.download_from and test.upload_from:
            print "start to upload data_set to %s folder: %s for download use" % (username, user_id)
            if test.upload_dest:
                for uf in test.upload_from:
                    folder_exist, fname = tool.file_or_folder(uf)
                    scp_path = test.upload_dest+fname
                    if not folder_exist:
                       scp_path += '/'
                    if scp_path in test.download_from:
                        raise Exception("When doing Con.Bi-Dir, the path of the download from should not same as upload from")
            tool.upload_folder_file2NAS(test.upload_from, test.download_from, test.port, user_id)
    '''

    ## start test ##
    try:
        con_user = []
        itera = 0
        rest_list = {}
        dlul_list = {}
        tool_list = {}

        if int(test.userno) > 1:
            duration = int(test.user_timeout)*60
            timeout = time.time() + duration
            test.log_info("--------duration for testing concurrent user: {0}".format(duration))
            pill2kill = threading.Event()
            for user in xrange(int(test.userno)):
                username = "nick%s@test.com" % user
                rest_list["rest_u{}".format(user)] = RestAPI(uut_ip=test.uut_ip, env=test.env, username=username,
                                                          password='Test1234')
                dlul_list["rest_u{}".format(user)] = DL_UL(uut_ip=test.uut_ip, port=test.port, server_ip=test.server_ip, server_port=test.server_port,
                  rest=rest_list["rest_u{}".format(user)])

                tool_list["rest_u{}".format(user)] = Tool(uut_ip=test.uut_ip, port=test.port, server_ip=test.server_ip, server_port=test.server_port,
                 rest=rest_list["rest_u{}".format(user)])

            while not pill2kill.isSet():
                test.log_info("****** Concurrent iteration: {0} ********".format(itera))
                for user in xrange(int(test.userno)):
                    try:
                        u = threading.Thread(target=test.worker_multi_user, name='User-%s' % user, args=(user, origin_dd, itera, str(rest_list["rest_u{}".format(user)].get_user_id()),))
                        con_user.append(u)
                        u.start()
                        time.sleep(4)
                    except Exception as e:
                        if "status code:429" in e.message:
                            test.log_info(e)
                            time.sleep(5)
                            continue

                # Let the thread jobs all done, and proceed the throughput measurement
                map(threading.Thread.join, con_user)

                # timeout be set or run times
                if int(test.user_timeout) > 0:
                    if time.time() > timeout:
                        pill2kill.set()
                        test.log_info("Total testing {0} mins".format(test.user_timeout))
                elif itera >= 1:
                    pill2kill.set()
                    test.log_info("Total testing {0} times".format(int(itera)))

                test.testCases = []
                test.ts.append(test.multi_ts)
                itera += 1
        else:
            test.log_info("Single user: ")
            rest_list["rest_u1"] = RestAPI(uut_ip=test.uut_ip, username=test.username, password=test.password, env=test.env)
            dlul_list["rest_u1"] = DL_UL(uut_ip=test.uut_ip, port=test.port,server_ip=test.server_ip, server_port=test.server_port,rest=rest_list["rest_u1"])
            tool_list["rest_u1"] = Tool(uut_ip=test.uut_ip,port=test.port,server_ip=test.server_ip,server_port=test.server_port,rest=rest_list["rest_u1"])
            test.run(correct_userID=dlul_list["rest_u1"].correct_userID)

    except Exception as e:
        print 'outside layer: {0}'.format(e.message)
        test.exit_code = 1

    finally:
        # Remove existed report files
        resultfile = os.path.join(os.getcwd()+'/output', 'output.xml')
        report_file = glob(resultfile)
        if report_file:
            for f in report_file:
                os.remove(f)
                test.log_info("Remove {} file".format(f))
        # Generate Report
        if not os.path.exists(os.getcwd()+'/output'):
            os.mkdir(os.getcwd()+'/output')
        result_file = os.path.join(os.getcwd()+'/output', 'output.xml')
        with open(result_file, 'a') as f:
            TestSuite.to_file(f, test.ts, prettyprint=True)
            f.close()

        # Remove user folder on NAS after test
        #delete_user_folder(uut_ip=test.uut_ip, port=test.port,server_ip=test.server_ip,server_port=test.server_port)
        print "Exit Code (PASS): ", test.exit_code
        sys.exit(test.exit_code)
