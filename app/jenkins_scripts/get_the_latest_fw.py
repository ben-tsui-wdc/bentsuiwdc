# -*- coding: utf-8 -*-
import argparse
import sys
import re
from bs4 import BeautifulSoup

# 3rd party modules
import requests


def get_the_latest_fw(cloud_environment, build_variant, product, kamino_version):
    ''' Replaced by getting bat_pass jenkins job, Ben Tsui, 2017.02.06
    # Prepare request 
    query_url = 'http://repo.wdc.com/service/local/repositories/projects/content/MyCloudOS/MCAndroid/'
    headers = {'accept': 'application/json,application/vnd.siesta-error-v1+json,application/vnd.siesta-validation-errors-v1+json'}

    # Send request
    response = requests.get(url=query_url, headers=headers)
    
    # Handle response
    if response.status_code == 200:
        json_resp = response.json()
        versions = [item['text'] for item in json_resp['data'] if item['text'].startswith('4.0.0-')]
        sorted_versions = sorted(versions)
        return sorted_versions.pop()
    else:
        return None
\    '''

    # cloud_environment => build_name
    build_name = {
        'qa1': 'MCAndroid-QA',
        'prod': 'MCAndroid-prod',
        'dev1': 'MCAndroid',
        #'integration': 'MCAndroid-integration'
    }.get(cloud_environment, 'MCAndroid')

    # build_variant => tag
    tag = {
        'engr': '-engr',
        'user': '-user'
    }.get(build_variant, '')

    # build_variant => query_url
    server_url = 'http://jenkins.wdc.com'

    build_version = {
        '1.2':'4_1_1',
        '1.3':'4_3_0',
        '1.4':'4_4_0',
        '1.5':'4_5_0',
        '2.0':'5_0_0',
        '2.1':'5_1_0',
    }.get(kamino_version)

    # Since Yoda and Yodaplus share the same firmware, which is named after -Yodaplus-.
    if 'yoda' in product:
        product = 'yodaplus'

    post_url = {
                'qa1': '/job/MyCloudAndroid-{0}-QA-{1}/bat_pass/'.format(build_version, product),
                'prod': '/job/MyCloudAndroid-{0}-prod-{1}/bat_pass/'.format(build_version, product),
                'dev1': '/job/MyCloudAndroid-{0}-dev-{1}/bat_pass/'.format(build_version, product),
        }

    fw_prefix = {
        'monarch': 'MCAndroid', 
        'pelican': 'MCAndroid', 
        'yodaplus': 'MCAndroid'
    }.get(product)

    query_url = server_url + post_url.get(cloud_environment)

    # Process first page
    latest_fw, url = request_and_find_fw(query_url, build_name, tag, product, fw_prefix)
    if latest_fw: # Found it.
        return latest_fw

    # Keep looking for the latest fw page by page.
    while url:
        url = server_url + url
        latest_fw, url = request_and_find_fw(url, build_name, tag, product, fw_prefix)
        if latest_fw:
            return latest_fw
    

def request_and_find_fw(query_url, build_name, tag, product, fw_prefix):

    # Send request
    #print 'Request:', query_url
    response = requests.get(query_url)

    # Handle response
    if response.status_code != 200:
        return None, None

    soup = BeautifulSoup(response.text, 'html.parser')

    # Get previous build page url
    rows = soup.findAll('a', text='Previous Build')
    if len(rows) != 1:
        #print 'Unexpected page format:', query_url
        return None, None
    previous_page_url = rows[0].attrs['href']

    # Get image names
    def is_image(x):
        if x:
            return x.startswith(fw_prefix) and x.endswith('.zip')
        else:
            return False

    rows = soup.findAll('a', text=is_image)

    # Find the latest fw from image file list.
    for r in rows:
        image_name = r.get_text()
        match = re.findall(r'\b\d+.\d+.\d+-\d+\b', image_name)
        if not match:
            # print 'Unexpected name format:', image_name
            continue
        image_firmware_version = match[0]
        # ['MCAndroid', 'usb-installer-monarch.zip']
        # ['MCAndroid', 'ota-installer-monarch-engr.zip']
        image_build_name, env_part = image_name.split('-'+image_firmware_version+'-')
        # "-engr" or "-user" or ""
        image_tag =  env_part.strip('.zip').split(product).pop()
        if image_build_name == fw_prefix and image_tag == tag:
            return image_firmware_version, previous_page_url

    return None, previous_page_url


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Get the latest version of MyCloudOS firmware from repo.wdc.com. Print firmware version or print nothing.')
    parser.add_argument('-env', '--cloud_environment', help='Target cloud environment', default='dev1', choices=['dev1', 'qa1', 'prod'])
    parser.add_argument('-variant', '--build_variant', help='Build variant', default='user')
    parser.add_argument('-product', '--product', help='Test product', default='monarch', choices=['monarch', 'pelican', 'yoda', 'yodaplus'])
    parser.add_argument('--kamino_version', help='kamino_version, such as 1.5 and 2.0', default='2.1', choices=['1.2', '1.3', '1.4', '1.5', '2.0', '2.1'])
    args = parser.parse_args()

    latest_version = get_the_latest_fw(args.cloud_environment, args.build_variant, args.product, args.kamino_version)
    if latest_version:
        print latest_version
        sys.exit(0)
    else:
        sys.exit(1)
