FROM algorand/testnet:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip

RUN mkdir -p /AkitaInuASASmartContracts

COPY requirements.txt /AkitaInuASASmartContracts

RUN pip3 install -r /AkitaInuASASmartContracts/requirements.txt