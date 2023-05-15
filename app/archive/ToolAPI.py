__author__ = 'Nick Yang <nick.yang@wdc.com>'

from platform_libraries.adblib import ADB
import logging
import os
import time
import requests
import commands

# Set default encoding from ascii to utf8, to prevent a transcoding error
import sys;
reload(sys);
sys.setdefaultencoding("utf8")

class Tool(object):
    def __init__(self, uut_ip=None,port=None,server_ip=None,server_port=None,rest=None):
        self.uut_ip = uut_ip
        self.port = port
        self.server_ip = server_ip
        self.server_port = server_port
        self._rest = rest
        self.log = logging.getLogger('Tool')

    def check_create_data_on_nas(self, srcFile=None, destFile=None ,userno=0, item_no=0):
        path_existed, items_data, user_folder_id = self.search_id(destFile)
        parentID = items_data[0]['parentID']
        if not path_existed:
            if parentID == user_folder_id:
                parentID = ''
            if srcFile is None:
                self.generate_upload_list(destFile, parentID, userno, item_no)
            else:
                self.generate_upload_list(srcFile, parentID, userno, item_no)
            status, result = self.upload_command(userno, item_no)
            if not status:
                raise Exception('check_create_data_on_nas: {0}'.format(result))

    def generate_upload_list(self, source_path='', parent_ID='', userno=0, item_no=0):
        if not parent_ID:
            parent_ID = 'root'
        folder, name = self.file_or_folder(source_path)
        fo = open('uploadFile_{0}_{1}'.format(userno, item_no), 'w')
        fo.write('--foo \n')
        fo.write('\n')
        command = '{"parentID":"%s",' % parent_ID
        # Just create a empty folder
        if folder:
            command += '"name":"%s",' % name
            command += '"mimeType":"application/x.wd.dir"}\n'
            fo.write(command)
        # Create file
        else:
            file_format = name.split('.')[1]
            command += '"name":"%s"' % name
            if file_format == 'jpg':
                command += ',"mimeType":"image/jpeg"}\n'
            elif file_format == 'mov' or file_format == 'MOV':
                command += ',"mimeType":"video/quicktime"}\n'
            elif file_format == 'mpg' or file_format == 'MPG':
                command += ',"mimeType":"video/mpeg"}\n'
            elif file_format == 'mp3':
                command += ',"mimeType":"audio/mpeg3"}\n'
            elif file_format == 'mp4':
                command += ',"mimeType":"video/mp4"}\n'
            # Assume it is plain text
            else:
                command += '}\n'
            fo.write(command)
            fo.write('\n')
            fo.write('--foo \n')
            fo.write('\n')

            fo.write(open(os.path.abspath(source_path), 'rb').read())
        fo.write('\n')
        fo.write('--foo--\n')
        fo.close()

    def upload_command(self, userno=0, item_no=0):
        access_token = str(self._rest.get_id_token())
        command = 'curl -v -X POST -H "Authorization: Bearer %s" ' % access_token + \
                  '-H "Content-Type: multipart/related;boundary=foo" ' + \
                  '--data-binary @uploadFile_{0}_{1} "http://{2}/sdk/v2/files"'.format(userno, item_no, self.uut_ip)
        status, result = commands.getstatusoutput(command)
        self.delete_upload_list(userno, item_no)
        created = False
        if 'HTTP/1.1 201 Created' in result or 'HTTP/1.1 409 Conflict' in result:
            created = True

        return created, result

    def delete_upload_list(self, userno=0, item_no=0):
        os.system('rm -rf {0}'.format(os.path.join(os.getcwd(), 'uploadFile_%s_%s'%(userno,item_no))))

    def search_files_command(self, ids='', pageToken=''):
        retry = 2
        url = 'http://%s/sdk/v2/filesSearch/parents?limit=1000' % self.uut_ip
        if ids:
            url += '&ids={0}'.format(ids)
        if pageToken:
            url += '&pageToken={0}'.format(pageToken)
        while retry >= 0:
            try:
                access_token = str(self._rest.get_id_token())
                headers = {'authorization': 'Bearer %s' % access_token}
                res = requests.get(url, headers=headers)
                result = res.json()
            except Exception as e:
                retry -= 1  
                if res.status_code != 200:
                    if retry == 0:
                        raise Exception('After retry twice with search parentsAPI: ids: %s, status_code : %s , response: %s, error in search_files_command from Tool.py' % (ids, res.status_code, res.content))
                else:
                    raise Exception("Response of search parentsAPI: %s , error in search_files_command from Tool.py'" % result)
            else:
                break

        return result

    def reformat_search_files_data(self, search_files_result):
        reformat_result_data = list()
        for files in search_files_result:
            for key, value in files.items():
                files[key] = str(value)
            reformat_result_data.append(files)

        return reformat_result_data

    def search_id(self, path):
        path_list = path.split('userRoots/')[1].split('/')
        data = [{'name': path_list[0], 'id': '', 'parentID': '', 'mimeType': 'application/x.wd.dir'}]
        folder_data = data
        user_folder_id = folder_data[0]['id']
        file_exist = True
        for i, names in enumerate(path_list):
            # start from root:
            result = self.get_all_files(ids=folder_data[0]['id'])
            if not len(result.get('files')):
                '''
                if not names:
                    print 'No files existed in %s ' % path_list[i-1]
                else:
                    print 'No files %s existed ' % names
                '''
                if file_exist and names:
                    folder_data = [{'name': names, 'id': '', 'parentID': folder_data[0].get('id'), 'mimeType': ''}]
                file_exist = False
                break
            elif i == 0:
                result = self.reformat_search_files_data(result.get('files'))
                folder_data[0]['id'] = result[0].get('parentID')
                user_folder_id = folder_data[0]['id']
                file_exist = True
            # search target file / folder name if existed , need pageToken
            else:
                result = self.reformat_search_files_data(result.get('files'))
                for files in result:
                    file_exist = False
                    if files.get('name') == names:
                        data = [files]
                        file_exist = True
                        folder_data = data
                        break
                    else:
                        continue
                if not file_exist:
                    # return target file / folder name and parentID
                    if not names:
                        file_exist = True
                        folder_data = result
                    else:
                        folder_data = [{'name': names, 'id': '', 'parentID': result[0].get('parentID'), 'mimeType': ''}]
                    break
        return file_exist, folder_data, user_folder_id

    def get_all_files(self, ids=None):
        files = {'files': []}
        pages = ['']
        for page in pages:
            data = self.search_files_command(ids,page)
            last_pageToken = data.get('pageToken')
            if last_pageToken not in pages:
                pages.append(last_pageToken)
                if 'files' in data.keys():
                    files['files'] += data.get('files')
            elif last_pageToken == '':
                if 'files' in data.keys():
                    files['files'] += data.get('files')
        return files

    def file_or_folder(self, path=''):
        '''
        Return parameter:
            folder (boolean) : True if the input parameter is a folder path
            name : the folder name or file name of the input path
        '''        
        path_list = path.split('/')
        folder = False
        if path_list[-1] == '':
            folder = True
            name = path_list[-2]
            return folder, name
        name = path_list[-1]
        return folder, name
    
    def get_type(self, path=''):
        path_list = path.split('/')

        if path_list[-1] == '':
            type = "Directory"
        else:
            file_type = path_list[-1].split('.')
            type = file_type[-1]
        return type        

    def get_file_content(self, file_id=None):
        '''
        Get file binary content of a single file
        '''
        # Get file content by file_id
        url = "http://{0}/sdk/v2/files/{1}/content".format(self.uut_ip, file_id)
        access_token = str(self._rest.get_id_token())
        headers = {'authorization': 'Bearer %s' % access_token}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            self.log_info("Get file content Okay")
        else:
            self.log_info("Get file content failed")

        return res.content

    def get_file_size(self, file_id=None):
        '''
        Get file size of a single file on NAS
        '''
        retry = 2
        filesize = 0

        url = "http://{0}/sdk/v2/files/{1}".format(self.uut_ip, file_id)
        while retry >= 0:
            try:
                access_token = str(self._rest.get_id_token())
                headers = {'authorization': 'Bearer %s' % access_token}
                res = requests.get(url, headers=headers)
                filesize = res.json()['size']
            except Exception as e:
                retry -= 1  
                if res.status_code != 200:
                    if retry == 0:
                        raise Exception('After retry twice with file ID: %s, status_code : %s , response: %s, error in get_file_size from Tool.py' % (file_id, res.status_code, res.content))
                else:
                    raise Exception("Response of get file size API: %s , error in get_file_size from Tool.py'" % res.json())
            else:
                break
            
        # Type: int
        return int(filesize)

    def upload_folder_file2NAS(self, src=None, dest=None, port=None, userid=None):

        # adb object to connect to device and execute commands
        adb = ADB(uut_ip=self.uut_ip, port=str(port),adbServer=self.server_ip, adbServerPort=self.server_port)

        # Connect to device via defined ip address:port
        #adb.connect()

        time.sleep(2)
        try:
            for loc, path in enumerate(dest):
                path = self.correct_userID_path(path, userid)
                sub_path = path.split('/data/wd/diskVolume0/restsdk/userRoots/{0}/'.format(userid))[1]

                sub_dir = sub_path.split('/')

                sub_dir.pop(-1)
                folder = '/data/wd/diskVolume0/restsdk/userRoots/{0}/'.format(userid)
                print "Push file onto the NAS: {0}".format(path)

                for dir in sub_dir:
                    folder += '%s/' % dir
                    adb.executeShellCommand('mkdir {0}'.format(folder))

                adb.push(local=src[loc],remote=folder)

        except Exception as ex:
            print "ADB push file fails, error message is %s" % ex.message
        '''
        finally:
            # Disconnect from device, and kill the running adb server on local environment
            adb.disconnect()
            adb.killServer()
        '''
        time.sleep(10)

    def correct_userID_path(self, path=None, correct_userID=None):
        sub_df = path.replace('/data/wd/diskVolume0/restsdk/userRoots/','')
        sub_dfList = sub_df.split('/')
        userID = sub_dfList[0]
        path = path.replace(userID, correct_userID)
        return path

    def compare_md5(self, local_filepath=None, dest_path=None,adb=None):
        '''

        Comparing the md5 checksum of the file on local device and NAS device, respectively
        :param local_filepath: Local environment file path
        :param dest_path: Destination file path on NAS
        :return: comparing result (True/False, message)
        '''
        try:
            dest_path = dest_path.replace('auth0','auth0\\')

            local_command = 'md5sum %s' % local_filepath
            nas_command = 'md5sum %s' % dest_path

            # Get local file checksum
            local_checksum = commands.getstatusoutput(local_command)[1].split(' ')[0]
            self.log_info('Local folder checksum is [{}]'.format(local_checksum))

            time.sleep(5)
            # Get NAS file checksum
            #adb.connect()
            #time.sleep(5)

            md5sum, stderr = adb.executeShellCommand(nas_command, consoleOutput=True)
            md5sum = md5sum.split(' ')[0]

            # Disconnect from device, and kill the running adb server on local environment
            #adb.disconnect()
            #adb.killServer()

            self.log_info('NAS folder checksum is [{}]'.format(md5sum))

            # Return the comparing result
            result = True
            message = "Hash check passed!"

            if local_checksum != md5sum:
                result = False
                message = 'Hash check failed!'

            return result, message

        except Exception as ex:
            print "Comparing md5 checksum FAIL, error message is %s" % ex.message

    def get_throughput(self,throughput_list=None,type=None):
        '''
        Return the min, avg, max throughput of each of the download and upload job
        '''
        min_value = 0
        max_value = 0
        average_value = 0

        if throughput_list:
            min_value = min(throughput_list)
            max_value = max(throughput_list)
            average_value = round(sum(throughput_list) / float(len(throughput_list)), 3)

            if type == 'download':
                self.log_info("Minimum download throughput is {0} kB/s".format(min_value))
                self.log_info("Maximum download throughput is {0} kB/s".format(max_value))
                self.log_info("Average download throughput is {0} kB/s".format(average_value))
            else:
                self.log_info("Minimum upload throughput is {0} kB/s".format(min_value))
                self.log_info("Maximum upload throughput is {0} kB/s".format(max_value))
                self.log_info("Average upload throughput is {0} kB/s".format(average_value))
        else:
            self.log_info("*** {0} : {1} There is no any job to calculate the throughput ***".format(type,self._rest.username))
        return type, min_value, max_value, average_value

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

if __name__ == '__main__':
    local = '/home/nick/Documents/platform_automation/app/test_output/test_12/5MB_1.jpg'
    nas = '/data/wd/diskVolume0/restsdk/userRoots/auth0|57fc1c9b7ded0b375d1c7e91/download/5MB_0.jpg'

    tool = Tool()
    result, message = tool.compare_md5(local_filepath=local,dest_path=nas)
    print message