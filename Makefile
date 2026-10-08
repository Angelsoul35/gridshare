.PHONY: install compile test lint run demo clean

install:
	pip install -e ".[dev]"

compile:
	python -m gridshare.chain.compile

test:
	pytest --cov=gridshare --cov-report=term-missing

lint:
	ruff check gridshare tests

run:
	uvicorn gridshare.main:app --reload --port 8000

demo:
	python -m gridshare.cli demo

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
