FROM algorand/testnet:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    vim \
    tmux \
    wget \
    curl

COPY start_algorand_node_testnet.sh /

RUN chmod +x /start_algorand_node_testnet.sh

CMD /start_algorand_node_testnet.sh && \
   tail -f /dev/null