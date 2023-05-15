__author__ = 'Nick Yang <nick.yang@wdc.com>'

from platform_libraries.adblib import ADB
from ToolAPI import Tool
import os
import logging
import time
import requests

class DL_UL(object):
    def __init__(self, uut_ip=None,port=None,server_ip=None,server_port=None,rest=None):
        self.uut_ip = uut_ip
        self.port = port
        self.server_ip = server_ip
        self.server_port = server_port
        self._rest = rest
        self.correct_userID = str(self._rest.get_user_id())
        self._tool = Tool(uut_ip=uut_ip, port=port,server_ip=server_ip,server_port=server_port,rest=self._rest)
        self.dl_throughput = []
        self.ul_throughput = []
        self.log = logging.getLogger('DL_UL')
        self.adb = ADB(uut_ip=self.uut_ip, port=str(self.port), adbServer=self.server_ip, adbServerPort=self.server_port)


    def upload(self, src=None, dest=None, userno=0, item_no=0):
        result = False
        default_path_on_nas = '/data/wd/diskVolume0/restsdk/userRoots'
        dest_path = dest.replace(default_path_on_nas, '')
        dest_path_list = dest_path.split('/')
        if dest_path_list[len(dest_path_list)-1]:
            raise Exception('destination must be a folder')

        dest_path_list.pop(0)
        userID = dest_path_list.pop(0)
        if self.correct_userID != userID:
            dest = dest.replace(userID, self.correct_userID)
            userID = self.correct_userID

        dest_path_list.pop(len(dest_path_list)-1)
        if dest_path_list:
            # means need to create sub folder under userID's folder
            current_path = '/'.join((default_path_on_nas, userID)) + '/'
            for path_list in dest_path_list:
                current_path += path_list
                current_path += '/'
                print 'create folder: %s' % current_path
                self._tool.check_create_data_on_nas(destFile=current_path, userno=userno, item_no=item_no)

        if not os.path.isdir(src):
            # start to upload file to dest
            filenames = src.split('/')[-1]
            destFile = dest + filenames

            start = time.time()
            self._tool.check_create_data_on_nas(srcFile=src, destFile=destFile, userno=userno, item_no=item_no)
            end = time.time()
            
            status, items_data, user_folder_id = self._tool.search_id(destFile)
            file_id = items_data[0]['id']

            if 'size' not in items_data[0].keys():
                message = "No key: 'size' in data list:{0} for upload {1} to NAS: {2}".format(items_data[0], filenames, destFile)
                raise Exception(message)
            
            elif int(items_data[0]['size']):
                file_size = int(items_data[0]['size'])

            elif file_id:
                file_size = self._tool.get_file_size(file_id)
                if file_size == 0:
                    message = 'Still no size after retry twice with file ID: {0} and fileInfo: {1}'.format(file_id, items_data[0])
                    raise Exception(message)

            else:
                message = "no size and id in 'size' & 'id' field: {0} for upload {1} to NAS: {2}".format(items_data[0], src, destFile)
                raise Exception(message)
                
            # Perform file comparison
            result, message = self._tool.compare_md5(local_filepath=src, dest_path=destFile,adb=self.adb)

            if result:
                self.log_info("File {0} is upload successfully onto NAS: {1}".format(filenames, destFile))
            else:
                self.log_error("File {0} fails to be upload onto NAS: {1} with {2}".format(filenames, destFile, message))
                
            # Calculate single file throughput
            duration = end - start
            throughput = round((file_size * 0.001)/(duration), 3)
            self.ul_throughput.append(throughput)

        else:
            # start to upload folder to dest
            self.log.info('Upload Folder')
            for path, dirs, filenames in os.walk(src):
                print 'path: %s' % path
                for directory in dirs:
                    destDir = path.replace(src, dest)

                    # Create sub-folder
                    self._tool.check_create_data_on_nas(destFile=os.path.join(destDir, directory)+'/', userno=userno, item_no=item_no)
                    self.log_info("sub-Folder {0} is created successfully onto NAS: {1}".format(destDir, self.correct_userID))

                for sfile in filenames:
                    srcFile = os.path.join(path, sfile)
                    destFile = os.path.join(path.replace(src, dest), sfile)

                    start = time.time()
                    self._tool.check_create_data_on_nas(srcFile=srcFile, destFile=destFile, userno=userno, item_no=item_no)
                    status, items_data, user_folder_id = self._tool.search_id(destFile)
                    end = time.time()
                    file_id = items_data[0]['id']
                    if 'size' not in items_data[0].keys():
                        message = "No key: 'size' in data list:{0} for upload {1} to NAS: {2}".format(items_data[0], sfile, destFile)
                        raise Exception(message)
            
                    elif items_data[0]['size']:
                        file_size = int(items_data[0]['size'])
                    elif file_id:
                        file_size = self._tool.get_file_size(file_id)  
                        if file_size == 0:
                            message = 'Still no size after retry twice with file ID: {0} and fileInfo: {1}'.format(file_id, items_data[0])
                            raise Exception(message)                  
                    else:
                        message = "no size and id in 'size' & 'id' field: {0} for upload {1} to NAS: {2}".format(items_data[0], sfile, destFile)
                        raise Exception(message)
                    
                    # Perform file comparison
                    result, message = self._tool.compare_md5(local_filepath=srcFile, dest_path=destFile,adb=self.adb)

                    if result:
                        self.log_info("Folder {0} is upload successfully onto NAS: {1}".format(sfile, destFile))
                    else:
                        self.log_error("Folder {0} fails to upload to NAS: {1} with {2}".format(sfile, destFile, message))
                        
                    # Calculate single file throughput
                    duration = end - start
                    throughput = round((file_size * 0.001)/(duration), 3)
                    self.ul_throughput.append(throughput)

        return result
                       
    def download_dir_files(self, download_dest=None, download_from=None):
        '''
        Download a single file or directory from NAS to local

        INPUT:
        download_dest (String) : Download destination on local environment
        download_from (String) : Download path on NAS storage
        '''

        file_exist, nas_info_dic, pa = self._tool.search_id(download_from)
        file_compare_result = False

        folder_or_file, name = self._tool.file_or_folder(download_from)

        # Create a folder on local if downloaded destination folder not exists
        if not os.path.exists(download_dest):
            createdir_command = 'mkdir -p {0}'.format(download_dest)
            os.system(createdir_command)

        # means path is directory (ex: /root/)
        if folder_or_file:                
                  
            # Create a folder on local if downloaded folder not exists
            dl_path = os.path.join(download_dest, name)
            if not os.path.exists(dl_path):
                createdir_command = 'mkdir -p {0}'.format(dl_path)
                os.system(createdir_command)
            
            # Download all the contents of each file/directory under the directory
            for j in range(len(nas_info_dic)):
                fileinfo = nas_info_dic[j]
                file_id = fileinfo['id']
                file_name = fileinfo['name']

                start = time.time()
                # Write the binary content into local file
                local_path = os.path.join(dl_path, file_name)

                if 'size' not in fileinfo.keys():
                    message = "No key: 'size' in data list:{0} for download {1} from NAS".format(fileinfo, download_from+file_name)
                    raise Exception(message)

                elif fileinfo['size']:
                    file_size = int(fileinfo['size'])
                elif file_id:
                    file_size = self._tool.get_file_size(file_id)
                    if file_size == 0:
                        message = 'Still no size after retry twice with file ID: {0} and fileInfo: {1}'.format(file_id, fileinfo)
                        raise Exception(message)                  
                else:
                    message = "no size and id in 'size' & 'id' field: {0} for download {1} from NAS".format(fileinfo, download_from+file_name)
                    raise Exception(message)
                
                file_content = self._tool.get_file_content(file_id)
                with open(local_path, 'w') as f:
                    f.write(file_content)
                end = time.time()
            
                # Do file comparison to compare local file and NAS file
                file_compare_result, message = self._tool.compare_md5(local_filepath=local_path, dest_path=download_from+file_name,adb=self.adb)
                if file_compare_result:
                    self.log_info("File {0} is downloaded successfully onto local".format(download_from+file_name))
                else:
                    self.log_error("File {0} fails to be downloaded with {1}".format(download_from+file_name, message))
                                
                # Calculate single file throughput

                duration = end - start
            
                # Change unit from Byte/s to kB/s
                throughput = round((file_size * 0.001)/(duration), 3)
                self.dl_throughput.append(throughput)

                '''
                # If current element is a non-empty folder (ex: /root/hello/), recursively call download_dir_files() again
                elif (file_mime == "application/x.wd.dir") and (file_num != 0):
                    sub_download_from = download_from + file_name + '/'
                    sub_download_dest = dl_path + '/'                
                    self.download_dir_files(sub_download_dest, sub_download_from, dnum)
                '''

        # means path is file (ex: /root/abc.txt)
        else:
            start = time.time()

            # Only 1 file in nas_id_dic, so get first element is OK
            fileinfo = nas_info_dic[0]
            file_id = fileinfo['id']
            file_name = fileinfo['name']
            
            # Get file size by file_id
            if 'size' not in fileinfo.keys():
                message = "No key: 'size' in data list:{0} for download {1} from NAS".format(fileinfo, download_from)
                raise Exception(message)
            
            elif fileinfo['size']:
                file_size = int(fileinfo['size'])
            elif file_id:
                file_size = self._tool.get_file_size(file_id)
                if file_size == 0:
                    message = 'Still no size after retry twice with file ID: {0} and fileInfo: {1}'.format(file_id, fileinfo)
                    raise Exception(message)
            else:
                message = "no size and id in 'size' & 'id' field: {0} for download {1} from NAS".format(fileinfo, download_from)
                raise Exception(message)

            file_content = self._tool.get_file_content(file_id)
            local_path = os.path.join(download_dest, file_name)

            # Write the binary content into local file
            with open(local_path, 'w') as f:
                f.write(file_content)
            end = time.time()
           
            # Do file comparison to compare local file and NAS file
            file_compare_result, message = self._tool.compare_md5(local_filepath=local_path, dest_path=download_from,adb=self.adb)
            if file_compare_result:
                self.log_info("File {0} is downloaded successfully onto local".format(download_from))
            else:
                self.log_error("File {0} fails to be downloaded with {1}".format(download_from, message))
                
            # Calculate single file throughput
            duration = end - start
            # Change unit from Byte/s to kB/s
            throughput = round((file_size * 0.001)/(duration), 3)
            self.log.info('Throughput  {0}'.format(throughput))
            self.dl_throughput.append(throughput)

        return file_compare_result

    def delete_dir_files_on_nas(self, src=None,dest=None):
        folder_or_file, name = self._tool.file_or_folder(src)

        if not folder_or_file:
            destFile = dest + name
            status, items_data, user_folder_id = self._tool.search_id(destFile)

            # Cannot delete a file/folder which is not on NAS
            if not status:
                print 'no %s existed' % destFile
                return
            try:
                url = 'http://{0}/sdk/v2/files/{1}'.format(self.uut_ip, items_data[0]['id'])
                access_token = str(self._rest.get_id_token())
                headers = {'Authorization': 'Bearer %s' % access_token}
                res = requests.delete(url, headers=headers)

                if res.status_code == 204:
                    print "%s is deleted" % destFile
                else:
                    raise Exception('Delete {0} error with: {1}'.format(destFile, res.content))
            except Exception as e:
                self.log.info('Exception: {0} when delete'.format(repr(e)))
        else:
            adb = ADB(uut_ip=self.uut_ip, port=str(self.port),adbServer=self.server_ip,adbServerPort=self.server_port)
            adb.connect()
            time.sleep(2)

            dest = dest.replace('auth0', 'auth0\\')
            print 'Removing contents in %s' % dest
            adb.executeShellCommand('rm -rf {0}'.format(dest), consoleOutput=True)
            time.sleep(5)

            #adb.disconnect()
            #adb.killServer()

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
