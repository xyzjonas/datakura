
[parallel]
default: ci-python ci-js

install:
    uv sync
    cd frontend && npm i

dev:
    uv run manage.py runserver

preview:
    cd frontend && npm run build
    just dev

manage *ARGS:
    uv run manage.py {{ARGS}}

shell:
    uv run manage.py shell

migrate *ARGS:
    uv run manage.py migrate {{ARGS}}

makemigrations:
    uv run manage.py makemigrations

createsuperuser:
    uv run manage.py createsuperuser --skip-checks --username admin --email admin@gmail.com

lint *ARGS:
    uv run ruff check {{ARGS}}

format:
    uv run ruff format

format-check:
    uv run ruff format --check

type-check:
    uv run mypy

test:
    uv run pytest

seed:
    uv run manage.py seed

[working-directory: "frontend"]
ui:
     npm run dev

[working-directory: "frontend"]
openapi-gen:
    npm run openapi-ts

[working-directory: "frontend"]
ui-build:
    npm run build

[working-directory: "frontend"]
test-js:
    npm run test:unit

[working-directory: "frontend"]
eslint:
    npm run lint-check

[working-directory: "frontend"]
ts-check:
    npm run type-check

[parallel]
ci-js: eslint ts-check test-js

[parallel]
ci-python: lint format-check type-check test
