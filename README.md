# Content Moderation Pipeline

Users submit content, an automated engine flags it with written reasoning, high-confidence
cases are decided automatically, and everything ambiguous is routed to a human moderator.

v1 domain: job board postings. Full design and rationale: [docs/PLAN.md](docs/PLAN.md).

## Stack

Django + DRF, React (Vite + TS), Celery, Redis, PostgreSQL. See `docker-compose.yml` under
`infra/` for how the pieces fit together.

## Running locally with Docker (recommended)

```
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

- Backend: http://localhost:8000 (health check at `/healthz/`)
- Frontend: http://localhost:5173
- Django admin: http://localhost:8000/admin/ (create a superuser first, see below)

Create a superuser once the stack is up:

```
docker compose -f infra/docker-compose.yml exec backend python manage.py createsuperuser
```

## Running without Docker

Requires a local PostgreSQL and Redis instance; point `.env` at them.

Backend:

```
cd backend
python -m venv .venv
.venv/Scripts/activate   # .venv/bin/activate on macOS/Linux
pip install -r requirements/dev.txt
python manage.py migrate
python manage.py runserver
```

Celery worker (separate terminal, same venv):

```
celery -A config worker -l info
```

Frontend:

```
cd frontend
npm install
npm run dev
```

## Tests

```
cd backend && pytest
cd frontend && npm run build && npm run lint && npm run test
```

## Repository layout

```
backend/   Django project (config/, apps/, ml/, tests/)
frontend/  React app (src/api, components, pages, hooks, types)
infra/     Docker Compose and Dockerfiles
docs/      Project plan
```

## Status

All 7 phases in the plan are complete. See [docs/PLAN.md](docs/PLAN.md)'s status table for
what each phase delivered.
