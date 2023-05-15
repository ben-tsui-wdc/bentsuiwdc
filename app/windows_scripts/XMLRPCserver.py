from SimpleXMLRPCServer import SimpleXMLRPCServer
import socket
import subprocess


#hostIP = socket.gethostbyname(socket.gethostname())

IP_prefix = '192'

if_config = socket.gethostbyname_ex(socket.gethostname())
print 'interface configuration: {}'.format(if_config)

if IP_prefix:
    print 'The local network used: {}.X.X.X'.format(IP_prefix)
    for IP in if_config[2]:
        if IP.startswith(IP_prefix):  # Use the IP prefix which you wanted.
            hostIP = IP
            break
else:
    print 'There is no specified IP_prefix. Use the first interface as hostIP.'
    hostIP = if_config[2][0]


print '\nXMLRPCserver IP: {}'.format(hostIP)

def command(cmd):
    args = [r"powershell", '-ExecutionPolicy', 'Unrestricted', r"{}".format(cmd)]
    process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)  # Merge the stderr into stdout.
    #process = subprocess.Popen([r"{}".format(cmd)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)  # Merge the stderr into stdout
   
    stdout, stderr = process.communicate()
    print stdout
      
    process.kill()  # Close the spawned child process.
    
    result = unicode(stdout, errors='ignore')
    return result

server = SimpleXMLRPCServer((hostIP, 12345), allow_none=True)
print "Listening on port 12345..."

server.register_function(command)
server.serve_forever()