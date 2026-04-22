# Flight Price Harvester

Full-stack flight price collection app built with FastAPI, PostgreSQL, React, and SerpAPI Google Flights.

It supports:

- JWT authentication and role-based access control
- Scheduled and manual scraping
- Per-user route groups and price history
- Excel export
- Docker-based local environments
- Unit, service, and E2E test coverage

## Stack

- Backend: FastAPI, SQLAlchemy async, Alembic, APScheduler
- Frontend: React, TypeScript, Vite, React Query
- Database: PostgreSQL
- Scraper provider: SerpAPI Google Flights
- Testing: Pytest, Vitest, Playwright

## Project Layout

```text
flight-harvester/
├─ backend/
│  ├─ app/
│  ├─ alembic/
│  ├─ tests/
│  ├─ Dockerfile
│  └─ pyproject.toml
├─ frontend/
│  ├─ src/
│  ├─ e2e/
│  ├─ Dockerfile
│  └─ package.json
├─ docker-compose.yml
└─ Makefile
```

## Quick Start With Docker

1. Copy the backend env file.

```bash
cd flight-harvester
cp backend/.env.example backend/.env
```

2. Edit `backend/.env` and set at least:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flight_harvester
JWT_SECRET_KEY=<generate-with-openssl-rand-hex-32>
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=<strong-password>
SERPAPI_KEY=<your-serpapi-key>
DEMO_MODE=false
```

3. Start the stack.

```bash
docker compose up --build
```

4. Open the app at [http://localhost](http://localhost).

The backend health endpoints are:

- `GET /health`
- `GET /health/live`
- `GET /health/ready`

## Local Development

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
python -m alembic upgrade head
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Frontend dev server: [http://localhost:5173](http://localhost:5173)

Backend API: [http://localhost:8000](http://localhost:8000)

## Environment Variables

Core backend settings:

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | Yes | Must use `postgresql+asyncpg://...` |
| `JWT_SECRET_KEY` | Yes | Minimum 32 chars |
| `ADMIN_EMAIL` | Yes | Default admin account |
| `ADMIN_PASSWORD` | Yes | Minimum 12 chars |
| `CORS_ORIGINS` | Yes | Comma-separated or JSON list of explicit origins |
| `ALLOWED_HOSTS` | No | Host allow-list for trusted host middleware |
| `SERPAPI_KEY` | Yes in production | Leave empty only for demo mode |
| `SERPAPI_DEEP_SEARCH` | No | `true` for exact Google Flights prices |
| `DEMO_MODE` | No | Keep `false` in production |
| `SCHEDULER_ENABLED` | No | Enables APScheduler collection |
| `SCHEDULER_INTERVAL_MINUTES` | No | Full collection cadence |
| `SCRAPE_BATCH_SIZE` | No | Requests per collection batch |
| `SCRAPE_DELAY_SECONDS` | No | Delay between route batches |
| `PROVIDER_TIMEOUT_SECONDS` | No | Per-request timeout |
| `PROVIDER_MAX_RETRIES` | No | Retry attempts for SerpAPI |
| `PROVIDER_CONCURRENCY_LIMIT` | No | Concurrent SerpAPI requests |
| `PROVIDER_MIN_DELAY_SECONDS` | No | Minimum spacing between SerpAPI requests |
| `LOGIN_RATE_LIMIT_ATTEMPTS` | No | Failed login attempts allowed per window |
| `LOGIN_RATE_LIMIT_WINDOW_SECONDS` | No | Login rate-limit window |
| `SCRAPE_RATE_LIMIT_ATTEMPTS` | No | Manual scrape trigger attempts allowed per window |
| `SCRAPE_RATE_LIMIT_WINDOW_SECONDS` | No | Scrape trigger rate-limit window |
| `SENTRY_DSN` | No | Optional error reporting |
| `TELEGRAM_BOT_TOKEN` | No | Optional job notifications |
| `TELEGRAM_CHAT_ID` | No | Optional job notifications |

Frontend settings:

| Variable | Required | Notes |
|---|---|---|
| `VITE_API_BASE_URL` | No | Use `http://localhost:8000` in local dev; leave empty in Docker |

## Security Notes

The current build includes:

- strict secret handling via `.env` and ignore rules for `.env.*`
- JWT secret and admin password validation
- trusted host middleware and explicit CORS validation
- redacted logging for tokens, API keys, passwords, and DB URLs
- login rate limiting
- scrape trigger rate limiting
- owner-scoped access for prices, logs, and route groups
- request IDs on responses and server errors
- public liveness/readiness endpoints
- safer Docker defaults and removal of hardcoded remote credentials

## Testing

### Backend

Unit and service tests:

```bash
cd backend
.venv\Scripts\python.exe -m pytest tests\test_airline_codes.py tests\test_auth_schema.py tests\test_config.py tests\test_route_group_schema.py tests\test_services
```

Integration tests require a reachable PostgreSQL instance:

```bash
set DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/flight_data_scrapper_test
.venv\Scripts\python.exe -m pytest tests\integration
```

### Frontend

Unit tests:

```bash
cd frontend
npm run test:run
```

E2E tests:

```bash
cd frontend
npm run e2e
```

## Dependency Audits

Backend:

```bash
cd backend
.venv\Scripts\python.exe -m pip_audit
```

Frontend:

```bash
cd frontend
npm audit --omit=dev --registry=https://registry.npmjs.org
```

## Common Commands

```bash
make dev
make down
make test
make lint
make migrate
make revision msg="describe change"
```

## Production Notes

- Set `DEMO_MODE=false`.
- Use a managed PostgreSQL database with TLS enabled.
- Set `CORS_ORIGINS` and `ALLOWED_HOSTS` to real production domains.
- Keep `SERPAPI_KEY` only in your runtime secret manager.
- Do not expose the database directly to the public internet.
- Use `/health/ready` for platform readiness checks.
- Run the frontend behind the provided nginx proxy or another reverse proxy that forwards `X-Forwarded-*` headers.

## Suggested Hosting

- Easiest all-in-one: Railway for backend + Postgres, Vercel or Cloudflare Pages for frontend.
- More control: Render or Fly.io for backend, managed Postgres from Neon/Supabase/Railway.
- Lowest-friction CI/CD: GitHub Actions for tests/audits, deploy on merge to main.

Recommended CI/CD steps:

1. Run backend unit tests.
2. Run backend integration tests against a PostgreSQL service container.
3. Run frontend `npm run test:run`.
4. Run Playwright E2E with mocked APIs.
5. Run `pip_audit` and `npm audit --omit=dev`.
6. Build backend and frontend Docker images before deployment.
