___author___ = 'Vance Lo <vance.lo@wdc.com>', 'Ben Tsui <ben.tsui@wdc.com>'

# std modules
import collections
import colorlog
import errno
import json
import logging
import logstash
import os
import requests
import subprocess
from inspect import stack
from uuid import uuid4
# core modules
import middleware.step_logging as sl # init custom logging
from pyutils import NotSet
# platform modules
from jenkins_scripts.upload_ftp import FTP_connect, FTP_upload
import shlex # to split shell commands
import subprocess32 # subprocess module ported from python 3.2 with support for timeout exceptions
from subprocess32 import Popen, PIPE

# A collection of methods used in the ADB and Monsoon libraries for platform testing
# These can also be used in test scripts to make them more readable and cleaner in general

def unicode_to_str(data):
    """ Convert unicode data to str data. """
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(unicode_to_str, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(unicode_to_str, data))
    else:
        return data

def makeOutputDirectory(outputDir=None):
    """ Create directory and and subfolders """
    if outputDir:
        try:
            os.makedirs(outputDir)
        except OSError as exception:
            if exception.errno != errno.EEXIST:
                raise

def outputTextfile(textToWrite=None, filepath=None, append=False):
    if append:
        editMode = 'a'
    else:
        editMode = 'w'
    if textToWrite and filepath:
        with open(filepath, editMode) as text_file:
            text_file.write(textToWrite)

def setupLogstashLogger(loggerName='logstash', level=logging.INFO, host='10.104.130.130', port=5000, tags=None):
    l = logging.getLogger(loggerName)
    l.setLevel(logging.INFO)
    l.addHandler(logstash.TCPLogstashHandler(host=host, port=port, tags=tags, version=1))


#
# Logger Area
#

# Global value
ROOT_LOG = 'KAT'
OUTPUT_DIR = None
OVERWRITE = False
LOG_NAME_LENGTH = 30
STREAM_LOG_LEVEL = None
# Keep handlers (gen from @logger class) to update at once.
STREAM_HANDLERS = []


def logger(root_log=ROOT_LOG, log_name=None, output_dir=OUTPUT_DIR, overwrite=OVERWRITE, log_name_length=LOG_NAME_LENGTH,
        stream_log_level=None, log_attr='log', level_sync=True):
    # logger generate at loading code.
    def logger_decorator(cls):
        if log_attr in cls.__class__.__dict__.keys(): return cls # generate only one logger instance for each class.

        # Add method to change logger.
        def init_logger(self, *args, **kwargs):
            if 'log_name' not in kwargs or not kwargs['log_name']:
                kwargs['log_name'] = self.__class__.__name__
            setattr(self, log_attr, create_logger(*args, **kwargs))
            return self
        setattr(cls, 'init_logger', init_logger)

        # Generate logger for class and set it to log_attr.
        log = create_logger(root_log=ROOT_LOG, log_name=log_name if log_name else cls.__name__, output_dir=OUTPUT_DIR,
                    overwrite=OVERWRITE, log_name_length=LOG_NAME_LENGTH, stream_log_level=stream_log_level, level_sync=level_sync)
        setattr(cls, log_attr, log)
        return cls
    return logger_decorator


