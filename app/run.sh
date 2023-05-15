#!/bin/bash -e

# Using this script to make a simple command suite.

export PYTHONPATH=`dirname "$(readlink -f "$0")"`:${PYTHONPATH}

if [ ! -z ${JOB_NAME-} ]; then # Run with Jenkins Job.

    if [ ! -d /root/app/output ]; then
        mkdir /root/app/output
    fi

    # Run BAT 
    if [ "$1" == "--bat" ]; then
        shift
        cd /root/app/bat_scripts
        python "$@"
        if [ -e output.xml ]; then
            mv output.xml /root/app/output/
        fi
    # Run normal case
    elif [[ $# -gt 0 ]]; then
        cd /root/app
        python "$@"
    fi

else # Run in terminal.
    if [ ! -d `pwd`/output ]; then # Create output on current location.
        mkdir `pwd`/output
    fi

    python "$@"
fi
