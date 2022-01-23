#!/bin/bash
cd /root/node/data
rm ./genesis.json
ln -s /root/node/genesisfiles/mainnet/genesis.json ./genesis.json
cd ..
cp ./data/algod.token /shared_volume/
./update.sh -d ./data/
./goal node -d ./data/ catchup "`wget -qO- https://algorand-catchpoints.s3.us-east-2.amazonaws.com/channel/mainnet/latest.catchpoint`"