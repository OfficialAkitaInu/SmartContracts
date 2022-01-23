FROM algorand/testnet:latest

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    vim \
    tmux \
    wget

COPY start_algorand_node_mainnet.sh /

RUN chmod +x /start_algorand_node_mainnet.sh

CMD /start_algorand_node_mainnet.sh && tail -f /dev/null