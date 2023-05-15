__author__ = 'Ben Tsui <ben.tsui@wdc.com>'

# std modules
import ast
import json
import re
import socket
import time
import xmlrpclib

from types import FunctionType

# platform modules
import common_utils
from platform_libraries.ssh_client import SSHClient


class DESKTOP_SYNC(object):

    def get_methods(self, cls):
        return [x for x, y in cls.__dict__.items() if type(y) == FunctionType]

    def __init__(self, rest_obj, client_os='MAC', client_ip=None, client_username=None, client_password=None, kdd_product=None):
        """
            Below code is to get the method list in MAC/WIN class,
            create wrapper functions in DESKTOP_SYNC class,
            so that we can call them with the same function names in MAC/WIN OS
        """
        def wrapper_function(cls_obj, method_name):
            return lambda *arg, **kwarg: getattr(cls_obj, method_name)(*arg, **kwarg)

        self.log = common_utils.create_logger(overwrite=False)
        client_cls = {"MAC": MAC, "WIN": WIN}.get(client_os)
        client_obj = client_cls(rest_obj, client_ip=client_ip, client_username=client_username, client_password=client_password, kdd_product=kdd_product)
        method_list = self.get_methods(client_cls)
        for m in method_list:
            setattr(self, m, wrapper_function(client_obj, m))

    def compare_filename(self, file_list_before, file_list_after):
        diff = list(set(file_list_before) ^ set(file_list_after))
        if diff:
            self.log.warning("File names are not match! The different files:{}".format(diff))
            return False
        else:
            self.log.info("File names are match")
            return True

    def compare_checksum(self, checksum_dict_before, checksum_dict_after):
        diff = list(file for file in checksum_dict_before.keys() \
                    if checksum_dict_before.get(file) != checksum_dict_after.get(file))
        if diff:
            self.log.warning("MD5 comparison failed! The different files:")
            for file in diff:
                self.log.warning("{}: md5 before [{}], md5 after [{}]".
                                 format(file, checksum_dict_before.get(file), checksum_dict_after.get(file)))
            return False
        else:
            return True


