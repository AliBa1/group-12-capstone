# Detect the operating system
ifeq ($(OS),Windows_NT)
    # Windows-specific setup
    VENV_ACTIVATE = .\env\Scripts\activate
    PYTHON = py
else
    # macOS/Linux-specific setup
    VENV_ACTIVATE = source env/bin/activate
    PYTHON = python
endif

.PHONY: help

help:
	@echo "Available commands:"
	@echo "  install  Install project dependencies"
	@echo "  run     	Run server to website"
	@echo "  test     Run tests"
	@echo "  format   Format code"
	@echo "  docs     Build documentation"

run:
	$(VENV_ACTIVATE) && \
	$(PYTHON) -m pip install -r requirements.txt && \
	cd src && \
	$(PYTHON) manage.py runserver

test:
	$(VENV_ACTIVATE) && \
	cd src && \
	$(PYTHON) manage.py test

redis-mac:
	$(VENV_ACTIVATE) && \
	cd src && \
	docker start my-redis