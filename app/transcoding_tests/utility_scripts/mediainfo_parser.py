# -*- coding: utf-8 -*-
""" A tool to fetch multimediaa information of all the files in specified folder, and save data to a CSV/SQLite file.
"""
__author__ = "Estvan Huang <Estvan.Huang@wdc.com>"

# std modules
import csv
import os
import sqlite3
import subprocess
from argparse import ArgumentParser
from pprint import pprint


def scan_and_parse(scan_path, output_csv, path_skip_level):
    with open(output_csv, 'a') as csvfile: # Open CSV file
        writer = csv.DictWriter(csvfile, fieldnames=['filename', 'path', 'mediainfo'])
        writer.writeheader()

        # Scan all file
        for dir_path, dir_names, file_names in os.walk(scan_path):
            for file_name in file_names:
                # Init record
                record = {
                    'filename': file_name, 'path': None, 'mediainfo': None
                }
                try:
                    print '-'*30
                    record_path = path = os.path.join(dir_path, file_name)
                    if path_skip_level:
                        record_path = os.path.join(*path.split(os.sep)[path_skip_level+1:])
                    print 'Processing :{}'.format(path)
                    record['path'] = record_path

                    '''
                    # Parse it by mediainfo.
                    try:
                        raw_output = subprocess.check_output(['mediainfo', '--fullscan', path])
                    except subprocess.CalledProcessError:
                        print 'Parsing failed!'
                        continue
                    '''
                    # Parse it by ffprobe.
                    try:
                        raw_output = subprocess.check_output([
                            'ffprobe', '-v', 'quiet', '-print_format', 'json', '-show_format', '-show_streams' , path
                        ])
                    except subprocess.CalledProcessError:
                        print 'Parsing failed!'
                        continue
                    #print raw_output
                    record['mediainfo'] = raw_output
                finally: # Write data to CSV file
                    try: # Note that csv module cannot support unicode string.
                        writer.writerow(record)
                    except Exception, e:
                        print 'Write data failed: {}'.format(e)


def export_to_sqlite(input_csv, output_sqlite):
    with sqlite3.connect(output_sqlite) as con:
        con.text_factory = str
        cur = con.cursor()
        cur.execute("CREATE TABLE mediainfo (filename, path, mediainfo);")
        with open(input_csv, 'rb') as f:
            reader = csv.DictReader(f)
            for row in reader:
                to_db = (row['filename'], row['path'], row['mediainfo'])
                cur.execute("INSERT INTO mediainfo(filename, path, mediainfo) VALUES (?, ?, ?);", to_db)
        con.commit()


if __name__ == '__main__':
    parser = ArgumentParser(description='Scan all the files under specified folder and get mediainfo message')
    parser.add_argument('-path', '--scan_path', help='Folder path to scan')
    parser.add_argument('-skip', '--path_skip_level', help='Level number to skip recrod path', type=int, default=0)
    parser.add_argument('-csv', '--output_csv', help='CSV file path to save', default='output.csv')
    parser.add_argument('-sqlite', '--output_sqlite', help='SQLite file path to save', default='mediainfo_db')
    args = parser.parse_args()
    scan_and_parse(scan_path=args.scan_path, output_csv=args.output_csv, path_skip_level=args.path_skip_level)
    export_to_sqlite(input_csv=args.output_csv, output_sqlite=args.output_sqlite)