class MAC(object):

    def __init__(self, rest_obj, client_ip=None, client_username=None, client_password=None, kdd_product=None):

        self.log = common_utils.create_logger(overwrite=False)
        self.ssh = SSHClient(client_ip, client_username, client_password)
        self.client_username = client_username
        self.client_password = client_password
        self.owner = rest_obj
        self.sync_http_port = None
        self.kdd_http_port = None
        self.app_path = "/Users/{}/Library/Containers/com.wdc.WDDesktop.WDDesktopFinderSync".format(client_username)

        if kdd_product == 'ibi':
            self.kdd_product = 'ibi'
            self.app_name = 'ibiDesktop'
            self.kdd_executable = 'ibikdd'
        elif kdd_product == 'WD':
            self.kdd_product = 'WD'
            self.app_name = "WDDesktop"
            self.kdd_executable = 'kdd'
  


    def connect(self):
        self.ssh.connect()

    def disconnect(self):
        self.ssh.close()

    def stop_kdd_process(self):
        # Stop kdd
        status, response = self.ssh.execute('ps aux | grep Desktop | grep {}'.format(self.kdd_executable))
        if self.app_name in response:
            for element in response.split("\n"):
                if 'ps aux | grep Desktop | grep {}'.format(self.kdd_executable) not in element:
                    PID = element.split()[1]
                    status, response = self.ssh.execute('kill {}'.format(PID))
                    time.sleep(1)        
            time.sleep(4)  # Wait for killing process
            # Check if kdd is stopped.
            status, response = self.ssh.execute('ps aux | grep Desktop | grep {}'.format(self.kdd_executable))
            if self.app_name in response:
                return False
        return True

    def replace_kdd(self, kdd_url=''):
        # Download new kdd to correct location
        kdd_bin_location = "/Library/Application Support/{}.app/Contents/Resources/{}".format(self.app_name, self.kdd_executable)
        status, response = self.ssh.sudo_execute('curl "{}" --output "{}"'.format(kdd_url, kdd_bin_location))
        if "fail" in response or "Fail" in response:
            return False
        # Check if the kdd exist
        status, response = self.ssh.sudo_execute('ls "{}"'.format(kdd_bin_location))
        if 'No such file or directory' in response:
            return False
        # change kdd to executable
        status, response = self.ssh.sudo_execute('chmod +x "{}"'.format(kdd_bin_location))
        if "fail" in response or "Fail" in response:
            return False
        # Delete the odl log
        if self.kdd_product == 'ibi':
            folder = 'com.ibi.ibiDesktop.ibiDesktopFinderSync'
        elif self.kdd_product == 'WD':
            folder = 'com.wdc.WDDesktop.WDDesktopFinderSync'
        kdd_log_location = '~/Library/Containers/{}/Data/log/*'.format(folder)
        status, response = self.ssh.execute('rm -fr {}'.format(kdd_log_location))
        return True

    def start_kdd_process(self):
        self.log.info("Start {}.exe ...".format(self.kdd_executable))
        kdd_bin_location = "/Library/Application Support/{}.app/Contents/Resources".format(self.app_name)
        status, response = self.ssh.execute('"{}/run_kdd.sh" &'.format(kdd_bin_location))
        status, response = self.ssh.execute('ps aux | grep Desktop | grep {}'.format(self.kdd_executable))
        if self.app_name not in response:
            return False
        time.sleep(10)  # Wait for kdd is launched and drive mounted.
        return True

    def check_kdd_version(self, kdd_version=''):
        KDA_ver_in_device = None
        kdd_ver_in_device = None
        if self.kdd_product == 'ibi':
            folder = 'com.ibi.ibiDesktop.ibiDesktopFinderSync'
        elif self.kdd_product == 'WD':
            folder = 'com.wdc.WDDesktop.WDDesktopFinderSync'
        kdd_log_location = '~/Library/Containers/{}/Data/log/kddprivate.log'.format(folder)

        # This is a workaround because kddprivate.log will be flash out only when kdd stopped.
        self.stop_kdd_process()
        self.start_kdd_process()
        
        status, response = self.ssh.execute('cat {} | head -n 3'.format(kdd_log_location))
        for element in response.split('\n'):
            if "ver" in element and "version" in element:
                temp = ast.literal_eval(element)
                KDA_ver_in_device = temp.get("ver")
                kdd_ver_in_device = temp.get ("version")
                break
        if kdd_ver_in_device != kdd_version:
            return False
        return True

    def get_mount_path(self, device_id=None, *arg, **kwarg):
        mount_path = None
        status, response = self.ssh.execute('mount')
        # USe device-id to find mount_path
        if device_id:
            for element in response.split('\n'):
                if device_id in element:
                    mount_path = element.split(' (')[0].split(' on ')[1]
                    break
        return mount_path
   
    def get_file_size(self, file_path=None, unit='m', **kwarg):
        # unit='g', unit is GB
        # unit='m', unit is MB
        # unit='k', unit is KB
        total_file_size = None
        status, response = self.ssh.execute('du -cs{} {}'.format(unit, file_path))
        if 'total' not in response.split('\n')[-1]:
            print '### WARNING: There is no "total" label in response. ###'
        else:
            total_file_size = float(response.split('\n')[-1].split()[0])
        return total_file_size


    def file_transfer(self, source_path=None, dest_path=None, **kwarg):
        # start to transfer file
        upload_speed = 0
        status, response = self.ssh.execute('time cp -fr {} {}'.format(source_path, dest_path), timeout=1800)
        duration = float(re.findall('real\t\d+m.+s', response)[0].split('real\t')[1].split('m')[0]) * 60 + \
                      float(re.findall('real\t\d+m.+s', response)[0].split('m')[1].split('s')[0])
        upload_speed = (self.get_file_size(file_path=source_path))/duration  # This unit is MB after calculating.
        return upload_speed


    def read_write_perf(self):
        def _get_kdd_mount_path():
            kdd_mount_path = None
            status, response = self.ssh.execute('mount')
            for element in response.split('\n'):
                if self.app_name in element:
                    kdd_mount_path = element.split(' (')[0].split(' on ')[1]
                    break
            if kdd_mount_path:
                return kdd_mount_path
            else:
                return False
        kdd_mount_path = _get_kdd_mount_path()
        if not kdd_mount_path:
            return False, False, False, False
        # Get the size of testing dateset
        status, response = self.ssh.execute('du -cm ~/{}'.format('5G_Single'))
        if 'total' not in response.split('\n')[-1]:
            print '### WARNING: There is no "total" label in response. ###'
            return False, False, False, False
        else:
            single_file_size = float(response.split('\n')[-1].split()[0])
        status, response = self.ssh.execute('du -cm ~/{}'.format('5G_Standard'))
        if 'total' not in response.split('\n')[-1]:
            print '### WARNING: There is no "total" label in response. ###'
            return False, False, False, False
        else:
            standard_file_size = float(response.split('\n')[-1].split()[0])
        
        # Remove testing file first
        status, response = self.ssh.execute('rm -fr "{}"/{}'.format(kdd_mount_path, '5G_Single'))
        status, response = self.ssh.execute('rm -fr ~/kdd_test_Mac')
        
        # Copy the single file from Mac to NAS.
        status, response = self.ssh.execute('time cp -fr ~/{} "{}"'.format('5G_Single', kdd_mount_path), timeout=3600)
        duration = float(re.findall('real\t\d+m.+s', response)[0].split('real\t')[1].split('m')[0]) * 60 + \
                      float(re.findall('real\t\d+m.+s', response)[0].split('m')[1].split('s')[0])
        SINGLE_WRITE_speed = single_file_size/duration

        # Copy the single file from NAS to Mac.
        status, response = self.ssh.execute('time cp -fr "{}"/5G_Single ~/kdd_test_Mac'.format(kdd_mount_path), timeout=3600)
        duration = float(re.findall('real\t\d+m.+s', response)[0].split('real\t')[1].split('m')[0]) * 60 + \
                      float(re.findall('real\t\d+m.+s', response)[0].split('m')[1].split('s')[0])
        SINGLE_READ_speed = single_file_size/duration

        # Remove testing file first
        status, response = self.ssh.execute('rm -fr "{}"/{}'.format(kdd_mount_path, '5G_Standard'))
        status, response = self.ssh.execute('rm -fr ~/kdd_test_Mac')

        # Copy the standard files from Mac to NAS.
        status, response = self.ssh.execute('time cp -fr ~/{} "{}"'.format('5G_Standard', kdd_mount_path), timeout=3600)
        duration = float(re.findall('real\t\d+m.+s', response)[0].split('real\t')[1].split('m')[0]) * 60 + \
                      float(re.findall('real\t\d+m.+s', response)[0].split('m')[1].split('s')[0])
        STANDARD_WRITE_speed = standard_file_size/duration

        # Copy the standard files from NAS to Mac.
        status, response = self.ssh.execute('time cp -fr "{}"/5G_Standard ~/kdd_test_Mac'.format(kdd_mount_path), timeout=3600)
        duration = float(re.findall('real\t\d+m.+s', response)[0].split('real\t')[1].split('m')[0]) * 60 + \
                      float(re.findall('real\t\d+m.+s', response)[0].split('m')[1].split('s')[0])
        STANDARD_READ_speed = standard_file_size/duration

        # Remove testing file
        status, response = self.ssh.execute('rm -fr "{}"/{}'.format(kdd_mount_path, '5G_Standard'))
        status, response = self.ssh.execute('rm -fr ~/kdd_test_Mac')        

        return SINGLE_WRITE_speed, SINGLE_READ_speed, STANDARD_WRITE_speed, STANDARD_READ_speed

    def install_app(self, app_version, env='dev1', app_folder='desktop_sync_pkg'):
        # Todo: Download latest version if app_version is not specified?
        app_url = "http://repo.wdc.com/content/repositories/desktop/kamino_desktop/"
        if app_version.startswith('1.1.0'):
            app_name = 'Kamino-{0}-{1}'.format(app_version.replace('1.1.0.', '1.1.0-'), env)
            app_url += "KaminoDesktop_Mac_1.1.0/{}/{}.zip".format(app_version, app_name)
        else:
            index = '.'.join(app_version.split('.')[:-1])  # For example: index is like '1.1.1'
            app_name = 'Kamino-{0}-{1}'.format(app_version.replace('{}.'.format(index), '{}-'.format(index)), env)
            app_url += "KaminoDesktop_Mac/{}/{}.zip".format(app_version, app_name)

        app_path = '/Users/{0}/{1}'.format(self.client_username, app_folder)
        if not self.ssh.check_folder_exist(app_path):
            self.ssh.create_folder(app_path)

        if self.ssh.check_file_exist("{}/{}.zip".format(app_path, app_name)):
            self.log.info("{} has already been downloaded before".format(app_name))
        else:
            status, response = self.ssh.execute('/usr/local/bin/wget -q -nv -t 10 "{}" -P {}'.
                                                format(app_url, app_path))
            if status == 0:
                self.log.info("Download complete")
            else:
                self.log.error("Donwload failed, error message: {}".format(response))

        self.log.info("Unzip the downloaded app")
        self.ssh.execute('unzip -oq {0}/{1}.zip -d {0}'.format(app_path, app_name))
        if not self.ssh.check_file_exist("{}/{}.pkg".format(app_path, app_name)):
            self.log.error("Failed to unzip downloaded app")
            return False

        # Need to use 'sudo visudo' and set "{user_name} ALL=(ALL) NOPASSWD:ALL" in privilege specification
        self.log.info("Installing WD Sync")
        status, response = self.ssh.execute('sudo installer -store -pkg "{}/{}.pkg" -target /'.
                                             format(app_path, app_name))
        if 'Install failed' in response:
            return False
        else:
            return True

    def uninstall_app(self):
        delete_tool_path = "/Library/Application\ Support/WDDesktop.app/Contents/Resources/uninstall.sh"
        if not self.ssh.check_file_exist(delete_tool_path):
            self.log.error("Cannot find specified delete tool")

        # Need to use 'sudo visudo' and set "{user_name} ALL=(ALL) NOPASSWD:ALL" in privilege specification
        status, response = self.ssh.execute("sudo {}".format(delete_tool_path))
        if status == 0:
            self.log.info("Uninstall app successfully, response: {}".format(response))
            return True
        else:
            self.log.error("Uninstall app failed, response: {}".format(response))
            return False

    def start_kdd_wdsync_process(self):
        self.ssh.execute_background('/Library/Application\ Support/WDDesktop.app/Contents/Resources/wddesktop.sh')

    def check_kdd_wdsync_process(self):
        kdd_process = False
        wdsync_process = False
        status, response = self.ssh.execute('ps aux | grep WDDesktop')
        if '/Library/Application Support/WDDesktop.app/Contents/Resources/kdd' in response:
            self.log.info('kdd process is running')
            kdd_process = True
        else:
            self.log.warning('kdd process is not running!')

        if '/Library/Application Support/WDDesktop.app/Contents/Resources/wdsync' in response:
            self.log.info('wdsync process is running')
            wdsync_process = True
        else:
            self.log.warning('wdsync process is not running!')

        return kdd_process, wdsync_process

    def stop_kdd_wdsync_process(self):
        self.log.info("Trying to kill wddesktop process")
        status, response = self.ssh.execute('ps aux | grep wddesktop.sh')
        if status == 0 and response:
            plist = response.split('\n')
            for p in plist:
                if '/Resources/wddesktop.sh' in p:
                    pid = p.strip().split()[1]
                    self.log.info("Killing pid: {}".format(pid))
                    self.ssh.execute('kill {}'.format(pid))
        else:
            self.log.error("Unable to kill KDD and WD Sync process, error msg:{}".format(response))

    def get_sync_http_port(self):
        status, response = self.ssh.execute('cat {}/Data/Sync/httpPort.json'.format(self.app_path))
        if status == 0 and 'HTTPPort' in response:
            self.sync_http_port = json.loads(response)['HTTPPort']
            return self.sync_http_port
        else:
            self.log.error("Failed to get sync http port, error message: {}".format(response))
            return None

    def get_kdd_http_port(self):
        status, response = self.ssh.execute('cat {}/Data/httpPort.json'.format(self.app_path))
        if status == 0 and 'HTTPPort' in response:
            self.kdd_http_port = json.loads(response)['HTTPPort']
            return self.kdd_http_port
        else:
            self.log.error("Failed to get kdd http port, error msg: {}".format(response))
            return None

    def kdd_login(self, id_token, refresh_token):
        url = "http://localhost:{}/kdd/v1/user/login?accessToken={}&refreshToken={}". \
              format(self.kdd_http_port, id_token, refresh_token)
        status, response = self.ssh.execute('curl -s -w "{0}" -X POST "{1}"'.format('%{http_code}', url))
        # Todo: use 204 no content?
        if status == 0 and response == "204":
            self.log.info("KDD login successfully")
            return True
        else:
            self.log.error("KDD login failed, error msg: {}".format(response))
            return False

    def kdd_log_status(self):
        url = "http://localhost:{}/kdd/v1/user/status".format(self.kdd_http_port)
        status, response = self.ssh.execute('curl -s -w "{}" "{}"'.format('%{http_code}', url))
        # Todo: use 204 no content?
        if status == 0 and response == "204":
            self.log.info("User already logged in KDD")
            return True
        else:
            self.log.info("User is not logged in KDD")
            return False

    def kdd_logout(self):
        url = "http://localhost:{}/kdd/v1/user/logout".format(self.kdd_http_port)
        status, response = self.ssh.execute('curl -s -w "{0}" -X POST "{1}"'.format('%{http_code}', url))
        # Todo: use 204 no content?
        if status == 0 and response == "204":
            self.log.info("User logged out successfully")
            return True
        else:
            self.log.error("User logged out failed")
            return False

    def create_sync(self, src_path, dst_path):
        data_temp = json.dumps({"SrcPath": src_path, "DstPath": dst_path})
        # todo: We need to send '\'' for ' in data info in curl commands, are there any better ways to do so?
        if "'" in data_temp:
            data = data_temp.replace("'", "'\\''")

        url = "http://localhost:{}/sync/v1/folders -d '{}'".format(self.sync_http_port, data)
        status, response = self.ssh.execute('curl -s -w "{0}" -X POST {1}'.format('%{http_code}', url))
        if status == 0 and response == "201":
            self.log.info("Create sync successfully")
            return True
        else:
            self.log.error("Create sync failed")
            return False

    def delete_sync(self, src_path):
        url = 'curl -s -w "{}" -X DELETE http://localhost:{}/sync/v1/folders?path={}' \
              .format('%{http_code}', self.sync_http_port, src_path)
        status, response = self.ssh.execute(url)
        if status == 0 and response == "204":
            self.log.info("Delete sync info successfully")
            return True
        else:
            self.log.error("Failed to delete sync info, error message: {}".format(response))
            return False

    def get_sync(self):
        url = 'curl -s http://localhost:{}/sync/v1/folders'.format(self.sync_http_port)
        status, response = self.ssh.execute(url)
        if status == 0:
            self.log.info("Get sync info successfully")
            if response == "[]":
                self.log.warning("There is no sync setup before")
                return None
            else:
                return response
        else:
            self.log.error("Failed to get sync info! Error message: {}".format(response))
            return None

    def check_sync_status(self):
        # Todo: Wait for RD to implement it
        status, response = self.ssh.execute('')
        print status, response

    def get_nas_mount_path(self, owner_first_name, nas_folder_name):
        device_id = self.owner.get_device_id()
        nas_mount_path = "{0}/Data/volumes/{1}/{2}'s My Cloud Home/{3}".\
                         format(self.app_path, device_id, owner_first_name, nas_folder_name)
        return nas_mount_path

    def check_local_folder_exist(self, folder_path):
        result = self.ssh.check_folder_exist(folder_path)
        return result

    def get_local_checksum_dict(self, folder_path):
        file_list = self.ssh.get_file_list(folder_path)
        if not file_list:
            self.log.error("Failed to get file list from: {}".format(folder_path))
        else:
            checksum_dict = dict()
            for file in file_list:
                md5 = self.ssh.get_file_checksum("{0}/{1}".format(folder_path, file))
                if md5:
                    checksum_dict[file] = md5
                else:
                    self.log.error("Failed to get md5 checksum of file: {}".format(file))
                    return None

            return checksum_dict

    def download_files_from_file_server(self, server_ip, folder_path, download_to):
        download_from = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(server_ip), folder_path)
        cur_dir = folder_path.count('/')
        url = '/usr/local/bin/wget -q -t 10 --no-host-directories --cut-dirs={0} -r --no-passive {1} -P {2}'.\
              format(cur_dir, download_from, download_to)
        status, response = self.ssh.execute(url)
        if status == 0:
            return True
        else:
            return False

    def create_folder(self, folder_path):
        self.ssh.create_folder(folder_path)

    def delete_folder(self, folder_path):
        self.ssh.delete_folder(folder_path)

    def delete_file(self, file_path):
        self.ssh.delete_file(file_path)