def create_logger(root_log=ROOT_LOG, log_name=None, output_dir=OUTPUT_DIR, overwrite=OVERWRITE, log_name_length=LOG_NAME_LENGTH,
        stream_log_level=NotSet, level_sync=False):
    """
        Configure the logging system. The log full name will be 'root_log.log_name', ex. KAT.restAPI

        :param log_name: The name of the logger. Default is the script name.
        :param output_dir: The place to save log file
        :param overwrite: Choose to overwrite or append the logs to existed log file
        :param root_log: The prefix of the log_name, default is KAT.
        :param log_name_length: log_name < log_name_length will be filled with spaces for alignment
        :param stream_log_level: Log level to print on screen.
        :param level_sync: To sync stream_log_level to environment or not. For @logger case.
        :return: The logger object
    """
    # Find current script name if log_name is not specified
    if stream_log_level is NotSet:
        stream_log_level = STREAM_LOG_LEVEL
    if not log_name:
        caller_frame = stack()[1]
        calling_script = caller_frame[0].f_globals.get('__file__', None)
        calling_script = os.path.basename(calling_script)
        if '.' in calling_script:
            calling_script = calling_script.split('.')[0]
        log_name = '{0}.{1}'.format(root_log, calling_script)
    elif not log_name.startswith('{}.'.format(root_log)):
        log_name = '{0}.{1}'.format(root_log, log_name)

    # Create output folder if it's not exist
    if not output_dir:
        output_dir = 'output' # Put log file into ./output/
    if not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
        except Exception as e:
            print "Warning: cannot create output folder:{0}, error message:{1}".format(output_dir, repr(e))

    # Every logger has to be started with root_log name
    if not log_name.startswith('{}.'.format(root_log)):
        log_name = '{}.{}'.format(root_log, log_name)

    log_name = log_name.ljust(log_name_length)
    root_logger = _create_root_logger(root_log, output_dir, overwrite)
    logger = logging.getLogger(log_name)
    if logger.handlers:
        return logger
    # Set for child logging.
    logger.propagate = False # Not pass record to root.
    logger.addHandler(root_logger.handlers[0]) # Share root's file handler.
    if not isinstance(stream_log_level, int):
        stream_log_level = logging.INFO
    stream_handler = gen_stream_handler(level=stream_log_level) # Generate own stream handler.
    logger.addHandler(stream_handler)
    if level_sync: # Record for @logger case
        STREAM_HANDLERS.append(stream_handler)
    return logger


def _create_root_logger(root_log=ROOT_LOG, output_dir=OUTPUT_DIR, overwrite=OVERWRITE):
    """
        Configure the root logging format.
        Every log starts with the same root log name will use the same format and save to the same file.

        :param root_log: The root log_name. Default is 'KAT'
        :param output_dir: The place to save log file
        :param overwrite: Choose to overwrite or append the logs to existed log file
        :return: The logger object
    """
    if '.' in root_log:
        root_log = root_log.split('.')[0]

    root_logger = logging.getLogger(root_log)
    if root_logger.handlers:
        # Already created, so return
        return root_logger

    root_logger.setLevel(logging.DEBUG)

    # Create file handler
    file_name = '{}_log.txt'.format(root_log)
    log_file = os.path.join(output_dir, file_name)
    if overwrite:
        mode = 'w'
    else:
        mode = 'a'

    file_handler = logging.FileHandler(filename=log_file, mode=mode)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)-19s %(name)-12s: %(levelname)-8s %(message)s', '%Y-%m-%d %H:%M:%S')
    file_handler.setFormatter(file_formatter)

    # Create stream handler
    stream_handler = gen_stream_handler(level=logging.DEBUG)

    # Add handlers to root logger
    root_logger.addHandler(file_handler) # Always put it at first one.
    root_logger.addHandler(stream_handler)
    return root_logger


def gen_stream_handler(level=logging.INFO):
    stream_handler = colorlog.StreamHandler()
    stream_handler.setLevel(level)
    log_colors = colorlog.default_log_colors.copy()
    log_colors[sl.DISPLAY_NAME] = 'cyan' # add color for Test Step.
    stream_formatter = colorlog.ColoredFormatter('%(name)-12s: %(log_color)s%(levelname)-8s %(message)s', log_colors=log_colors)
    stream_handler.setFormatter(stream_formatter)
    return stream_handler


def update_stream_handlers(level=None):
    if not level:
        level = STREAM_LOG_LEVEL
    for stream_handler in STREAM_HANDLERS:
        stream_handler.setLevel(level)


