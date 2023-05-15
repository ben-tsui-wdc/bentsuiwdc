#!/bin/sh

# [Download uboot image to the usb plugged in UUT]
# Connect UUT by net console, and execute below commands:
#
# cd /tmp
# busybox wget ftp://ftp:ftppw@fileserver.hgst.com/firmware/download_uboot.sh -O download_uboot.sh
# sh download_uboot.sh {fw_ver} {optional:file_server_ip}


usb=`ls /mnt/media_rw`
if [ -z "$usb" ]; then
  echo "No USB drive detected! Stop upgrade firmware!"
  exit 1
else
  echo "# USB drive: $usb"
fi


if [ $# -lt 1 ]; then
  echo "Please input sh ./download_uboot.sh {fw_ver} {optional:file_server_ip}"
  exit 1
fi

file_server=${2:-"fileserver.hgst.com"}

echo "# File Server: $file_server"
echo "# Firmware: $1"

configURL=`cat /etc/restsdk-server.toml | grep config`
if echo "$configURL" | grep -q "dev"; then
   env=''
elif echo "$configURL" | grep -q "qa1"; then
   env='-QA'
else
   env='-prod'
fi
echo "FW Environment: $env"

platform=`getprop ro.board.platform`
echo "# Platform: $platform"


uboot_name=`curl http://repo.wdc.com/content/repositories/projects/MyCloudOS/MCAndroid$env/$1/ | grep uboot | grep $platform | busybox awk -F "\">" '{print $2}' | busybox awk -F "</a></td>" '{print $1}' | busybox sed -n '1p'`

#uboot_name="MCAndroid$env-$1-uboot-$platform-$2.zip"
echo "# uboot filename: $uboot_name"

file_server_url="ftp://ftp:ftppw@$file_server/firmware/"

mount -o remount,rw /mnt/media_rw/$usb
rm -r /mnt/media_rw/$usb/$MCAndroid*uboot*.zip
rm -r /mnt/media_rw/$usb/*uboot32*.bin
rm -r /mnt/media_rw/$usb/*uboot32*.md5

busybox wget "$file_server_url$uboot_name" -P "/mnt/media_rw/$usb"
busybox unzip -o "/mnt/media_rw/$usb/$uboot_name" -d "/mnt/media_rw/$usb"
