.PHONY: install test lint run clean docker-build

install:
	pip install -e .[dev,full]

test:
	pytest tests/ -v --tb=short

lint:
	ruff check .

run:
	python main.py $(URL)

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf output/ .cache/ build/ dist/ *.egg-info

docker-build:
	docker build -t go-viral-video .

docker-run:
	docker run --rm -v $(PWD)/output:/app/output go-viral-video $(URL)