def upload_kdp_fw_to_server(model=None, fw=None, env=None, ver=None, data_type='os',ftp_username='ftp', ftp_password='ftppw', ftp_file_path='fileserver.hgst.com/firmware', retry=3):

    if not ftp_file_path.endswith('/'):
        ftp_file_path += '/'

    download_path = 'http://repo.wdc.com/content/repositories/projects/kdp/kdp-firmware'

    if data_type == 'ota':
        fw_name = 'kdp-firmware-{0}-ota-installer-{1}-{2}.zip'.format(fw, model, env)
    elif data_type == 'os':
        fw_name = 'kdp-firmware-{0}-os-{1}-{2}.zip'.format(fw, model, env)
    elif data_type == 'ota-installer':
        fw_name = 'kdp-firmware-{0}-ota-installer-{1}-{2}.zip'.format(fw, model, env)
    elif data_type == 'install-tool':
        if ver:
            fw_name = 'kdp-firmware-{0}-install-tool-{1}-{2}-{3}.zip'.format(fw, model, env, ver)
        else:
            fw_name = 'kdp-firmware-{0}-install-tool-{1}-{2}.zip'.format(fw, model, env)

    for i in xrange(retry):
        try:
            try:
                subprocess.check_output('rm {}'.format(fw_name), shell=True)
            except subprocess.CalledProcessError:
                pass
            try:
                subprocess.check_output('rm {}.md5'.format(fw_name), shell=True)
            except subprocess.CalledProcessError:
                pass
            print '~~~ Before download firmware, check the firmware is exist on the file server or not ~~~'
            url = 'http://{}{}'.format(ftp_file_path, fw_name)
            response = requests.head(url)
            if response.status_code == 200:
                print 'content-length:{}, Last-Modified:{}'.format(response.headers['content-length'], response.headers['Last-Modified'])
                msg = 'Firmware:{} is exist, skip to upload firmware to server step !!!'.format(fw_name)
                print msg
                return True, msg
            print '~~~ try to download firmware [{}], iteration: {} ~~~'.format(fw_name, i+1)
            print 'Firmware[{}] is being downloaded to local ...'.format(fw_name)
            subprocess.check_output('wget -nv -t 10 -c {0}/{1}/{2}'.format(download_path, fw, fw_name), shell=True)
            subprocess.check_output('wget -nv -t 10 -c {0}/{1}/{2}.md5'.format(download_path, fw, fw_name), shell=True)
            md5sum_real = subprocess.check_output('cat {}.md5'.format(fw_name), shell=True)
            md5sum_local = subprocess.check_output('md5sum {}'.format(fw_name), shell=True).split()[0]
            if md5sum_real != md5sum_local:
                raise Exception('The md5sum of file is different between in repo and in local.')

            print 'Firmware[{}] is being uploaded to ftp server ...'.format(fw_name)
            print '\n\ncurl -u {0}:{1} -T {2} ftp://{3}\n\n'.format(ftp_username, ftp_password, fw_name, ftp_file_path)
            subprocess.check_output('curl -u {0}:{1} -T {2} ftp://{3}'.format(ftp_username, ftp_password, fw_name, ftp_file_path), shell=True)
            md5sum_ftpserver = subprocess.check_output('curl -s http://{0}{1} |md5sum'.format(ftp_file_path, fw_name), shell=True).split()[0]
            if md5sum_real != md5sum_ftpserver:
                raise Exception('The md5sum of file is different between in local and in ftp server({}).'.format(ftp_file_path))

            msg = 'Firmware is uploaded to ftp server successfully after md5sum checking.'
            return True, msg
        except Exception as e:
            print e
            print '~~~ failed to download firmware [{}], iteration: {} ~~~'.format(fw_name, i+1)
            if i+1 == retry:
                return False, str(e)+' after retrying {} times.'.format(retry)


