#!/bin/bash -ue
# author: Ben Tsui <Ben.Tsui@wdc.com>
#
# brief: The test_runner.sh is used to setup uut device and execute automation tests on Jenkins server.
#        Sample Jenkins job: 
#        https://autojenkins.wdmv.wdc.com/view/Automation/job/Kamino-Android-Platform-FFmpeg-Stress-Test
#
# Environment variables in Jenkins job:
# 
# required: PLATFORM -> monarch / pelican / yoda / yodaplus
#           FIRMWARE_NUMBER -> will get the latest fw if not specified
#           ENVIRONMENT -> dev1 / qa1 / prod
#           VARIANT -> userdebug / user / engr
#           LOGSTASH_IP -> used for upload results to ELK
#           TEST_NAME -> used for checking test result exist on ELK
#           KAMINO_VERSION -> Kamino version, 1.2 / 1.3 / 1.4 / 1.5 / 2.0 (yoda)
#           SCRIPT_PATH -> where the script located
#           SCRIPT_ARGV -> the script arguments
#               example: --env ${ENVIRONMENT} --var ${VARIANT}
#           *** Put the arguments in INV_ARGV if you can only get the value AFTER device is checked out ***
#           INV_ARGV -> If you need to get uut info from inventory server and pass it to your script.
#                       Note that UUT_IP is already passed to script by default.        
#                       Check available arguments in "execute_test" function and seperate them by ","
#               example: INV_ARGV="Power,Serial"
#           WIFI_SSID -> for yoda only
#           WIFI_PASSWORD ->< for yoda only
#
# optional: ITER -> how many loops
#           UUT_IP -> Will randomly checkout a device from inventory server if not specified
#           CHECK_RESULT_EXIST -> check result exist on ELK before testing
#           DRY_RUN -> result will not upload to ELK

function check_bs4_module() {
    # Install python module: bs4 for parsing latest bat_passed fw from the web of build server
    bs4_module=`pydoc modules | grep bs4`
    if [ "${bs4_module}" == "" ]; then
        pip install bs4
    fi
}

function get_latest_fw() {
    cd "${WORKSPACE}"/platform_automation/app/jenkins_scripts
    if [ "${FIRMWARE_NUMBER}" != "" ]; then
        latest_fw="${FIRMWARE_NUMBER}"
    else
        latest_fw=$(python get_the_latest_fw.py -product ${PLATFORM} -env ${ENVIRONMENT} -variant ${VARIANT} --kamino_version ${KAMINO_VERSION})
    fi

    if [ $? -ne 0 ]; then
        echo "Failed to get latest firmware version, stop the test!"
        exit 1
    else    
        echo "Latest firmware version is: ${latest_fw}"
    fi
}

function check_result_exist() {
    cd "${WORKSPACE}"/platform_automation/app/jenkins_scripts
    if ${CHECK_RESULT_EXIST}; then
        test_result_exist=$(python test_result_exists.py -fw ${latest_fw} -test_name ${TEST_NAME} -es_ip ${LOGSTASH_IP})
    else
        test_result_exist="non-exists"
    fi

    echo "Test result exist: ${test_result_exist}"

    if [ $? -ne 0 ]; then
        echo "Failed to check test results on ELK, stop the test!"
        exit 1
    else
        if [ ${test_result_exist} == "exists" ]; then
            echo "Test result already exist, no need to execute test."
            exit 1
        fi
    fi
}

function check_out_device() {
    cd "${WORKSPACE}"/platform_automation
    RUN_CMD="--platform ${PLATFORM} -e ${ENVIRONMENT} -url http://sevtw-inventory-server.hgst.com:8010/InventoryServer"
    if [ "${UUT_IP}" != "" ]; then
        RUN_CMD+=" --uut_ip ${UUT_IP}"
    fi
    
    if [ "${CHECKOUT_ARGV}" != "" ]; then
        RUN_CMD+=" ${CHECKOUT_ARGV}"
    fi

    ./start.sh jenkins_scripts/checkout_device.py ${RUN_CMD}
    if [ $? -ne 0 ]; then
        echo "Failed to check out device, stop the test!"
        exit 1
    fi

    echo "### UUT device info ###"
    UUT_INFO=$(cat ${WORKSPACE}/platform_automation/output/UUT)
    echo $UUT_INFO

    # Device information from Inventory server, add more if necessary
    UUT_IP=$(echo $UUT_INFO | jq -r .internalIPAddress)
    POWER_IP=$(echo $UUT_INFO | jq -r .powerSwitch.ipAddress)
    POWER_PORT=$(echo $UUT_INFO | jq -r .powerSwitch.port)
    SERIAL_IP=$(echo $UUT_INFO | jq -r .serialServer.ipAddress)
    SERIAL_PORT=$(echo $UUT_INFO | jq -r .serialServer.port)

    echo UUT_IP=$UUT_IP >> ${WORKSPACE}/build.device_info
    echo POWER_IP=$POWER_IP >> ${WORKSPACE}/build.device_info
    echo POWER_PORT=$POWER_PORT >> ${WORKSPACE}/build.device_info
    echo SERIAL_IP=$SERIAL_IP >> ${WORKSPACE}/build.device_info
    echo SERIAL_PORT=$SERIAL_PORT >> ${WORKSPACE}/build.device_info
}

