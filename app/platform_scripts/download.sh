#!/bin/sh

# [Download firmware to the usb plugged in UUT]
# Connect UUT by net console, and execute below commands:
#
# cd /tmp
# busybox wget ftp://ftp:ftppw@fileserver.hgst.com/firmware/download.sh -O download.sh
# sh upgrade.sh {fw ver} {env} {variant}

usb=`ls /mnt/media_rw`
if [ -z "$usb" ]; then
  echo "No USB drive detected! Stop upgrade firmware!"
  exit 1
else
  echo "# USB drive: $usb"
fi

platform=`getprop ro.board.platform`
echo "# Platform: $platform"

if [ $# -lt 3 ]; then
  echo "Please input sh ./download.sh {FW version} {dev1|qa1|prod} {user|userdebug|engr} {optional:file_server_ip}"
  exit 
fi

file_server=${4:-"fileserver.hgst.com"}

echo "# File Server: $file_server"
echo "# Firmware: $1"
echo "# Environment: $2"
echo "# Variant: $3"

fw_prefix="MCAndroid"  # Yoda and Kamino are in the same folder since 5.0.0-xxx

if [ "$2" == "qa1" ]; then
  build_name="$fw_prefix-QA"
elif [ "$2" == "prod" ]; then
  build_name="$fw_prefix-prod"
else
  build_name="$fw_prefix"
fi

if [ "$3" == "engr" ]; then
  tag="-engr"
elif [ "$3" == "user" ]; then
  tag="-user"
else
  tag=""
fi

# Change to os file + install tool since 5.0.0-337
fw_name="$build_name-$1-os-$platform$tag.zip"
install_tool_name="MCAndroid-5.0.0-337-install-tool-$platform-2.1.zip"
echo "# Firmware filename: $fw_name"
echo "# Install Tool: $install_tool_name"

file_server_url="ftp://ftp:ftppw@$file_server/firmware/"

mount -o remount,rw /mnt/media_rw/$usb
rm -r /mnt/media_rw/$usb/$fw_prefix*os*.zip
rm -r /mnt/media_rw/$usb/$fw_prefix*tool*.zip
rm -r /mnt/media_rw/$usb/install.img*
rm -r /mnt/media_rw/$usb/install_a*
rm -r /mnt/media_rw/$usb/rescue*
rm -r /mnt/media_rw/$usb/sata*
rm -r /mnt/media_rw/$usb/emmc*

busybox wget "$file_server_url$fw_name" -P "/mnt/media_rw/$usb"
busybox wget "$file_server_url$install_tool_name" -P "/mnt/media_rw/$usb"
busybox unzip -o "/mnt/media_rw/$usb/$fw_name" -d "/mnt/media_rw/$usb"
busybox unzip -o "/mnt/media_rw/$usb/$install_tool_name" -d "/mnt/media_rw/$usb"