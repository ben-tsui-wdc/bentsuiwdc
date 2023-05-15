#!/bin/bash
source /home/user/Workspace/py_env/pyserial/bin/activate
python /home/user/Workspace/source/platform_automation/infrastructure/serial_server/port_publisher.py --tcp-port 20000 -v --portfile /home/user/Workspace/etc/portfile --baudratefile /home/user/Workspace/etc/baudratefile --clean-registry-per 2592000