function compare_uut_firmware() {
    cd "${WORKSPACE}"/platform_automation
    ./start.sh jenkins_scripts/fwcheck.py --uut_ip "${UUT_IP}" --fw "${latest_fw}" --env "${ENVIRONMENT}" --variant "${VARIANT}"
    FW_CHECK=$(grep -Po '(?<=^FW_CHECK=)\w*$' ./output/result.txt)
    echo "FW_CHECK=${FW_CHECK}"
}

function setup_device() {
    cd "${WORKSPACE}"/platform_automation
    if [ ${FW_CHECK} == "False" ]; then
        echo "Firmware is not ${latest_fw}, updating now..."
        RUN_CMD="-ip ${UUT_IP} -fw ${latest_fw} -env ${ENVIRONMENT} -var ${VARIANT} -ss_ip ${SERIAL_IP} -ss_port ${SERIAL_PORT}"
        if ${LOCAL_IMAGE}; then
            RUN_CMD+=" --local_image"
        fi

        ./start.sh bat_scripts_new/fw_update_utility.py ${RUN_CMD} --dry_run
        if [ -f "./output/UpdateSuccess.txt" ]; then
            echo "Update Firmware Success!"
            sleep 60
        else
            echo "Download Firmware Failed! Stop the test!"
            exit 1
        fi
    fi

    if [ "${NO_FACTORY_RESET}" == "true" ]; then
        echo "DON'T do factory reset. Start the test in 60 secs..."
    else
        echo "running factory reset..."

        RUN_CMD="-ip "${UUT_IP}" -env "${ENVIRONMENT}" -var "${VARIANT}" -ss_ip "${SERIAL_IP}" -ss_port "${SERIAL_PORT}" -noapi -set uut_owner=False --dry_run"

        if echo "${PLATFORM}" | grep -q "yoda"; then
            RUN_CMD+=" -ap_ssid ${WIFI_SSID} -ap_password ${WIFI_PASSWORD}"
        fi

        ./start.sh bat_scripts_new/factory_reset.py ${RUN_CMD}

        if [ $? -ne 0 ]; then
            echo "Factory reset failed, stop the test!"
            exit 1
        else
            echo "Factory reset complete! Start the test in 60 secs..."
            sleep 60
        fi
    fi
    
}

function execute_test() {
    cd "${WORKSPACE}"/platform_automation
    RUN_CMD="--uut_ip ${UUT_IP} ${SCRIPT_ARGV}"
    if [ "${INV_ARGV}" != "" ]; then
        IFS=',' read -a inv_argv_list <<< "${INV_ARGV}"
        for i in "${inv_argv_list[@]}"
        do
            if [ $i == "Power" ]; then
                RUN_CMD+=" -power_ip ${POWER_IP} -power_port ${POWER_PORT}"
            elif [ $i == "Serial" ]; then
                RUN_CMD+=" -ss_ip ${SERIAL_IP} -ss_port ${SERIAL_PORT}"
            fi
        done
    fi

    if echo "${PLATFORM}" | grep -q "yoda"; then
        RUN_CMD+=" -ap_ssid ${WIFI_SSID} -ap_password ${WIFI_PASSWORD}"
    fi

    ./start.sh "${SCRIPT_PATH}" ${RUN_CMD}

    if [ $? -ne 0 ]; then
        echo "Execute test failed!"
        exit 1
    fi
}

function checkin_device() {
    cd "${WORKSPACE}"/platform_automation
    ./start.sh jenkins_scripts/checkin_device.py
    if [ $? -ne 0 ]; then
        echo "Failed to check in device, stop the test!"
        exit 1
    fi
}

function connect_wifi() {
    if echo "${PLATFORM}" | grep -q "yoda"; then
        ./start.sh platform_libraries/serial_client.py -ssid "${WIFI_SSID}" -password "${WIFI_PASSWORD}" -ip "${SERIAL_IP}" -port "${SERIAL_PORT}"
    else
        echo "Not wifi devices, no need to connect wifi"
    fi
}

set +x

echo "### Start running automation test ###"
# check_bs4_module
get_latest_fw
# check_result_exist
check_out_device
connect_wifi  # For Yoda
if [[ $1 == "no_update" ]]; then
    echo "Check firmware version and update will be skipped"
else
    compare_uut_firmware
    setup_device
fi
execute_test
checkin_device
echo "### Automation test finished ###"
