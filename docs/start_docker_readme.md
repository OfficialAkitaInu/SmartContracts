# Docker Compose Setup

This should result in a working docker environment with the local directory
`./data` mounted into the container at `/root/node/data`. This directories
contents have been excluded in git, as the first time you run the setup script
the token and keys generated will be unique to each developer.

## Initial Setup

First, create the data directory in the root of the project.

`mkdir data`

This will be mounted into the docker container, and give you access to the API
token on your local machine.

## Docker Compose

`docker-compose up -d --build`

If you get a permissions error, ensure that `./data` is empty the first time
you run it. There can be issues with permissions differences between the root
of the container and your local user. You may need to run the `docker-compose`
with sudo/admin permissions.

## After Docker Compose

Launch a shell into the container via:

`docker exec -it smartcontracts_algo-testnet_1 /bin/bash`

then:

`cd $HOME/node && sh setup.sh`

Note: name might differ from `smartcontracts_algo-testnet_1`.

Alternatively, run the script directly through docker via:

`docker exec -t smartcontracts_algo-testnet_1 sh /root/node/setup.sh`

## Verify

At this point there should be an algod token and other data generated for
`testnet` under `./data`. e.g., `$HOME/node/data/algod.token`.


