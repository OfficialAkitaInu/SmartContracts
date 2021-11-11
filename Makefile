build: ## Build the container
	docker build -t smartcontracts .

build-nc: ## Build the container without caching
	docker build --no-cache -t smartcontracts .

run: ## Run container 
	docker run smartcontracts
