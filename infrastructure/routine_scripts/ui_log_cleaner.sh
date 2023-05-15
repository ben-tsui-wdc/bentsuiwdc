#!/bin/bash
if [ x${1} == "x-h" ]; then
	echo This is a tool to clean up UI logs.
	echo Command example: ./ui_log_cleaner.sh workspace-path keep-days
	echo - workspace-path: the path which has the folder test_logs.
	echo - keep-days: the time days of logs want to keep. Default is 30.
fi
if [ x${1} == x ]; then
	echo need a workspave path
	exit 1 
fi
find ${1}/test_logs/* -type d -maxdepth 1 -ctime +${2:-30} | xargs rm -r
