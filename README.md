# I-Magnus Exams

I-Magnus Exams is a server-rendered EdTech platform for online exam preparation. It powers student learning journeys across course subscriptions, recorded video lectures, live classes, PDF notes, test series, scholarship tests, payments, and an internal administration dashboard.

The application is built with FastAPI, Jinja2 templates, PostgreSQL, Redis, Celery, and a custom Bootstrap-based UI layer. It is designed for a production education platform where reliability, clear student workflows, and a polished user experience matter.

## Project Scope

This repository contains the main web application and supporting API modules for:

- Student authentication, registration, dashboard, subscriptions, lecture access, notes, live classes, doubts, and test attempts.
- Admin workflows for courses, categories, lectures, study material, subscriptions, orders, students, scholarship tests, live classes, and current affairs.
- Public course and study-material pages.
- Payment/order flows with Razorpay integration points.
- Background processing for video-related tasks through Celery.
- PostgreSQL-backed data models managed through Tortoise ORM and Aerich.
- Deployment configuration for Docker, Render, and Kubernetes-style environments.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Web framework | FastAPI / Starlette |
| Templates | Jinja2 |
| Database | PostgreSQL |
| ORM | Tortoise ORM, SQLAlchemy utilities |
| Migrations | Aerich |
| Cache / queue | Redis |
| Background jobs | Celery |
| Payments | Razorpay |
| Storage / media integrations | AWS S3, Bunny, ImageKit, Vimeo |
| Frontend | Bootstrap, vanilla CSS, vanilla JS, jQuery |
| Server | Uvicorn / Hypercorn |
| Containerization | Docker, Docker Compose |

## Repository Layout

```text
.
|-- main.py                     # FastAPI application entrypoint
|-- config.py                   # Tortoise ORM configuration
|-- configs/                    # Runtime settings and database URL helpers
|-- admin_dashboard/            # Admin web views, APIs, and models
|-- student/                    # Student web views, APIs, and models
|-- courses/                    # Public/student course pages and course flows
|-- study_material/             # Notes, study material, and test-series flows
|-- scholarship_tests/          # Scholarship test web and API flows
|-- checkout/                   # Payment and order APIs
|-- screen_banners/             # Banner/content APIs
|-- send_mails/                 # Email helpers and routes
|-- aws_services/               # AWS/S3 integration helpers
|-- static/                     # Static assets and refreshed UI styles
|-- Dockerfile                  # Production container image
|-- docker-compose.yml          # Local app + Postgres + Redis stack
|-- render.yaml                 # Render deployment blueprint
|-- pyproject.toml              # Aerich configuration
|-- requirements.txt            # Python dependencies
`-- .env.example                # Environment variable template
```

## Getting Started

### Prerequisites

- Python 3.12+
- PostgreSQL 14+ or a managed PostgreSQL provider
- Redis 7+
- FFmpeg, if you are running video-processing workflows locally
- Docker and Docker Compose, if using the containerized setup

### Environment Setup

Create a local environment file from the public template:

```bash
cp .env.example .env
```

Fill in the required database, security, Redis, mail, payment, and media-provider values. Do not commit `.env` or any production credentials.

At minimum, local development requires:

- `SECRET_KEY`
- `DB_CONNECTION`
- `DB_HOST`
- `DB_PORT`
- `DB_DATABASE`
- `DB_USERNAME`
- `DB_PASSWORD`
- `DB_SSLMODE` when required by the database provider
- `REDIS_URL` or local Redis/Celery broker settings

### Run Locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The application will be available at:

```text
http://localhost:8000
```

Useful browser routes include:

- `GET /` - public landing/student entry flow
- `GET /student/login/` - student login
- `GET /student/registration/` - student registration
- `GET /student/dashboard/` - student dashboard entry
- `GET /administrator/login/` - admin login
- `GET /admin/` - admin dashboard
- `GET /student/courses/` - course listing

### Run with Docker Compose

Docker Compose starts the application, PostgreSQL, Redis, and a Celery worker:

```bash
docker compose up --build
```

Default local service ports:

- App: `http://localhost:8000`
- PostgreSQL: `localhost:5434`
- Redis: `localhost:6379`

### Background Worker

When running without Docker Compose, start the worker separately if you need Celery-backed jobs:

```bash
celery -A worker.celery worker --loglevel=info
```

## Database and Migrations

The application uses Tortoise ORM. The Aerich configuration is in `pyproject.toml`, and the ORM settings are loaded from `config.py`.

Common migration command:

```bash
aerich upgrade
```

Make sure the database environment variables are loaded before running migrations or starting the application.

## Deployment

The repository includes:

- `Dockerfile` for a production-oriented Python 3.12 image.
- `docker-compose.yml` for local multi-service development.
- `render.yaml` for Render blueprint deployment.
- `deployment.yaml` for Kubernetes-style deployment references.

Production deployments should provide secrets through the platform secret manager, not committed files.

## Security Notes

This is a public repository. Treat all credentials as external runtime configuration.

- Keep `.env`, production dumps, logs, and private keys out of git.
- Use `.env.example` as the only committed environment reference.
- Rotate any credential that has ever been committed or shared publicly.
- Restrict public browser keys, such as Firebase config, in their provider dashboards.
- Review payment, webhook, storage, and admin routes before enabling them in a new environment.
- The repository includes a GitHub Actions Gitleaks workflow for secret scanning.

## UI System

The student-facing UI uses a custom design refresh under `static/ui_refresh/`, built on top of Bootstrap and server-rendered Jinja2 templates. The theme supports light and dark modes through the `data-theme` attribute and `theme-controller.js`.

When changing UI, keep styles in the existing CSS files and avoid inline styles unless they are required for server-rendered dynamic values.

## Development Guidelines

- Prefer small, focused changes with clear template/CSS/API boundaries.
- Keep secrets and generated local files out of commits.
- Test student-facing flows in both desktop and mobile widths.
- Verify dark mode for dashboard and auth pages.
- Run the relevant API, template, or migration checks before deployment.

## License

No open-source license has been added yet. Until a license is provided, all rights are reserved by the repository owner.
