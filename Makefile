init:
	uv venv
	source .venv/bin/activate

install:
	uv pip install -r requirements.txt

installdev:
	uv pip install -r requirements-dev.txt

run:
	python -m piggy.interactive

# Format code with Black
format:
	black piggy/ tests/

# Lint code with Ruff
lint:
	ruff check piggy/ tests/

# Auto-fix linting issues
autolint:
	ruff check --fix piggy/ tests/

# Install pre-commit hooks (one-time setup)
installprecommit:
	pre-commit install

# Run all pre-commit hooks manually
runprecommit:
	pre-commit run --all-files