def upload_fw_to_server(model=None, fw=None, env=None, variant=None, data_type='ota',ftp_username='ftp', ftp_password='ftppw', ftp_file_path='fileserver.hgst.com/firmware', retry=3):

    if not ftp_file_path.endswith('/'):
        ftp_file_path += '/'

    if env == 'dev':
        download_path = 'http://repo.wdc.com/content/repositories/projects/MyCloudOS-Dev'
    else:
        download_path = 'http://repo.wdc.com/content/repositories/projects/MyCloudOS'

    if env == 'qa1':
        MCAndroid_name = 'MCAndroid-QA'
    elif env == 'prod':
        MCAndroid_name = 'MCAndroid-prod'
    elif env == 'dev1':
        MCAndroid_name = 'MCAndroid'
    elif env =='integration':
        MCAndroid_name = 'MCAndroid-integration'

    if variant == 'user':
        tag = '-user'
    elif variant == 'engr':
        tag = '-engr'
    else:
        tag = ''

    if data_type == 'ota':
        fw_name = '{0}-{1}-ota-installer-{2}{3}.zip'.format(MCAndroid_name, fw, model, tag)
    elif data_type == 'os':
        fw_name = '{0}-{1}-os-{2}{3}.zip'.format(MCAndroid_name, fw, model, tag)
    elif data_type == 'uboot':
        stdout = subprocess.check_output('curl {}/{}/{}/ | grep uboot'.format(download_path, MCAndroid_name, fw), shell=True)
        for item in stdout.splitlines():
            if "uboot" in item and model in item and 'md5' not in item and 'sha1' not in item:
                fw_name = item.split('">')[1].split('</a></td>')[0]
                break

    for i in xrange(retry):
        try:
            try:
                subprocess.check_output('rm {}'.format(fw_name), shell=True)
            except subprocess.CalledProcessError:
                pass
            try:
                subprocess.check_output('rm {}.md5'.format(fw_name), shell=True)
            except subprocess.CalledProcessError:
                pass
            print '~~~ Before download firmware, check the firmware is exist on the file server or not ~~~'
            url = 'http://{}{}'.format(ftp_file_path, fw_name)
            response = requests.head(url)
            if response.status_code == 200:
                print 'content-length:{}, Last-Modified:{}'.format(response.headers['content-length'], response.headers['Last-Modified'])
                msg = 'Firmware:{} is exist, skip to upload firmware to server step !!!'.format(fw_name)
                print msg
                return True, msg
            print '~~~ try to download firmware [{}], iteration: {} ~~~'.format(fw_name, i+1)
            print 'Firmware[{}] is being downloaded to local ...'.format(fw_name)
            subprocess.check_output('wget -nv -t 10 -c {0}/{1}/{2}/{3}'.format(download_path, MCAndroid_name, fw, fw_name), shell=True)
            subprocess.check_output('wget -nv -t 10 -c {0}/{1}/{2}/{3}.md5'.format(download_path, MCAndroid_name, fw, fw_name), shell=True)
            md5sum_real = subprocess.check_output('cat {}.md5'.format(fw_name), shell=True)
            md5sum_local = subprocess.check_output('md5sum {}'.format(fw_name), shell=True).split()[0]
            if md5sum_real != md5sum_local:
                raise Exception('The md5sum of file is different between in repo and in local.')

            print 'Firmware[{}] is being uploaded to ftp server ...'.format(fw_name)
            print '\n\ncurl -u {0}:{1} -T {2} ftp://{3}\n\n'.format(ftp_username, ftp_password, fw_name, ftp_file_path)
            subprocess.check_output('curl -u {0}:{1} -T {2} ftp://{3}'.format(ftp_username, ftp_password, fw_name, ftp_file_path), shell=True)
            md5sum_ftpserver = subprocess.check_output('curl -s http://{0}{1} |md5sum'.format(ftp_file_path, fw_name), shell=True).split()[0]
            if md5sum_real != md5sum_ftpserver:
                raise Exception('The md5sum of file is different between in local and in ftp server({}).'.format(ftp_file_path))

            msg = 'Firmware is uploaded to ftp server successfully after md5sum checking.'
            return True, msg
        except Exception as e:
            print e
            print '~~~ failed to download firmware [{}], iteration: {} ~~~'.format(fw_name, i+1)
            if i+1 == retry:
                return False, str(e)+' after retrying {} times.'.format(retry)


def gen_correlation_id(prefix_value='platform-autotests:', post_value=None):
    """ Generate an unique x-correlation-id header for logging on requesting APIs. """
    if not post_value:
        post_value = uuid4().hex
    # Example: "platform-autotests:6555abea9ace492db110720dc795a809"
    return {'x-correlation-id': '{}{}'.format(prefix_value, post_value)}


