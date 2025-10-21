
default:
    just ci-python
    just ci-js

install:
    uv sync
    cd frontend && npm i

dev:
    uv run manage.py runserver

[working-directory: "frontend"]
ui:
     npm run dev

manage *ARGS:
    uv run manage.py {{ARGS}}

shell:
    uv run manage.py shell

migrate *ARGS:
    uv run manage.py migrate {{ARGS}}

test:
    uv run pytest

[working-directory: "frontend"]
test-js:
    npm run test:unit

[working-directory: "frontend"]
eslint:
    npm run lint-check

[working-directory: "frontend"]
ts-check:
    npm run type-check

[working-directory: "frontend"]
ci-js:
    just eslint
    just ts-check
    just test-js

lint *ARGS:
    uv run ruff check

format:
    uv run ruff format

format-check:
    uv run ruff format --check

type-check:
    uv run mypy


ci-python:
    just lint
    just format-check
    just type-check
    just test
