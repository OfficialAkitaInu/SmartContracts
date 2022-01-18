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

### 2. Install the requirements

Ensure you have Python 3.8 installed on your machine, and prefereable within a virtual environment
([here's some detail on how to setup a virtual environment]([https://mothergeo-py.readthedocs.io/en/latest/development/how-to/venv-win.html)).
Then, install the python requirements using the following command in your terminal:
```bash
pip install -r requirements.txt
```

### 3. Create a fund a test wallet
It's recommended that you create and fund a wallet that you use only for development.
If in the case you accidentally upload your key, you'll upload the test wallet's key and 
not your personal wallet's key.

To do so, you'll need to download the Algorand wallet app to your mobile device. From the app
you should then switch to test net, create a wallet, and fund that wallet.
You can follow detailed instructions to do so here:


https://www.algorandwallet.com/support/develop-help-articles/connecting-to-testnet

### 4. Input your test wallet's key into testConfig.json
When you create your wallet, be sure to copy your mnemonic key to a safe place,
and label it as your test wallet's key. Take that key and enter it as the value 
to the `fund_account_mnemonic` key in `testConfig.json`. 

```json
{
  "algodAddress": "http://localhost:4001",
  "algodToken": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "indexerAddress": "http://localhost:8980",
  "indexerToken": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "fund_account_mnemonic": "key1 key2 key3 key4 key5 key6 key7 key8 key9 key10 key11 key12 key13 key14 key15 key16 key17 key18 key19 key20 key21 key22 key23 key24 key25"
}
```
### 5. Install Docker
You'll need docker to run these scripts and develop on Algorand's TestNet. To that
end, follow [Docker's instructions](https://docs.docker.com/compose/install/) to
download and install Docker Compose if you haven't already.

Next, run `docker-compose up -d`. This should start all containers.

Connect to your SmartContracts container with:
`docker ps` and get the Container ID for the smart contracts container, then
`docker exec -it <container_id> /bin/bash`

### 6. Clone and start Algorand Sandbox

Clone [Algorand's Sandbox environment](https://github.com/algorand/sandbox) and spin up a sandbox
TestNet instance using the following command in your terminal:

```bash
sandbox/sandbox up testnet
```

This will take a couple of minutes, and once it's done you'll be returned back to your
current working directory in your terminal.

To ensure that this worked, you can list the running containers by running this in 
your terminal:
```bash
docker ps
```

If everything started properly you should see something list this:

```bash
CONTAINER ID   IMAGE                     COMMAND                  CREATED        STATUS        PORTS                                                      NAMES
d1e7878f5d0b   sandbox_indexer           "/tmp/start.sh"          2 hours ago   Up 2 hours   0.0.0.0:8980->8980/tcp                                     algorand-sandbox-indexer
b44b170089d0   postgres:13-alpine        "docker-entrypoint.s…"   2 hours ago   Up 2 hours   0.0.0.0:5433->5432/tcp                                     algorand-sandbox-postgres
b91982aff959   sandbox_algod             "/opt/start_algod.sh"    2 hours ago   Up 2 hours   0.0.0.0:4001-4002->4001-4002/tcp, 0.0.0.0:9392->9392/tcp   algorand-sandbox-algod
```

### 5. Run tests and confirm everything's working
Finally, you should run some tests on your machine to ensure everything has been
set up properly. To do this, open up a terminal and run the following command:

```bash
python -m pytest test/
```

If everything checks out, then you should receive a response that looks something
like this:
```bash
python -m pytest test/
===================== test session starts =====================
platform darwin -- Python 3.8.2, pytest-6.2.5, py-1.11.0, pluggy-1.0.0
rootdir: /SmartContracts
collected 6 items                                                                                                                                                                                                                      

test/timed_asset_lock_contract_test.py ......                                                                                                                                                                                    [100%]

===================== 6 passed in 141.36s (0:02:21) =====================
```