#!/bin/bash -xue

# This script is used to download git repo with retries,
# need to clone it into fileserver and use wget to download in jenkins workspace

retry=0
maxRetries=5
retryInterval=60
until [ ${retry} -ge ${maxRetries} ]
do
  `git clone ssh://git@jira-git.wdmv.wdc.com:7999/tau/platform_automation.git ${WORKSPACE}/platform_automation` && break
  retry=$[${retry}+1]
  echo -e "\nRetrying [${retry}/${maxRetries}] in ${retryInterval}(s)...\n"
  sleep ${retryInterval}
done

if [ ${retry} -ge ${maxRetries} ]; then
  echo "Failed after ${maxRetries} attempts!"
  exit 1
fi