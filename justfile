# list recipes
default:
    @just --list

# run the dev server with reload
dev:
    uv run fastapi dev

# run the server
run:
    uv run fastapi run

# run tests, extra args go to pytest
test *args:
    uv run pytest {{ args }}

# check lint, formatting, and types
lint:
    uv run ruff check
    uv run ruff format --check
    uv run ty check

# fix lint and format
fix:
    uv run ruff check --fix
    uv run ruff format

# lint and test, same as ci
check: lint test
