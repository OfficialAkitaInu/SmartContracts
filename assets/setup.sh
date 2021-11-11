#!/bin/bash

cp -fv $HOME/node/genesisfiles/genesis.json $HOME/node/data/
sed -i 's/mainnet/testnet/g' $HOME/node/data/genesis.json

