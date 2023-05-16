# FROM artifactory.wdc.com:6609/python:2.7.18
FROM python:2.7.18
MAINTAINER ben.tsui@wdc.com

RUN sed -i '/jessie-updates/d' /etc/apt/sources.list
RUN apt-get update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y \
        libxslt1.1 \
        mariadb-client \
        python-mysqldb \
        android-tools-adb \
        vim \
        cifs-utils \
        netcat \
        mediainfo \
        libglib2.0-dev \
        bluez \
        imagemagick \
        ncftp \
        ntpdate \
        nfs-common \
    --allow-downgrades \
    --fix-missing \
    --no-install-recommends && \
    rm -rf /var/lib/apt/lists/*

RUN echo 'alias ll="ls -alh --color=auto"' >> /root/.bashrc

# Install static ffmpeg
WORKDIR /root/
RUN wget http://fileserver.hgst.com/utility/ffmpeg/5.0-static/ffmpeg-release-amd64-static.tar.xz
RUN tar xvfp ffmpeg-release-amd64-static.tar.xz --strip=1 -C /usr/local/bin/
RUN rm ffmpeg-release-amd64-static.tar.xz

# Adding requirements.txt by itself so that only a change to that file
# will trigger a reinstall of the python packages
RUN mkdir /root/app
WORKDIR /root/app
COPY app/ /root/app/
RUN pip install --default-timeout=600 --upgrade pip==20.3.4 && \
    pip install --default-timeout=600 -r requirements.txt
RUN chmod 400 /root/app/platform_libraries/ssh_cert/id_ecdsa

ENTRYPOINT ["/root/app/run.sh"]

