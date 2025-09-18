.PHONY: venv install test lint

venv:
	python -m venv .venv

install: venv
	. .venv/bin/activate && pip install -U pip && pip install -e . && pip install -r requirements.txt

test:
	. .venv/bin/activate && pytest

lint:
	. .venv/bin/activate && black src tests && flake8 src tests
