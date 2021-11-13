==============================================================================
Intro

Repo for building Smart Contracts

To get started you'll need docker installed

The docker-compose is a work in progress...
but the DockerFile works
This project is written using pyteal, the python library used to write smart contracts for the Algorand blockchain

To build run `make build`
To run container in interactive mode run `make run`

==============================================================================
SETUP
Be sure to make a copy of DeveloperConfigExample.json that is renamed to DeveloperConfig.json and fill in the relevant
fields.

==============================================================================
GIT PRACTICES

Developers for this project should follow the practice of a forking workflow, basic link below, you can easily google additional information or ask other devs on the team more info :)
https://docs.gitlab.com/ee/user/project/repository/forking_workflow.html

Some of our developers are working from free github and con only fork to a private repo...this can be troublesome if the developer wants to share progress with the team. The workaround right now is that the developer opens a pull request to the main repo and gives the pull request a "DoNotMerge" tag

==============================================================================
Doc Links

[Docker Compose Setup](docs/start_docker_readme.md)
==============================================================================