class WIN(object):

    def __init__(self, rest_obj, client_ip=None, kdd_product=None, **kwarg):
        self.client_ip = client_ip
        self.sync_http_port = None
        self.kdd_http_port = None
        self.log = common_utils.create_logger(overwrite=False)
        #self.execute_kdd()
        self.owner = rest_obj
    
    def XMLRPCclient(self, cmd):
        try:
            print "{0} \r\n".format(cmd)
            server = xmlrpclib.ServerProxy("http://{}:12345/".format(self.client_ip))
            result = server.command(cmd)  # server.command() return the result which is in string type.
            print result
            return result
        except socket.error as e:
            e = str(e)
            print "socket.error: {0}\nCould not connect with the socket-server: {1}".format(e, self.client_ip)
            self.log.error("error message: {}".format(e))
            return e

    def connect(self):
        pass

    def disconnect(self):
        pass

    def stop_kdd_process(self, kdd_product='ibi'):
        if kdd_product == 'ibi':
            kdd_executable = 'ibikdd'
        elif kdd_product == 'WD':
            kdd_executable = 'kdd'
        self.log.info("Trying to kill {} process".format(kdd_executable))
        result = self.XMLRPCclient('Stop-Process -processname {}'.format(kdd_executable))
        result = self.XMLRPCclient('Get-Process {}'.format(kdd_executable))
        if 'Cannot find a process with the name "{}"'.format(kdd_executable) in result:
            return True
        else:
            self.log.error("Unable to kill {} process, error msg:{}".format(kdd_executable, result))
            return False

    def replace_kdd(self, kdd_url='', kdd_product='ibi'):
        if kdd_product == 'ibi':
            kdd_location = 'ibi Desktop App'
            kdd_executable = 'ibikdd'
        elif kdd_product == 'WD':
            # Need to implement in the future
            pass    
        result = self.XMLRPCclient('Remove-Item -Force "C:/Program Files/{}/{}"'.format(kdd_location, kdd_executable))
        result = self.XMLRPCclient(' try {{ Invoke-WebRequest -Uri "{}" -OutFile "C:/Program Files/{}/{}" }} catch {{ $_.Exception.Response.StatusCode }}'.format(kdd_url, kdd_location, kdd_executable))
        # check
        result = self.XMLRPCclient('Test-Path "C:/Program Files/{}/{}"'.format(kdd_location, kdd_executable))
        if 'True' in result: 
            self.log.info("Download {} completed".format(kdd_executable))
        else:
            self.log.error('Donwload failed, error message: "C:/Program Files/{}/{}" doesn\'t exist.'.format(kdd_location, kdd_executable))
            return False
        return True

    def start_kdd_process(self, kdd_product='ibi'):
        if kdd_product == 'ibi':
            kdd_location = 'ibi Desktop App'
            kdd_executable = 'ibikdd'
        elif kdd_product == 'WD':
            # Need to implement in the future
            pass
        self.log.info("Start {}.exe ...".format(kdd_executable))
        # Need to be executed in the background
        result = self.XMLRPCclient("Start-Process 'C:\Program Files\{}\{}.exe' -WindowStyle Hidden".format(kdd_location, kdd_executable)) 
        return True

    def check_kdd_version(self, kdd_product='ibi', kdd_version=''):
        return True




    def get_mount_path(self, device_id=None, **kwarg):
        # The hardcode below is a workaround for Windows.
        # This folder which is named after device_id will be used to recognize which kdd volume belongs to which ibi.
        folder_id = self.owner.commit_folder("{}_by_desktop_sync".format(device_id))
        time.sleep(5)  # Sometimes there is latency while committing folder is displayed in "net use"
        mount_path = None
        result = self.XMLRPCclient("net use")
        # KDDFS_list = []
        for row in result.split('\n'):
            if ":        \\" and "My Cloud" in row:
                mount_path_candidate = row.split(':')[0].strip()
                # The target volume must have a folder which is named afer device_id.
                temp = self.XMLRPCclient("DIR {}:".format(mount_path_candidate))
                if device_id in temp:
                    mount_path = mount_path_candidate
                    break
        #self.owner.delete_file(folder_id)  # Delete the folder which is only for recognition.
        return mount_path

    def get_file_size(self, file_path=None, unit='M', **kwarg):
        # unit='M', MB
        # unit='G', GB
        # unit='K', KB
        total_file_size = None
        temp = self.XMLRPCclient("(Get-ChildItem -Recurse {} | Measure-Object -Sum Length).sum /1{}B".format(file_path, unit))
        total_file_size = float(temp)
        return total_file_size


    def file_transfer(self, source_path=None, dest_path=None, **kwarg):
        # start to transfer file
        upload_speed = 0
        upload_speed = self._robocopy(source_path, dest_path)  # By default the unit is MB
        return float(upload_speed)


    def _robocopy(self, source, destination):
        if source.startswith("~\\"):
            source = source.replace("~\\", "$HOME\\")
        if destination.startswith("~\\"):
            destination = destination.replace("~\\", "$HOME\\")
        retry = 3
        for x in xrange(retry):
            cmd = "robocopy {0} {1} /E /NP /NS /NC /NFL /NDL /W:1 /COPY:D /R:0".format(source, destination)
            result = self.XMLRPCclient(cmd)
            match = re.search('(\d+)\sBytes/sec', result)
            if match:
                speed = match.group(1)
                speed = float(speed) / float(1024*1024)  # Convert Bytes/sec to MB/sec.
                MB_per_second = '{}'.format(round(speed, 3))
                return MB_per_second
            else:
                if x == retry - 1:
                    print 'Error occurred while robocopy, there is no XXX Bytes/sec displayed after retrying {} times.'.format(retry)
                    #self.error_handle('Error occurred while robocopy, there is no XXX Bytes/sec displayed after retrying {} times.'.format(retry))
                else:
                    time.sleep(5)


    def read_write_perf(self):
        windows_drive_letter='C'
        windows_mount_point = 'Z'

        print "\n### Dekstop App performance test is being executed ... ###\n"
        self.delete_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
        self.delete_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))
        self.create_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
        self.create_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))
        # Copy the single file from Windows to NAS.
        SINGLE_WRITE_speed = self._robocopy('{}:\\5G_Single'.format(windows_drive_letter), '{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point))
        # Copy the single file from NAS to Windows.
        SINGLE_READ_speed = self._robocopy('{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point), '{}:\\WebDAVTestFolder_Windows'.format(windows_drive_letter))
        self.delete_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
        self.delete_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))
        self.create_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
        self.create_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))
        # Copy the standard files from Windows to NAS.
        STANDARD_WRITE_speed = self._robocopy('{}:\\5G_Standard'.format(windows_drive_letter), '{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point))
        # Copy the standard files from NAS to Windows.
        STANDARD_READ_speed = self._robocopy('{}:\\WebDAVTestFolder_NAS'.format(windows_mount_point), '{}:\\WebDAVTestFolder_Windows'.format(windows_drive_letter))
        self.delete_folder("{}:\\WebDAVTestFolder_NAS".format(windows_mount_point))
        self.delete_folder("{}:\\WebDAVTestFolder_Windows".format(windows_drive_letter))
        
        return SINGLE_WRITE_speed, SINGLE_READ_speed, STANDARD_WRITE_speed, STANDARD_READ_speed

    def install_app(self, app_version, env='dev1', app_folder='desktop_sync_pkg'):
        '''
        It is necessary to install "wget64.exe" on Windows client in advance.
        The download link:     https://eternallybored.org/misc/wget/
        '''
        app_name = 'KDA_Setup-{}-{}'.format(app_version, env)
        result = self.create_folder(app_folder)

        # Delete the old KDA_Setup.exe
        self.delete_file('./{}/KDA_Setup.exe'.format(app_folder))
        self.log.info("Downloading KaminodesktopAPP...")

        app_url = 'http://repo.wdc.com/content/repositories/desktop/kamino_desktop/'
        if app_version.startswith('1.1.0'):
            app_url += 'KaminoDesktop_Win_1.1.0/{0}/{1}.zip'.format(app_version, app_name)
        else:
            app_url += 'KaminoDesktop_Win/{0}/{1}.zip'.format(app_version, app_name)

        result = self.XMLRPCclient(' try {{ Invoke-WebRequest -Uri "{0}" -OutFile ./{1}/{2}.zip }} catch {{ $_.Exception.Response.StatusCode }}'.format(app_url, app_folder, app_name))
        # check
        result = self.XMLRPCclient('Test-Path ./{0}/{1}.zip'.format(app_folder, app_name))
        if 'True' in result: 
            self.log.info("Download complete")
        else:
            self.log.error("Donwload failed, error message: ./{0}/{1}.zip doesn\'t exist.".format(app_folder, app_name))

        self.log.info("Unzip KaminodesktopAPP...")
        print '\n Unzip and install {} \n'.format(app_name)
        result = self.XMLRPCclient('Expand-Archive ./{0}/{1}.zip -DestinationPath ./{2} -Force'.format(app_folder, app_name, app_folder))  # Force: Overwrite the existing file.
        if result.strip():
            self.log.error("Unzip failed, error message: {}".format(result))

        self.log.info("Installing KaminodesktopAPP...")
        result = self.XMLRPCclient('./{}/KDA_Setup.exe /install /passive'.format(app_folder))
        if result.strip():
            self.log.error("Install failed, error message: {}".format(result))
            return False
        else:
            self.log.info("Installing WD Sync complete")
            return True

    def uninstall_app(self, app_folder='desktop_sync_pkg'):
        self.log.info("Uninstall KaminodesktopAPP...")
        result = self.XMLRPCclient('./{}/KDA_Setup.exe /uninstall /passive'.format(app_folder))
        result = self.XMLRPCclient("ls 'C:\\Program Files'")
        if 'WD Desktop App' in result:
            self.log.error("fail ro uninstall KaminodesktopAPP, error message: {}".format(result))
            return False
        else:
            # There is a need to reboot Windows after uninstall KDA_Setup.exe, otherwise, KDA_Setup.exe cannot be installed again.
            result = self.XMLRPCclient("Restart-Computer")
            temp = time.time()
            while True:
                time.sleep(30)
                result = self.XMLRPCclient('ipconfig')  # Just check if the XMLRPCserver is running.
                if "Connection refused" in result:
                    print '\nWait for Windows rebooting\n'
                else:
                    break
                if (time.time() - temp) > 300:
                    self.log.error("Windows cannot be rebooted or XMLRPCserver is failed to launch.")
                    break
            self.log.info("Windows rebooting finished")
            return True

    def start_kdd_wdsync_process(self):
        self.log.info("Start kdd.exe ...")
        result = self.XMLRPCclient("Start-Process 'C:\Program Files\WD Desktop App\kdd.exe' -WindowStyle Hidden")  # Need to be executed in the background

    def check_kdd_wdsync_process(self):
        kdd_process = False
        wdsync_process = False
        
        result = self.XMLRPCclient('Get-Process kdd')
        if 'Cannot find a process with the name "kdd"' in result:
            self.log.warning('kdd process is not running!')
        else:
            kdd_process = True
        
        result = self.XMLRPCclient('Get-Process wdsync')
        if 'Cannot find a process with the name "wdsync"' in result:
            self.log.warning('wdsync process is not running!')
        else:
            wdsync_process = True

        time.sleep(3)  # Wait for kdd executed
        return kdd_process, wdsync_process

    def stop_kdd_wdsync_process(self):
        self.log.info("Trying to kill wddesktop process")
        result = self.XMLRPCclient('Stop-Process -processname kdd')
        if result:
            self.log.error("Unable to kill kdd process, error msg:{}".format(result))
        result = self.XMLRPCclient('Get-Process kdd')
        if 'Cannot find a process with the name "kdd"' not in result:
            self.log.error("Unable to kill kdd process, error msg:{}".format(result))
        result = self.XMLRPCclient('Get-Process wdsync')
        if 'Cannot find a process with the name "wdsync"' not in result:
            self.log.error("Unable to kill wdsync process, error msg:{}".format(result))

    def get_sync_http_port(self):
        result = self.XMLRPCclient('cat C:\\Users\\automation\\AppData\\Roaming\\WDDesktop\\Data\\Sync\\httpPort.json')
        try:
            self.sync_http_port = json.loads(result).get('HTTPPort')
            return self.sync_http_port
        except Exception as e:
            self.log.error("Failed to get sync http port, error message: {}".format(e))
            return None

    def get_kdd_http_port(self):
        result = self.XMLRPCclient('cat C:\\Users\\automation\\AppData\\Roaming\\WDDesktop\\Data\\httpPort.json')
        try:
            self.kdd_http_port = json.loads(result).get('HTTPPort')
            return self.kdd_http_port
        except Exception as e:
            self.log.error("Failed to get kdd http port, error message: {}".format(e))
            return None

    def kdd_login(self, id_token, refresh_token):
        self.log.info("Log in to kdd...")
        result = self.XMLRPCclient("Invoke-RestMethod -Method Post -Uri 'http://localhost:{0}/kdd/v1/user/login?accessToken={1}&refreshToken={2}'".format(self.kdd_http_port, id_token,refresh_token))
        if result.strip():
            self.log.error("KDD login failed, error msg: {}".format(result))
            return False
        else:
            self.log.info("KDD login successfully")
            return True

    def kdd_log_status(self):
        result = self.XMLRPCclient("Invoke-RestMethod -Method Get -Uri http://localhost:{}/kdd/v1/user/status".format(self.kdd_http_port))
        if result.strip():
            self.log.info("User is not logged in KDD")
            return False
        else:
            # If user is not logged in, the response will be NotFound(404).
            self.log.info("User already logged in KDD")
            return True

    def kdd_logout(self):
        result = self.XMLRPCclient("Invoke-RestMethod -Method Post -Uri http://localhost:{}/kdd/v1/user/logout".format(self.kdd_http_port))
        # In fact, whether the user is logged in or not, the response is always '' by Windows KDA.
        if not self.kdd_log_status():
            self.log.info("User logged out successfully")
            return True
        else:
            self.log.error("User logged out failed")
            return False

    def create_sync(self, src_path, dst_path):
        # def create_sync(self, src_path='C:\\\\winfolder', dst_path='Z:\\\\testfolder'):  For example of format
        print '\n Create sync\n'
        # Invoke-RestMethod -Method Post -Uri 'http://localhost:49989/sync/v1/folders' -Body '{"SrcPath":"C:\\5G_Single","DstPath":"Z:\\testfolder"}' 
        # If creating sync successfully, the response is '\n'.
        body = '{{"SrcPath":"{0}","DstPath":"{1}"}}'.format(src_path.replace("\\", "\\\\"), dst_path.replace("\\", "\\\\"))
        result = self.XMLRPCclient('Invoke-RestMethod -Method Post -Uri \'http://localhost:{0}/sync/v1/folders\' -Body \'{1}\''.format(self.sync_http_port, body))
        if result.strip():
            self.log.error("Create sync failed")
            return False
        else:
            self.log.info("Create sync successfully")
            return True

    def delete_sync(self, src_path):
        # delete_sync(self, src_path="C:\\winfolder"):  For example of format
        print '\n Delete sync\n'
        result = self.XMLRPCclient('Invoke-RestMethod -Method Delete -Uri \'http://localhost:{0}/sync/v1/folders?path={1}\''.format(self.sync_http_port, src_path))
        if result.strip():
            self.log.error("Failed to delete sync info, error message: {}".format(result))
            return False
        else:
            self.log.info("Delete sync info successfully")
            return True

    def get_sync(self):
        print '\n Get the list of Desktop Sync file(s)\n'
        result = self.XMLRPCclient("Invoke-RestMethod -Method Get -Uri http://localhost:{}/sync/v1/folders".format(self.sync_http_port))  # Log out from MyCloud
        if result.strip():
            self.log.info("Get sync info successfully")
            return result
        else:
            self.log.warning("There is no sync setup before")
            return None

    def check_sync_status(self):
        # Not implement yet
        # status, response = self.ssh.execute('')
        # print status, response
        pass

    def get_nas_mount_path(self, owner_first_name, nas_folder_name):
        nas_mount_path = 'Z:\\{}'.format(nas_folder_name)  # Because the nas drive mounted on Windows is Z:\
        return nas_mount_path

    def check_local_folder_exist(self, folder_path):
        result = self.XMLRPCclient("Test-Path {}".format(folder_path))
        if 'True' in result:
            return True
        else:
            return False

    def get_local_checksum_dict(self, folder_path):
        # <folder_path> is absolute file path, for example: "C:\*" or "C:\picture.jpg"
        cmd = "Get-FileHash {}\* -Algorithm MD5 | Format-List".format(folder_path)
        result = self.XMLRPCclient(cmd)
        if result:
            checksum_dict = {}
            for element in result.split('\n\n'):
                if element:
                    checksum_dict.update({element.split('Path      : ')[1].split('\\')[-1]: \
                        element.split('Hash      : ')[1].split('\nPath')[0].lower()})
            return checksum_dict
        else:
            self.log.error("Error occurred while calculating MD5 of '{}'".format(folder_path))

    def download_files_from_file_server(self, server_ip, folder_path, download_to):
        download_from = '{0}{1}'.format('ftp://ftp:ftppw@{}'.format(server_ip), folder_path)
        cut_dir = folder_path.count('/')
        url = './wget64.exe  -q -t 10 --no-host-directories --cut-dirs={0} -r --no-passive {1} -P {2}'.format(cut_dir, download_from, download_to)
        result = self.XMLRPCclient(url)
        # Check
        cmd = "DIR {}".format(download_to)
        result = self.XMLRPCclient(cmd)
        if result:
            return True
        else:
            return False

    def create_folder(self, folder_path):
        cmd = "New-Item -type directory {}".format(folder_path)
        result = self.XMLRPCclient(cmd)

    def delete_folder(self, folder_path):
        cmd = "Remove-Item -Recurse -Force {}".format(folder_path) 
        result = self.XMLRPCclient(cmd)

    def delete_file(self, file_path):
        cmd = "Remove-Item -Recurse -Force {}".format(file_path) 
        result = self.XMLRPCclient(cmd)



if __name__ == '__main__':
    import time
    from platform_libraries.restAPI import RestAPI
    owner = RestAPI('10.92.224.36', 'dev1', 'wdctest_desktop_sync_owner+qawdc@test.com', 'Test1234')
    ds = DESKTOP_SYNC(client_os='MAC', client_ip='10.92.224.61', client_username='test', client_password='`1q', rest_obj=owner)
    ds.connect()
    ds.install_app('1.1.0.14', 'dev1')
    ds.start_kdd_wdsync_process()
    time.sleep(5)
    ds.check_kdd_wdsync_process()
    ds.get_sync_http_port()
    ds.get_kdd_http_port()
    ds.kdd_login(owner.id_token, owner.refresh_token)
    time.sleep(5)
    ds.kdd_log_status()
    src = "/Users/test/desktop_sync_local_folder/"
    device_id = owner.get_device_id()
    dst = "/Users/test/Library/Containers/com.wdc.WDDesktop.WDDesktopFinderSync/Data/volumes/{}/Ben's My Cloud Home/desktop_sync_nas_folder".format(device_id)
    result = ds.create_sync(src, dst)
    print result
    time.sleep(5)
    result = ds.get_sync()
    print result
    ds.delete_sync(src)
    ds.kdd_logout()
    ds.stop_kdd_wdsync_process()
    ds.disconnect()
