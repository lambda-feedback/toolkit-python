all: build test

build:
	poetry build

publish:
	poetry publish --repository lf_toolkit

test:
	poetry run pytest --cov=lf_toolkit --cov-report=xml --cov-report=term tests/

export:
	poetry export -f requirements.txt -o requirements.txt

clean_build:
	rm -rf dist/
	rm -rf build/

clean: clean_build

fresh: clean
	rm -rf .venv/

generate-mued-types:
	MUED_SPEC_VERSION=$(MUED_SPEC_VERSION) MUED_SPEC_URL=$(MUED_SPEC_URL) poetry run python scripts/generate_mued_types.py
