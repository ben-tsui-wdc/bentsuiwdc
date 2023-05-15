#!/bin/bash
set -x
set +e

# ${FFMPEG}: ffmpeg path

Source=$1 # Source video file (need 10-bits 60fps video and >= 5min)
Target=$2 # Dataset location
Dataset=$3 # 10s,1min,5min

# For FFMPEG: Too many packets buffered for output stream 0:1
#AdditionalParams="-max_muxing_queue_size 1024"

if [[ ! -e ${Source} ]]; then
    echo No source file
    exit 1
fi
echo Source: ${Source}

if [[ ${FFMPEG}x == x ]]; then
    FFMPEG=ffmpeg
fi
which ${FFMPEG} > /dev/null; 
if [[ $? -ne 0 ]]; then
    echo No ffmpeg found
    exit 1
fi

if [[ ${Dataset}x == x ]]; then
    Dataset=10s,1min,5min
fi
echo Dataset: ${Dataset}

EightBits=8_bit.mkv
function genEightBitsSample {
    test -e ${EightBits} && rm ${EightBits}
   # 10bit -> 8 bit 
    ${FFMPEG} -i "${Source}" ${AdditionalParams} \
       -c:v libx265 -preset medium -x265-params crf=28 -pix_fmt yuv420p -c:a copy -t ${1} \
       ${EightBits}
} 

function genVideo {
    # $1: source file
    # $2: codec
    # $3: profile and level params
    # $4: resolution and FPS
    # $5: duration
    # $6: output file name
    ${FFMPEG} -y -i "$1" ${AdditionalParams} \
        -map 0 -c:v $2 $3 -filter:v $4 -c:a copy -c:s copy -t $5 ${Workspace}/"$6"
}

