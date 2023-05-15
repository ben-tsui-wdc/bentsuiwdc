#!/bin/bash -x

# Container to run a python app
#
# Basic usage
# ./start.sh yourpythonscript.py [OPTIONS]
#
# If Python buffers output (and you don't want it to), try this:
# PYTHONUNBUFFERED=0 ./start.sh yourpythonfile.py [OPTIONS]

set -e
set +x
APPNAME=${APPNAME:-pythonapp}

# Use '-i' to run in interactive mode
RUN_CMD=
RUN_OPTS=${RUN_OPTS}
if [ "$1" = "-i" ]; then
    RUN_CMD=
    RUN_OPTS='-it --entrypoint /bin/bash'
fi

# Error checks
if [ $# -eq 0 ] && [ "$RUN_CMD" == "" ]; then
    echo "Usage: $0 pythonapp.py [OPTIONS] PARAMETERS"
    exit 1
fi

if [ ! -e app ]; then
    echo "Directory named \"app\" (with your code inside) not found"
    exit 1
fi

# Leave this section alone
if [ "$XPATH" = "" ]; then
    XPATH=$(pwd)
else
    echo "Adjusting path for the underlying host filesystem"
    XPATH="${XPATH}"/$(pwd | sed 's/.*workspace\///')
fi

# Pass the environment variables in this list to docker if they
# are defined and have any value except blank
VARS_OF_INTEREST="\
    BUILD_NUMBER \
    BUILD_URL \
    DOCKER_IP \
    FIRMWARE_NUMBER \
    FIRMWARE_VERSION \
    HOST_IP \
    INVENTORY_DEBUG \
    INVENTORY_FORCE \
    INVENTORY_RETRY_COUNT \
    INVENTORY_RETRY_DELAY \
    INVENTORY_URL \
    JOB_NAME \
    PLATFORM_DESCRIPTION \
    PRODUCT_NAME \
    PYTHONUNBUFFERED \
    UBOOT_NUMBER \
    UBOOT_VERSION \
    UUT_BROKEN \
    UUT_ENVIRONMENT \
    UUT_FIRMWARE \
    UUT_LOCATION \
    UUT_PLATFORM \
    UUT_VARIANT \
    UUT_SITE \
    UUT_TAG \
    UUT_UBOOT \
    UUT_USB \
    UUT_REBOOTABLE \
    UUT_UPDOWNLOADABLE \
    UUT_USBABLE \
    UUT_FACTORYRESETABLE \
"
VARS_TO_PASS=
for var in $VARS_OF_INTEREST; do
    NEW_ADD="$(eval echo \$$var)"
    if [ "$NEW_ADD" ]; then
        VARS_TO_PASS="$VARS_TO_PASS -e $var=$NEW_ADD"
    fi
done
set -x

# Install ssh certs
SSH_CERT_FOLDER=app/platform_libraries/ssh_cert/
test -e ${SSH_CERT_FOLDER} || mkdir ${SSH_CERT_FOLDER}
if [[ `ls ${SSH_CERT_FOLDER} | wc -l | awk '{ print $1}'` -ne 0 ]]; then
    echo "ssh certs already installed"
elif [[ x"${SSH_CERT}" != x"" ]]; then
    cp ${SSH_CERT}/* ${SSH_CERT_FOLDER}
elif [[ -e ~/ssh_cert ]]; then
    cp ~/ssh_cert/* ${SSH_CERT_FOLDER}
else
    echo "No ssh certs found in host"
fi

docker build --tag ${APPNAME} .

rm -f container.cid

CHAR_DEVICE=/dev/ttyACM0

#if [ -c "$CHAR_DEVICE" ]; then
#    echo "$CHAR_DEVICE exists"
#else
#    echo "$CHAR_DEVICE is not available"
#    exit 1
#fi

set +e # for always copy file from docker container

# Mount local output to container for instant update.
if [ x"$LOGM" = x"y" ]; then
    DOCKER_OPTS="-v $(pwd)/output:/root/app/output"
    # move data for overwite issue.
    if [ x"$LOGD" = x"y" ]; then
        test -e output && mv output output.$(date '+%Y%m%d-%H%M%S').moved
    fi
fi

docker run \
    ${RUN_OPTS} \
    --tty \
    --cidfile container.cid \
    --privileged \
    --net=host \
    ${DOCKER_OPTS} \
    ${VARS_TO_PASS} \
    ${APPNAME} \
    ${RUN_CMD} "$@"

EXIT_CODE=$?

if [ x"$LOGM" != x"y" ]; then
    # Copy output folder and subdirectories from inside the container
    docker cp $(cat container.cid):/root/app/output ./
    # Backup current run data for overwite issue.
    OUTPUT_FOLDER=output.`echo "$@" | python -c 'import sys; print sys.stdin.read().split(" ")[0].split(".")[0].split("/")[-1][:20]'`
    test -e ${OUTPUT_FOLDER} && OUTPUT_FOLDER=$OUTPUT_FOLDER.$(cat container.cid | cut -c 1-10)
    mkdir ./${OUTPUT_FOLDER} && docker cp $(cat container.cid):/root/app/output ./${OUTPUT_FOLDER}
fi

KEEP_CONTAINER=${KEEP_CONTAINER:-}

if [[ ! $KEEP_CONTAINER ]]; then
  docker stop $(cat container.cid)
  docker rm $(cat container.cid)
fi

exit $EXIT_CODE
