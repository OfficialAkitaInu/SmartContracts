# Akita Smart Contracts

This repo contains assets for creating Smart Contacts for Akita Inu ASA.
## Getting Started

It's exciting to see so many people get involved! Below is a guide to
getting started that is intended to help accommodate anybody  who wants to
contribute.

For a detailed description on how to contribute to a Git project, read through
this guide from data school:
https://www.dataschool.io/how-to-contribute-on-github/

Additionally, developers working in this repo should follow the practice of a forking workflow.
The link below describes that workflow in detail, and you can easily google additional information
or ask others on the team more info.
https://docs.gitlab.com/ee/user/project/repository/forking_workflow.html

We follow PEP8 standards which can be found below.
https://www.python.org/dev/peps/pep-0008/


### 1. Clone the repo
First open your terminal and clone this repo by running this command:
```bash
git clone https://github.com/OfficialAkitaInu/SmartContracts.git
```

This will create a new directory names `SmartContracts` which you can develop in.
If you want this in a particular folder on your computer, make sure you navigate to
that folder using the `cd` command before cloning the repo.


Ensure you have Python 3.8 installed on your machine, and prefereable within a virtual environment
([here's some detail on how to setup a virtual environment]([https://mothergeo-py.readthedocs.io/en/latest/development/how-to/venv-win.html)).
Then, install the python requirements using the following command in your terminal:
```bash
pip install -r requirements.txt
```

### 2. Create and fund a test wallet
It's recommended that you create and fund a wallet that you use soley for development.
If in the case you accidently upload your key, you'll upload the test wallet's key and 
not your personal wallet's key.

To do so, you'll need to download the Algorand wallet app to your mobile device. From the app
you should then switch to test net, create a wallet, and fund that wallet (with the dispenser tool).
https://bank.testnet.algorand.network/

```
Note, you can also use my algo and switch it to testnet mode
```
You can follow detailed instructions to do so here:

https://www.algorandwallet.com/support/develop-help-articles/connecting-to-testnet

### 3. Add your test wallet's key into docker secrets
When you create your wallet, be sure to copy your mnemonic key to a safe place,
and label it as your test wallet's key.

We treat fund_account_mnemonic as a secret, and don't want it to be committed to source control, even though it's a test account. We have a separate environment variable file for this purpose. Create a file named `.secrets` under the `test/` directory with the plain text mneomic string. For example:

`test/.secrets`:
```bash
fund_account_mnemonic=dog akita wow pup cute super diamond woof bark leash walk chow bone pet slobber dig

```
(of course, replace this with your generated test mnemonic)

This file is added to .gitignore so it should not be committed to the project; you don't have to do anything special to ensure it doesn't get committed unless you are creating the file in the wrong directory / wrong name.

You can leave the other configs the same for development purposes.

```json
{
  "algodAddress": "http://algorand-sandbox-algod:4001",
  "algodToken": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "indexerAddress": "http://algorand-sandbox-indexer:8980",
  "indexerToken": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
}
```

### 4. Install Docker
You'll need [Docker](https://docs.docker.com/get-docker/) to run this development environment and develop on Algorand's TestNet. Detailed instructions for the setup are on the source project: [algorand/sandbox](https://github.com/algorand/sandbox).

### 5. Start the stack with the instructions in the `algorand/sandbox environment` with the `testnet` configuration.
To get started:
```
cd sandbox
./sandbox up testnet -v
```

This should be successful. You can verify with checking to make sure the docker containers are running with output something like this:
```
docker ps
CONTAINER ID   IMAGE                           COMMAND                  CREATED          STATUS          PORTS                                                                                                      NAMES
7ab2df254ad3   sandbox_indexer                 "/tmp/start.sh"          15 minutes ago   Up 15 minutes   0.0.0.0:8980->8980/tcp, :::8980->8980/tcp                                                                  algorand-sandbox-indexer
82232695d4a1   sandbox_akita_smart_contracts   "bash"                   15 minutes ago   Up 15 minutes                                                                                                              smartcontracts
3088ec20d64d   sandbox_algod                   "/opt/start_algod.sh"    15 minutes ago   Up 15 minutes   0.0.0.0:4001-4002->4001-4002/tcp, :::4001-4002->4001-4002/tcp, 0.0.0.0:9392->9392/tcp, :::9392->9392/tcp   algorand-sandbox-algod
60aa5d93858b   postgres:13-alpine              "docker-entrypoint.s…"   15 minutes ago   Up 15 minutes   0.0.0.0:5433->5432/tcp, :::5433->5432/tcp                                                                  algorand-sandbox-postgres

```

You can see any containers that failed to start with `docker ps -a`. You can get logs from those containers with `docker logs <CONTAINER ID>`, e.g. if in the above example the indexer failed to start `docker logs 7ab2df254ad3`


### 6. Wait for node sync, then run tests and confirm everything's working
It will take a few minutes for your testnet algod node to catch up. You will need it to finish syncing before you can run the tests.

Finally, you should run some tests on your machine to ensure everything has been
set up properly. To do this, first connect to the `smartcontracts` container:
```
docker exec -it smartcontracts bash
```
Then, run the following command:

```bash
python -m pytest
```

If everything checks out, then you should receive a response that looks something
like this:
```bash
python -m pytest
===================== test session starts =====================
platform darwin -- Python 3.8.2, pytest-6.2.5, py-1.11.0, pluggy-1.0.0
rootdir: /SmartContracts
collected xxxx items

test/timed_asset_lock_contract_test.py ......                                                                                                                                                                                    [100%]

===================== 6 passed in 141.36s (0:02:21) =====================
```

## Common Errors

### 1. An Exception running the tests with `pending tx not found in timeout rounds`
Wait a bit longer for your algod node to sync

### 2. An Exception running the tests with `overspend`
You may need more algo to your test wallet with dispenser. Or you should wait a bit longer for the node to sync.

### 3. Fast-catchup staying at 0%
If you've run a `./sandbox up` command with an environment config other than
`testnet`, or if you want to change your sandbox configuration, you'll need to
shutdown and clean the sandbox environment by running:
```
./sandbox down
./sandbox clean
```

After that you can start your sandbox again with:
```
./sandbox up testnet -v
```
