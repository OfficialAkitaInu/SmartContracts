#!/bin/bash
rm /shared_volume/algod.token
cd /root/node/data
rm ./genesis.json
ln -s /root/node/genesisfiles/testnet/genesis.json ./genesis.json
cd ..
./update.sh -d ./data/
cp ./data/algod.token /shared_volume/
./goal node -d ./data/ catchup "`wget -qO- https://algorand-catchpoints.s3.us-east-2.amazonaws.com/channel/testnet/latest.catchpoint`"