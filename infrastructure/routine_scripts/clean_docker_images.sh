#!/bin/bash
/usr/local/bin/docker images | grep none | awk '{print $'"${1:-3}}" | xargs /usr/local/bin/docker rmi -f