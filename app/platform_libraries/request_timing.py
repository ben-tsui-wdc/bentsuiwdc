""" Here are the tools for timing any HTTP request.

The following timing tools are using pycurl module (which is an interface to libcurl), it should be nearly as using curl command. 

REF: https://curl.haxx.se/libcurl/c/curl_easy_getinfo.html
"""
__author__ = 'Estvan Huang <Estvan.Huang@wdc.com>'

# 3rd party modules
import pycurl
import cStringIO

def get_request(url, headers=None, write_io=None, follow_location=False):
    """ Send GET request with the specified url.

    [Arguments]
        url: String
           URL to request.
        headers: String list
            Request headers. ex: ['header_name1: header_value1', 'header_name2: header_value2']
        write_io: IO object
            Redirect download data stream to the specified I/O object. ex: open('/dev/null', 'w')
        follow_location: boolean
            To follow location URL or not.

    [Raises]
        pycurl.error:
            An error occurred during performing the reuqest.
    """
    try:
        hdr = cStringIO.StringIO()
        c = pycurl.Curl()
        c.setopt(pycurl.URL, url) # Set request URL.
        c.setopt(pycurl.FOLLOWLOCATION, follow_location)
        c.setopt(pycurl.HEADERFUNCTION, hdr.write)
        if headers: c.setopt(pycurl.HTTPHEADER, headers)
        if write_io: # Set I/O object to receive data stream.
            c.setopt(c.WRITEDATA, write_io)
        else: # Ignore reponse data.
            c.setopt(pycurl.WRITEFUNCTION, lambda x: None)
        c.perform() # Send request.

        # Read response headers
        status_line = hdr.getvalue().splitlines()
        location = None
        for line in status_line:
            if 'Location' in line:
                location = line
                break

        return {
            'status_code': c.getinfo(pycurl.RESPONSE_CODE),
            'dns_time': c.getinfo(pycurl.NAMELOOKUP_TIME), # DNS time
            'connect_time': c.getinfo(pycurl.CONNECT_TIME), # TCP/IP 3-way handshaking time
            'TTFB_time': c.getinfo(pycurl.STARTTRANSFER_TIME), # time-to-first-byte time
            'total_time': c.getinfo(pycurl.TOTAL_TIME),# Elapsed time
            'location': location
        }
    finally:
        c.close()
