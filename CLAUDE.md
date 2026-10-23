<!--
  Copyright 2026 Alokin LLC
  SPDX-License-Identifier: FCL-1.0-ALv2
-->
# Faraflow — Developer Guide

Faraflow is a visual studio and workflow engine for AI agents. It grew out of the open-source PySpur project: a SvelteKit frontend (replacing PySpur's Next.js one) on a Python/FastAPI backend. The Python package is still named `pyspur`.

## Repository Layout

```
faraflow/
├── backend/              # Python/FastAPI backend (pyspur package)
│   ├── pyspur/
│   │   ├── api/          # FastAPI route handlers
│   │   ├── models/       # SQLAlchemy ORM models + Alembic migrations
│   │   ├── nodes/        # Node type implementations (one file per node)
│   │   ├── execution/    # Workflow execution engine
│   │   └── schemas/      # Pydantic schemas
│   ├── pyproject.toml
│   └── entrypoint.sh     # Runs alembic upgrade then uvicorn
├── frontend/             # SvelteKit frontend (active development)
│   ├── src/
│   │   ├── lib/
│   │   │   ├── actions/      # Svelte action/state modules (.svelte.ts)
│   │   │   ├── components/   # Reusable Svelte components
│   │   │   ├── stores/       # Svelte stores
│   │   │   ├── types/        # TypeScript type definitions
│   │   │   └── utils/        # Utility functions
│   │   └── routes/           # SvelteKit file-based routes
├── docker-compose.yml        # Production (pre-built images)
├── docker-compose.dev.yml    # Development (builds locally + hot reload)
├── Dockerfile.backend
├── Dockerfile.frontend
└── nginx/                    # Nginx reverse proxy config
```

## Development: Running the Stack

### Docker (recommended)

```bash
# Copy env file and edit as needed
cp .env.example .env

# Start all services with hot reload
docker compose -f docker-compose.dev.yml up --build
```

Services started:
| Service    | Internal port | Exposed via nginx at |
|------------|--------------|----------------------|
| `backend`  | 8000         | `localhost:6080/api` |
| `frontend` | 3000 (vite)  | `localhost:6080`     |
| `db`       | 5432         | `localhost:54321`    |
| `nginx`    | 80           | `localhost:6080`     |

The backend mounts the repo root at `/pyspur` — Python changes reload automatically (uvicorn `--reload`). Frontend changes hot-reload via Vite.

### Local (no Docker)

Do not run anything on the local machine. Always run all npm, pip, uv commands within the respective docker container, using docker-compose or docker commands.

## Useful Commands

### Frontend
Do not run anything on the local machine. Always run all npm, pip, uv commands within the respective docker container, using docker-compose or docker commands.

```bash
npm run dev          # Dev server with HMR
npm run build        # Production build (output: build/)
npm run check        # svelte-check type checking
npm run lint         # ESLint
npm run format       # Prettier
```

### Backend

Do not run anything on the local machine. Always run all npm, pip, uv commands within the respective docker container, using docker-compose or docker commands.

```bash
# Run tests
cd backend && pytest

# Lint / format
ruff check pyspur/
ruff format pyspur/
```

### Database Migrations
```bash
# Generate a new migration after changing SQLAlchemy models
./generate_migrations.sh <seq_number> <short_description_snake_case>
# e.g.: ./generate_migrations.sh 003 add_run_tags

# Apply migrations (also runs automatically on backend startup)
cd backend && alembic upgrade head

# Blow away local dev DB (safe if no production data)
docker volume rm <compose-project>_postgres_data   # e.g. faraflow_postgres_data
```

## Key Docker Compose Shortcuts (devcontainer)

These aliases are set up inside the devcontainer:

| Alias    | Command                               |
|----------|---------------------------------------|
| `dcup`   | `docker compose up`                   |
| `dlogs`  | tail all container logs (last 5 min)  |
| `dlogb`  | tail backend logs only                |
| `dlogf`  | tail frontend logs only               |
| `dlogn`  | tail nginx logs only                  |

## Architecture Notes

- **Frontend ↔ Backend**: The frontend calls the backend REST API at `/api/*`. In dev, nginx proxies `/api` → `backend:8000` and `/` → `frontend:3000`.
- **State management**: Svelte 5 runes + `.svelte.ts` action files (see `src/lib/actions/`). Prefer runes (`$state`, `$derived`, `$effect`) over legacy stores.
- **Node system**: Each AI node type is a single Python file in `backend/pyspur/nodes/`. Adding a new node type means adding one file there — no other registration needed.
- **Workflow execution**: Async task-based engine in `backend/pyspur/execution/`. Workflows run as background tasks; the frontend polls for status.
- **DB**: PostgreSQL in production/dev Docker; SQLite supported for quick local runs via `pyspur serve --sqlite`.

## Environment Variables

Key variables in `.env` (copy from `.env.example`):

| Variable          | Default       | Purpose                          |
|-------------------|--------------|----------------------------------|
| `PYSPUR_PORT`     | `6080`        | Exposed port for the whole app   |
| `ENVIRONMENT`     | `production`  | Set to `development` for dev builds |
| `DATABASE_URL`    | (postgres)    | Postgres connection string       |

Add LLM provider API keys in the app UI under **Settings → API Keys**, or directly in `.env`.
