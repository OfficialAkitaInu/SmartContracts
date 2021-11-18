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