function genDataset {
    echo Generating $1s dataset...
    genEightBitsSample $1
    Workspace=${Target}/${1}s
    test -e ${Workspace} && rm ${Workspace}/* || mkdir ${Workspace}
    # 4K 60FPS
    genVideo ${EightBits} hevc "-profile:v main -level:v 51" "scale=3840:2160,fps=60" $1 "H265_4K_60FPS_MAIN@L51_${1}S.mkv" # Monarch not support
    genVideo ${Source} hevc "-profile:v main10 -level:v 51" "scale=3840:2160,fps=60" $1 "H265_4K_60FPS_MAIN10@L51_${1}S.mkv" # 10bit - Monarch not support
    genVideo ${EightBits} libvpx-vp9 "-profile:v 0" "scale=3840:2160,fps=60" $1 "VP9_4K_60FPS_P0@_${1}S.mkv" # 8bit - all not support
    genVideo ${Source} libvpx-vp9 "-profile:v 1 -pix_fmt yuv422p" "scale=3840:2160,fps=60" $1 "VP9_4K_60FPS_P1@_${1}S.mkv" # 10bit - all not support
    #genVideo ${Source} libvpx-vp9 "-profile:v 2 -pix_fmt yuv420p10le" "scale=3840:2160,fps=60" $1 "VP9_4K_60FPS_P2@_${1}S.mkv" # 10bit - all not support
    # 4K 30FPS
    genVideo ${EightBits} hevc "-profile:v main -level:v 51" "scale=3840:2160,fps=30" $1 "H265_4K_30FPS_MAIN@L5_${1}S.mkv" # Monarch not support
    genVideo ${Source} hevc "-profile:v main10 -level:v 51" "scale=3840:2160,fps=30" $1 "H265_4K_30FPS_MAIN10@L5_${1}S.mkv" # 10bit - Monarch not support
    genVideo ${EightBits} libvpx-vp9 "-profile:v 0" "scale=3840:2160,fps=30" $1 "VP9_4K_30FPS_P0@_${1}S.mkv" # 8bit - Monarch not support
    genVideo ${Source} libvpx-vp9 "-profile:v 1 -pix_fmt yuv422p" "scale=3840:2160,fps=30" $1 "VP9_4K_30FPS_P1@_${1}S.mkv" # 10bit - all not support
    #genVideo ${Source} libvpx-vp9 "-profile:v 2 -pix_fmt yuv420p10le" "scale=3840:2160,fps=30" $1 "VP9_4K_30FPS_P2@_${1}S.mkv" # 10bit
    # 1080P 60FPS
    genVideo ${EightBits} h264 "-profile:v main -level:v 42" "scale=1920:1080,fps=60" $1 "H264_1080P_60FPS_MAIN@L42_${1}S.mkv"
    genVideo ${EightBits} h264 "-profile:v high -level:v 42" "scale=1920:1080,fps=60" $1 "H264_1080P_60FPS_HIGH@L42_${1}S.mkv"
    genVideo ${EightBits} h264 "-profile:v baseline -level:v 32" "scale=1920:1080,fps=60" $1 "H264_1080P_60FPS_BASELINE@L32_${1}S.mkv"
    genVideo ${EightBits} mpeg4 "-profile:v 0 -level:v 5" "scale=1920:1080,fps=60" $1 "MPEG4_1080P_60FPS_SIMPLE@L5_${1}S.mkv"
    genVideo ${EightBits} mpeg4 "-profile:v 15 -level:v 5" "scale=1920:1080,fps=60" $1 "MPEG4_1080P_60FPS_ADVANCEDSIMPLE@L5_${1}S.mkv"
    genVideo ${EightBits} libvpx-vp9 "" "scale=1920:1080,fps=60" $1 "VP9_1080P_60FPS_P0@_${1}S.mkv"
    # rotate tag
    ${FFMPEG} -y -i "${Workspace}/H264_1080P_60FPS_MAIN@L42_${1}S.mkv" -codec copy -metadata:s:v rotate=-90 "${Workspace}/H264_1080P_60FPS_MAIN@L42_${1}S_90D.mov"
    ${FFMPEG} -y -i "${Workspace}/H264_1080P_60FPS_MAIN@L42_${1}S.mkv" -codec copy -metadata:s:v rotate=-180 "${Workspace}/H264_1080P_60FPS_MAIN@L42_${1}S_180D.mov"
    ${FFMPEG} -y -i "${Workspace}/H264_1080P_60FPS_MAIN@L42_${1}S.mkv" -codec copy -metadata:s:v rotate=-270 "${Workspace}/H264_1080P_60FPS_MAIN@L42_${1}S_270D.mov"

    # Other resolution
    genVideo ${EightBits} hevc "-profile:v main -level:v 4" "scale=1920:1080,fps=30" $1 "H265_1080P_30FPS_MAIN@L4_${1}S.mkv" # Monarch not support
    genVideo ${EightBits} hevc "-profile:v main -level:v 31" "scale=1280:720,fps=30" $1 "H265_720P_30FPS_MAIN@L31_${1}S.mkv" # Monarch not support
    genVideo ${EightBits} libvpx-vp9 "" "scale=1280:720,fps=30" $1 "VP9_720P_30FPS_P0@_${1}S.mkv"
    genVideo ${EightBits} libvpx-vp9 "" "scale=640:480,fps=30" $1 "VP9_480P_30FPS_P0@_${1}S.mkv"
    genVideo ${EightBits} h264 "-profile:v main -level:v 31" "scale=1280:720,fps=30" $1 "H264_720P_30FPS_MAIN@L31_${1}S.mkv"
    genVideo ${EightBits} h264 "-profile:v main -level:v 30" "scale=640:480,fps=30" $1 "H264_480P_30FPS_MAIN@L3_${1}S.mkv"
    genVideo ${EightBits} mpeg4 "-profile:v 0 -level:v 2" "scale=1280:720,fps=30" $1 "MPEG4_720P_30FPS_SIMPLE@L2_${1}S.mkv"
    genVideo ${EightBits} mpeg4 "-profile:v 0 -level:v 1" "scale=640:480,fps=30" $1 "MPEG4_480P_30FPS_SIMPLE@L1_${1}S.mkv"
    # Other not support
    genVideo ${EightBits} msmpeg4 "" "scale=640:480,fps=30" $1 "MPEG43_480P_30FPS_${1}S.mkv" # MPEG-4 part 2 Microsoft variant version 3
    genVideo ${EightBits} mpeg2video "" "scale=640:480,fps=30" $1 "MPEG2_480P_30FPS_MAIN@MAIN_${1}S.mkv"
    genVideo ${EightBits} mpeg1video "" "scale=640:480,fps=30" $1 "MPEG_480P_30FPS_${1}S.mkv"
    genVideo ${EightBits} vp8 "" "scale=640:480,fps=30" $1 "VP8_480P_30FPS_${1}S.mkv"
    echo done.
    # Monarch doesn't support 4K videos and H.265.
}

if [[ ${Dataset} == *"10s"* ]]; then
    genDataset 10
fi

if [[ ${Dataset} == *"1min"* ]]; then
    genDataset 60
fi

if [[ ${Dataset} == *"5min"* ]]; then
    genDataset 300
fi
