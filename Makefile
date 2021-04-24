all: check

FORMAT = black
PIP = pip
PROJECT = qe2e
PYTHON = python
MIN_COVERAGE = 80
VENV = .venv
VENV_PATH=.venv

setup_ubuntu: ## Install Python, pip and venv on Ubuntu (sudo required)
	@echo "Installing ubuntu packages"
	@sudo apt-get install python3 python3-pip python3-venv graphviz

setup: ## Create virtual environment
	@echo "Creating virtual env..."
	@python3 -m venv $(VENV)
	@chmod u+x $(VENV)/bin/activate

install: setup ## Create virtual environment and install any dependencies
	@echo "Installing dependencies..."
	@$(VENV)/bin/activate
	@$(PIP) install -r requirements.txt
	@$(PIP) install -r requirements-dev.txt

check: mypy linter coverage  ## Run type checking (mypy), linting and test coverage

formatter:	## Run formatter
	@echo "Running formatter..."
	@$(FORMAT) $(PROJECT)

mypy:  ## Perform type checking
	@echo "Running mypy..."
	@mypy $(PROJECT)

test:  ## Run tests
	@echo "Running tests..."
	@coverage run --branch \
					-m pytest \
					-vv \
					--doctest-modules \
					$(PROJECT)

coverage: test  ## Check code coverage for tests
	@echo "Checking covearge..."
	@coverage report --fail-under=$(MIN_COVERAGE) -m

.PHONY: help

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| sed -n 's/^\(.*\): \(.*\)##\(.*\)/\1 - \3/p' \
	| column -t  -s ' '
