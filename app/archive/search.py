import time
import os
from os.path import isdir, isfile, join, exists

def searchfile(paths, times, des):
    starttime = time.time()
    pathnum = ''
    if exists(paths):
        pathnum = 1
        for i in range(0, times):
            if isdir(paths):
                print '*INFO* Path is directory'
                for root, dirs, files in os.walk(paths):
                    dirs.sort()
                    files.sort()
                    for file in sorted(files):
                        path = join(root, file)
                        if '.' in path:
                            if isfile(path):
                                print '*INFO* Path: {0}'.format(path)
                                print 'Copy file from {0} ---> {1}/{2}.{3}'.format(path.rsplit('/', 1)[1],
                                                                                   des, pathnum, path.rsplit('.', 1)[1])
                                os.system('sudo cp "{0}" "{1}/{2}.{3}"'.format(path, des ,pathnum, path.rsplit('.', 1)[1]))
                                pathnum += 1
                        else:
                            if isfile(path):
                                print '*INFO* Path: {0}'.format(path)
                                print 'Copy file from {0} ---> {1}/{2}'.format(path.rsplit('/', 1)[1], des, pathnum)
                                os.system('sudo cp "{0}" "{1}/{2}"'.format(path, des, pathnum))
                                pathnum += 1

    print '*INFO*** Copy completed in {0} seconds'.format(int(time.time() - starttime))
    print '*INFO*** Total {} file(s)'.format(pathnum)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Test script to use ADB LIBRARY')
    parser.add_argument('-p', help='Local Folder Path')
    parser.add_argument('-c', help='Loop count')
    parser.add_argument('-d', help='Destination Path')
    args = parser.parse_args()

    paths = args.p
    des = args.d
    if args.c:
        times = int(args.c)
    else:
        times = 1
    searchfile(paths=paths, times=times, des=des)


