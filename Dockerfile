FROM ubuntu:jammy

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    vim \
    less \
    tmux

RUN ln -sf /usr/bin/python3 /usr/bin/python

RUN mkdir -p /SmartContracts

WORKDIR /SmartContracts

COPY . /SmartContracts

RUN pip3 install -r /SmartContracts/requirements.txt
