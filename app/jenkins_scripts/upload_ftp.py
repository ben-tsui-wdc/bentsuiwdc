# -*- coding: utf-8 -*-
""" A simple tool to upload files to FTP server. """
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import argparse
import ftplib
import os
import sys
# platform modules
try:
    from platform_libraries.common_utils import create_logger
    log_inst = create_logger()
except:
    log_inst = None


#
# Remote Change Directory
#
def remote_chdir(ftp, path, debug=True):
    """ Change directory and create it if it does not exist.

    [Arguments]
        path: Relative path base on cruuent directory.
    """
    path = os.path.normpath(path) # for easy to handle path.
    path_split = [n for n in path.split('/') if n]
    recursive_chdir(ftp, path_split, debug=debug) 

def directory_exists(ftp, directory, debug=True):
    # Check if directory exists (in current location).
    filelist = []
    ftp.retrlines('LIST', filelist.append)
    for f in filelist:
        if f.split()[-1] == directory and f.upper().startswith('D'):
            return True
    return False

def recursive_chdir(ftp, descending_path_split, debug=True):
    if len(descending_path_split) == 0:
        return
    next_level_directory = descending_path_split.pop(0)
    if '.' == next_level_directory or '..' == next_level_directory:
        pass
    elif not directory_exists(ftp, next_level_directory, debug=debug):
        log('Create directory {}...'.format(next_level_directory), debug=True)
        ftp.mkd(next_level_directory)
    log('[Remote] Change directory to {}'.format(next_level_directory), debug=debug)
    ftp.cwd(next_level_directory)
    recursive_chdir(ftp, descending_path_split, debug=debug)

#
# Local Change Directory
#
def local_chdir(path, debug=True):
    # Change directory to specified path or change directory to specified file location.
    dir_path = path
    if os.path.isfile(path):
        dir_path, file = os.path.split(path)
    if not dir_path:
        return
    log('[Local] Change directory to {}'.format(dir_path), debug=debug)
    os.chdir(dir_path)

#
# Upload features
#
def FTP_upload(ftp, source, target, debug=True):
    """ Start to upload data from "source" to "target". 

    [Returns]
        True if upload success or False if upload failed.
    """
    if not os.path.exists(source):
        log('Path does not exists: {}'.format(source) , debug=debug)
        return False

    abs_source = os.path.abspath(source) # for easy to handle path.
    location, target_name = os.path.split(abs_source)
    # Keep local and remote host are the same folder level.
    local_chdir(abs_source, debug=debug)
    remote_chdir(ftp, target, debug=debug)
    if os.path.isfile(abs_source):
        target_file = target_name
        upload_file(ftp=ftp, filename=target_file, debug=debug)
    else:
        target_folder = target_name
        source_folder = abs_source
        # Create the first level folder.
        recursive_chdir(ftp=ftp, descending_path_split=[target_folder], debug=debug)
        upload_directory(ftp=ftp, path=source_folder, debug=debug)
    return True

def upload_file(ftp, filename, debug=True):
    # Upload single file (in current location).
    with open(filename, 'rb') as fp:
        log('Upload {}...'.format(filename))
        ftp.storbinary('STOR %s' % filename, fp)

def upload_directory(ftp, path, debug=True):
    items = os.listdir(path)
    for item in items:
        log('Prcoess {} ...'.format(item), debug=debug)
        if os.path.isfile(item):
            upload_file(ftp=ftp, filename=item, debug=debug)
        elif os.path.isdir(item):
            remote_chdir(ftp, item, debug=debug)
            local_chdir(item, debug=debug)
            upload_directory(ftp, '.', debug=debug)
    log('[Remote] Change directory back to parent directory...', debug=debug)
    ftp.cwd('..')
    log('[Local] Change directory back to parent directory...', debug=debug)
    os.chdir('..')

def FTP_connect(server, port=21, username='ftppw', password='ftppw', debug=True):
    """ Connect to FEP server and return a FTP object. 

    [Returns]
        FTP object.
    """
    target_FTP = ftplib.FTP(timeout=60)
    log('Connect to {0}:{1}...'.format(server, port))
    target_FTP.connect(server, port)
    log('Login with {0}...'.format(username, password))
    target_FTP.login(username, password)
    return target_FTP

#
# Logging
#
def log(message, debug=True):
    """ Logging message if debug set as True, or do nothing. 
    """
    if not message:
        return
    elif not debug:
        return

    if log_inst:
        log_inst.info(message)
    else: # Use print instead of logging module if it's used in standalone.
        print message


if __name__ == '__main__':
    # Handle input arguments. 
    parser = argparse.ArgumentParser(description='Upload files to FTP server.',
        formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument('-s', '--server', help='FTP server URL', metavar='fileserver.hgst.com')
    parser.add_argument('-p', '--port', help='FTP server port', metavar='PORT', type=int, default='21')
    parser.add_argument('-U', '--username', help='FTP user', metavar='USER', default='ftp')
    parser.add_argument('-P', '--password', help='FTP user password', metavar='PASSWORD', default='ftppw')
    parser.add_argument('-S', '--source', help='Local path to upload', metavar='PATH')
    parser.add_argument('-T', '--target', help='Remote path to save (Start from root)', metavar='PATH', default='/')
    parser.add_argument('-d', '--debug', help='Enable debug mode', action='store_true', default=False)
    args = parser.parse_args()

    server = args.server
    port = args.port
    username = args.username
    password = args.password
    source_path = args.source
    target_path = args.target
    debug = args.debug

    # Start upload
    target_FTP = FTP_connect(server=server, port=port, username=username, password=password, debug=debug)
    if FTP_upload(ftp=target_FTP, source=source_path, target=target_path, debug=debug):
        log('Upload done.')
        sys.exit(0)
    log('Upload failed.')
    sys.exit(1)
