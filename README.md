# DATAKURA

"Data" + kura (倉, storehouse)

Datakura is a warehouse management system for day-to-day internal operations. It combines a Django + Django Ninja backend with a Vue 3 + Quasar frontend and covers products, customers, inbound and outbound orders, invoices, credit notes, warehouse flows, and inventory snapshots.

## Stack

- Backend: Django, Django Ninja, SQLite for local development, `uv` for Python environment and commands
- Frontend: Vue 3, TypeScript, Quasar, UnoCSS, Vite
- API client generation: `@hey-api/openapi-ts`
- Task runner: `just`

## What It Does

Datakura is built for warehouse and back-office workflows. Main areas in current app:

- product catalog and pricing
- customers and customer groups
- inbound and outbound orders
- warehouse inbound and outbound handling
- invoice and credit note processing
- inventory snapshots and analytics
- printer and packaging-related operations

## Requirements

- Python with `uv` installed
- Node.js `^20.19.0 || >=22.12.0`
- npm
- `just`

## Setup

Install backend and frontend dependencies:

```bash
just install
```

This wraps:

```bash
uv sync
cd frontend && npm i
```

## Development

Run backend dev server:

```bash
just dev
```

Run frontend dev server in another terminal:

```bash
just ui
```

Default local addresses:

- backend app and API: `http://localhost:8000`
- frontend Vite dev server: `http://localhost:5173` if default Vite port is free

API routes live under:

```text
/api/v1/
```

OpenAPI schema used for client generation:

```text
http://localhost:8000/api/v1/openapi.json
```

## Common How-Tos

### Run Local CI Checks

Run full repo checks the same way CI does:

```bash
just
```

This runs Python and frontend validation in parallel.

### Preview Production-like App

Build frontend and run backend with Gunicorn:

```bash
just preview
```

### Generate OpenAPI Client

Start backend first so schema is available, then regenerate frontend client:

```bash
just dev
# in another terminal
just openapi-gen
```

Generation config lives in `frontend/openapi-ts.config.ts` and points to:

```ts
input: "http://localhost:8000/api/v1/openapi.json";
output: "src/client";
plugins: ["@hey-api/sdk", "@hey-api/client-fetch", "@hey-api/typescript"];
```

Generated files are written to `frontend/src/client`.

## Hey API SDK Usage

Generated SDK exports are re-exported from `frontend/src/client/index.ts`, so most frontend code can import from `@/client`.

Example:

```ts
import { warehouseApiRoutesWarehouseGetWarehouses } from "@/client";

const response = await warehouseApiRoutesWarehouseGetWarehouses();

if (response.data) {
  console.log(response.data);
}
```

The shared generated client is configured in `frontend/src/App.vue` with repo-specific headers such as `X-CSRFToken`:

```ts
import { client } from "./client/client.gen";

client.setConfig({
  headers: {
    "X-CSRFToken": csrfToken ?? "not-set",
  },
});
```

Use that pattern when request behavior should be global. Use generated SDK functions from `@/client` for endpoint calls instead of hand-writing fetch calls.

## Project Layout

```text
apps/warehouse/        Django app with domain logic, API routes, tests, templates
conf/                  Django settings and URL configuration
frontend/              Vue application, generated API client, unit and e2e tests
docs/                  business and domain notes
media/                 local uploaded/generated files
```

## Notes

- Use `just` as main entrypoint for day-to-day work.
- Keep backend server running before regenerating OpenAPI client.
- Prefer generated SDK calls from `frontend/src/client` over ad-hoc API wrappers.