def upload_logs(output_path, target_path, server='fileserver.hgst.com', port='21', username='ftp', password='ftppw', remote_root='/logs'):
    """ Tool for uploading data to remote log folder. """
    ftp = None
    try:
        #ftp = FTP_connect(server=server, port=port, username=username, password=password, debug=False)
        #if FTP_upload(ftp=ftp, source=output_path, target='{}/{}'.format(remote_root, target_path), debug=False):
        subprocess.check_output('ncftpput -r 100 -t 900 -d ftp.log -mRzAv -u "{0}" -p "{1}" -P "{2}" "{3}" "{4}" "{5}"'.format(
            username, password, port, server, '{}/{}'.format(remote_root, target_path), output_path), shell=True)
        print 'Upload done.'
    except:
        print 'Upload failed.'
        if ftp:
            ftp.close()
        raise


def execute_local_cmd(cmd=None, consoleOutput=True, stdout=PIPE, stderr=PIPE, timeout=60, utf8=False):
    """
    Execute command and return stdout, stderr
    Handle timeout exception if limit exceeded and return None
    """
    log = create_logger(overwrite=False)
    if consoleOutput:
        log.info('Executing command: %s' %(cmd))
    cmd = shlex.split(cmd)
    output = subprocess32.Popen(cmd, stdout=stdout, stderr=stderr)
    try:
        if utf8:
            stdout = u''
            for line in output.stdout:
                stdout+=line.decode('utf-8')
            stderr = u''
            for line in output.stderr:
                stderr+=line.decode('utf-8')
            output.wait()
        else:
            stdout, stderr = output.communicate(timeout=timeout)
        if output.returncode != 0:
            log.error('\tstderr: ' + stderr.strip())
            raise RuntimeError('The return code should have been 0 but it is {}!'.format(output.returncode))
        if 'device offline' in stderr:
            log.error('\tstderr: ' + stderr.strip())
            raise RuntimeError('Device offline!')
    except subprocess32.TimeoutExpired as e:
        log.info('Timeout Exceeded: %i seconds' %(timeout))
        log.info('Killing command %s' %(cmd))
        output.kill()
        log.debug('Timeout exceeded: {0} seconds, killing command {1}'.format(timeout, cmd))
        raise e
    else:
        if consoleOutput:
            log.info('\tstdout: ' + stdout.strip())
            log.info('\tstderr: ' + stderr.strip())
        return stdout, stderr


def delete_local_file(file_path):
    if os.path.isfile(file_path):
        os.remove(file_path)
        print('File: {} has been deleted'.format(file_path))
    else:
        print('File: {} not exist'.format(file_path))

def check_port_pingable(ip, port):
    command = 'nc -zvn -w 1 {0} {1} > /dev/null 2>&1'.format(ip, port)
    response = os.system(command)
    if response == 0:
        return True
    return False


class ClientUtils(object):

    def __init__(self, log_inst=None):
        if log_inst:
            self.log = log_inst
        else:
            self.log = create_logger(overwrite=False)

    def create_random_file(self, file_name, local_path='', file_size='1048576'):
        # Default 1MB dummy file
        self.log.info('Creating local file: {}'.format(file_name))
        try:
            with open(os.path.join(local_path, file_name), 'wb') as f:
                f.write(os.urandom(int(file_size)))
        except Exception as e:
            self.log.error('Failed to create file: {0}, error message: {1}'.format(local_path, repr(e)))
            raise

    def delete_local_file(self, file_path):
        self.log.info("Deleting local file: {}".format(file_path))
        if os.path.isfile(file_path):
            os.remove(file_path)
            self.log.info('File: {} has been deleted'.format(file_path))
        else:
            self.log.warning('File: {} not exist'.format(file_path))

    def md5_checksum(self, file_path):
        process = subprocess.Popen('md5sum {}'.format(file_path), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, shell=True)
        stdout = process.communicate()[0]
        return stdout.split()[0]