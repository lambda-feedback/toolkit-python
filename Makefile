all: build test

build:
	poetry build

publish:
	poetry publish --repository lf_toolkit

test:
	poetry run pytest --cov=lf_toolkit --cov-report=xml --cov-report=term tests/

clean_build:
	rm -rf dist/
	rm -rf build/

clean: clean_build

fresh: clean
	rm -rf .venv/
