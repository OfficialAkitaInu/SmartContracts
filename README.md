# Akita Smart Contracts

## Getting Started

it's exciting to see so many people get involved! Below there is a guide to 
getting started that is intended to help accommodate anybody  who wants to 
contribute.  

For a detailed description on how to contribute to a Git project, read through 
this guide from data school:
https://www.dataschool.io/how-to-contribute-on-github/

#### 1. Clone the repo
First open your terminal and clone this repo by running this command:
```bash
git clone https://github.com/OfficialAkitaInu/SmartContracts.git
```

This will create a new directory names `SmartContracts` which you can develop in.
If you want this in a particular folder on your computer, make sure you navigate to 
that folder using the `cd` command before cloning the repo.

#### 2. Install the requirements

Ensure you have Python 3.8 installed on your machine, and prefereable within a virtual environment
([here's some detail on how to setup a virtual environment]([https://mothergeo-py.readthedocs.io/en/latest/development/how-to/venv-win.html)).
Then, install the python requirements using the following command in your terminal:
```bash
pip install -r requirements.txt
```

#### 3. Create a fund a test wallet
It's recommended that you create and fund a wallet that you use soley for development.
If in the case you accidently upload your key, you'll upload the test wallet's key and 
not your personal wallet's key.

To do so, you'll need to download the Algorand wallet app to your mobile device. From the app
you should then switch to test net, create a wallet, and fund that wallet.
You can follow detailed instructions to do so here:


https://www.algorandwallet.com/support/develop-help-articles/connecting-to-testnet

#### 4. Input your test wallet's key into testConfig.json
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

#### 5. Run tests and confirm everything's working
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

==============================================================================
Intro

Repo for building Smart Contracts

==============================================================================
REGARDING THE DOCKER INCLUDED WITH THIS PROJECT

NOTE: The docker in this repository is not used for development currently, it is a work in progress.
Currently our devs are making use of the Algorand Sandbox Docker found here
https://github.com/algorand/sandbox

==============================================================================
SETUP

Be sure to make a copy of DeveloperConfigExample.json and rename to DeveloperConfig.json and fill in the relevant
fields.
Likewise, make a copy of the /test/testConfigExample.json and rename to testConfig.json and fill in the relevant
fields.

vvvvvvvvvvvvvvvIGNORE THIS BLOCKvvvvvvvvvvvvvvv
To get started you'll need docker installed

The docker-compose is a work in progress...
but the DockerFile works
This project is written using pyteal, the python library used to write smart contracts for the Algorand blockchain

To build run `make build`
To run container in interactive mode run `make run`
^^^^^^^^^^^^^^IGNORE THIS BLOCK^^^^^^^^^^^^^^

==============================================================================
GIT PRACTICES

Developers for this project should follow the practice of a forking workflow, basic link below, you can easily google additional information or ask other devs on the team more info :)
https://docs.gitlab.com/ee/user/project/repository/forking_workflow.html

==============================================================================
CODING PRACTICES

For Python we are doing our very best to adhere to the pep-8 standard
https://www.python.org/dev/peps/pep-0008/

==============================================================================
Doc Links

[Docker Compose Setup](docs/start_docker_readme.md)
==============================================================================
