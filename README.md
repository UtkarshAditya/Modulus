# Modulus

A plug-and-play content moderation pipeline: users submit content, an automated engine flags it
with written reasoning, high-confidence cases are decided automatically, and everything ambiguous
is routed to a human moderator. Public site and self-service signup live at `/`; job board
postings is the first live surface, with more use cases queued behind the same engine.

v1 domain: job board postings. Full design and rationale: [docs/PLAN.md](docs/PLAN.md). Marketing
site design and layout: [docs/MODULUS_WEBSITE.md](docs/MODULUS_WEBSITE.md).

## Stack

Django + DRF, React (Vite + TS), Celery, Redis, PostgreSQL. See `docker-compose.yml` under
`infra/` for how the pieces fit together.

## Running locally with Docker (recommended)

```
cp .env.example .env
docker compose -f infra/docker-compose.yml up --build
```

- Backend: http://localhost:8000 (health check at `/healthz/`)
- Frontend: http://localhost:5173 — public landing/signup/login at `/`, the submitter portal at
  `/postings` and moderator console at `/moderation` behind auth
- Celery monitoring (Flower): http://localhost:5555 (basic auth via `FLOWER_BASIC_AUTH` in `.env`)
- Django admin: http://localhost:8000/admin/ (create a superuser first, see below)

Sign up for an employer account directly through the running frontend at `/signup`, or seed demo
accounts for all three roles (`demo_employer` / `demo_moderator` / `demo_admin`, password
`password123!`):

```
docker compose -f infra/docker-compose.yml exec backend python manage.py seed_demo
```

Create a superuser (for Django admin access) once the stack is up:

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
frontend/  React app — public site (pages/landing, styles/modulus.css) and the
           authenticated submitter/moderator app (components, pages, hooks, types)
infra/     Docker Compose and Dockerfiles
docs/      Project plan and the Modulus site design notes
```

## Status

All 7 phases in the plan are complete (see [docs/PLAN.md](docs/PLAN.md)'s status table for what
each phase delivered), plus a post-plan pass adding the public Modulus site, self-service signup,
and an auth-gated path from the marketing page into the real submitter portal — see
[docs/MODULUS_WEBSITE.md](docs/MODULUS_WEBSITE.md).
