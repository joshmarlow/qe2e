all: check

FORMAT = black --include \.py
PIP = pip3
PROJECT = "qe2e"
PYTHON = python3
MIN_COVERAGE = 80
VENV = ".venv"
VENV_PATH=.venv
ENGLISH_MODEL=en_core_web_sm

setup_ubuntu: ## Install Python, pip and venv on Ubuntu (sudo required)
	@echo "Installing ubuntu packages"
	@sudo apt-get install python3 python3-pip python3-venv graphviz

setup: ## Create virtual environment
	@echo "Creating virtual env..."
	@$(PYTHON) -m venv $(VENV)
	@chmod u+x $(VENV)/bin/activate

install: setup ## Create virtual environment and install any dependencies
	@echo "Installing dependencies..."
	@$(VENV)/bin/activate
	@$(PIP) install -r requirements.txt
	@echo "Downloading spacy english model..."
	@spacy download $(ENGLISH_MODEL)

check: mypy linter coverage  ## Run type checking (mypy), linting and test coverage

linter:	## Run formatter
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
	@echo "Running tests with covearge..."
	@coverage report --fail-under=$(MIN_COVERAGE) \
					--omit=$(VENV_PATH)/*
	@coverage html --omit=$(VENV_PATH)/*

.PHONY: help

help:
	@grep -E '^[a-zA-Z0-9_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	| sed -n 's/^\(.*\): \(.*\)##\(.*\)/\1 - \3/p' \
	| column -t  -s ' '