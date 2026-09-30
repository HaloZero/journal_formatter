VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
FLASK := $(VENV)/bin/flask
PORT := 8571
HOST := 127.0.0.1

export FLASK_APP := app

.PHONY: help venv install setup db-init db-start db-stop db-restart db-status db-create db-ensure \
	migrate migration run shell test import analyze analyze-unanalyzed import-photos clean

help:
	@echo "make setup             create venv, install deps, init/start/create the local db, run migrations"
	@echo "make venv              create the virtualenv"
	@echo "make install           install dependencies + spaCy model into the venv"
	@echo "make db-init           initialize the project-local Postgres cluster (data/postgres)"
	@echo "make db-start          start the local Postgres cluster"
	@echo "make db-stop           stop the local Postgres cluster"
	@echo "make db-restart        restart the local Postgres cluster"
	@echo "make db-status         check whether the local Postgres cluster is running"
	@echo "make db-create         create the journal_python database"
	@echo "make migrate           apply migrations (flask db upgrade)"
	@echo "make migration name=…  generate a new migration (flask db migrate -m name)"
	@echo "make run               start the dev server with debug/auto-reload (flask run --debug)"
	@echo "make shell             open a flask shell"
	@echo "make test              run the test suite (pytest)"
	@echo "make import            trigger /import against a running server"
	@echo "make analyze           trigger /analyze (all entries) against a running server"
	@echo "make analyze-unanalyzed trigger /analyze?only_unanalyzed=1 against a running server"
	@echo "make import-photos     trigger /import_photos against a running server"
	@echo "make clean             remove Python cache files"

venv:
	python3 -m venv $(VENV)

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	$(PYTHON) -m spacy download en_core_web_trf

setup: install db-init db-start db-create migrate
	@echo "Setup complete. Run 'make run' to start the server."

db-init:
	./bin/db.sh init

db-start:
	./bin/db.sh start

db-stop:
	./bin/db.sh stop

db-restart:
	./bin/db.sh restart

db-status:
	./bin/db.sh status

db-create:
	./bin/db.sh create

db-ensure:
	@./bin/db.sh status > /dev/null 2>&1 || ./bin/db.sh start

migrate:
	$(FLASK) db upgrade

migration:
	$(FLASK) db migrate -m "$(name)"

run: db-ensure
	$(FLASK) run --host $(HOST) --port $(PORT) --debug

shell:
	$(FLASK) shell

test:
	$(PYTHON) -m pytest

import:
	curl -s "http://$(HOST):$(PORT)/import" > /dev/null && echo "Import started"

analyze:
	curl -s "http://$(HOST):$(PORT)/analyze" > /dev/null && echo "Analysis started"

analyze-unanalyzed:
	curl -s "http://$(HOST):$(PORT)/analyze?only_unanalyzed=1" > /dev/null && echo "Analysis of unanalyzed entries started"

import-photos:
	curl -s "http://$(HOST):$(PORT)/import_photos" > /dev/null && echo "Photo import started"

clean:
	find . -name "__pycache__" -not -path "./venv/*" -exec rm -rf {} +
	find . -name "*.pyc" -not -path "./venv/*" -delete
