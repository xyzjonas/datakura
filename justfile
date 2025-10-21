
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
