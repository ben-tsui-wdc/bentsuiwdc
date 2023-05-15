# -*- coding: utf-8 -*-
import argparse
import json
import sys

# 3rd party modules
import requests

def test_result_exists(firmware='*', test_name=None, es_ip='10.92.234.101', es_port='9200', verbose=False, **query_pairs):
    # Prepare request 
    query_url = 'http://{0}:{1}/testresult-{2}/_search'.format(es_ip, es_port, firmware)
    headers = {'Content-Type': 'application/json'}
    data = {
        'query':{
            'match':{
            }
        }
    }
    # Handle query condition
    if test_name:
        data['query']['match']['testName'] = test_name
    data['query']['match'].update(query_pairs)

    # No condition given
    if not data['query']['match']:
        if verbose:
            print 'No condition given.'
        return False

    # Send request
    response = requests.post(url=query_url, data=json.dumps(data), headers=headers)
    json_resp = response.json()

    # Handle response
    if response.status_code == 200:
        total = json_resp.get('hits', {}).get('total', 0)
        if total:
            if verbose:
                print 'Test results found. Total: {}'.format(total)
            return True
        else:
            if verbose:
                print 'Test results not found.'
            return False
    else:
        if verbose and 'error' in json_resp:
            print json_resp['error']
        return False

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Find testing results')
    parser.add_argument('-fw', help='Firmware version, ex. 4.0.0-100', default='*')
    parser.add_argument('-test_name', help='Test case name', default=None)
    parser.add_argument('-es_ip', help='Destination elasticsearch server IP address', default='10.92.234.101')
    parser.add_argument('-es_port', help='Destination elasticsearch server port number', default='9200')
    parser.add_argument('-q', help='Other query conditions in json string, ex. \'{"testSuite": "Sharing_Stress_Tests"}\'')
    parser.add_argument('-v', help='Verbose mode', action="store_true")
    args = parser.parse_args()

    if test_result_exists(firmware=args.fw, test_name=args.test_name, es_ip=args.es_ip, es_port=args.es_port,
        verbose=args.v, **(json.loads(args.q) if args.q else {})):
        print "exists"
    else:
        print "non-exists"
    
