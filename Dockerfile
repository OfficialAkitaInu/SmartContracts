FROM algorand/testnet:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    vim \
    less \
    tmux

RUN mkdir -p /AkitaInuASASmartContracts

WORKDIR /AkitaInuASASmartContracts

COPY utilities /AkitaInuASASmartContracts

COPY requirements.txt /AkitaInuASASmartContracts

RUN pip3 install -r /AkitaInuASASmartContracts/requirements.txt

RUN mkdir -p $HOME/node/data

RUN chown -R root: $HOME/node/data

RUN echo 'export ALGORAND_DATA="$HOME/node/data"' >> $HOME/.bashrc

RUN echo 'export PATH="$HOME/node:$PATH"' >> $HOME/.bashrc

WORKDIR /root/node

COPY assets/setup.sh .

RUN chmod 755 setup.sh
