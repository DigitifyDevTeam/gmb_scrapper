# LeadForge AI

B2B prospecting platform that discovers local businesses from Google Maps and detects whether they have a valid website.

**MVP scope ends at the Website Detection Engine.** Future modules (AI site generation, CRM, payments, etc.) are documented in `backend/app/core/roadmap.py` only.

## Architecture

```
Frontend (React + Vite + TypeScript + Tailwind)
        ↓
FastAPI Backend
        ↓
Playwright Google Maps Scraper
        ↓
Normalization Service
        ↓
Website Detection Engine
        ↓
MySQL Database
```

## Prerequisites

**Docker (recommended):** Docker Desktop only.

**Local development:** Docker Desktop (MySQL), Python 3.12+, Node.js 20+.

## Quick Start (Docker)

Run the full stack (MySQL + API + frontend):

```bash
docker compose up -d --build
```

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:8080 |
| API docs | http://localhost:8000/docs |
| MySQL (host) | `localhost:3307` |

Migrations run automatically on backend startup. Stop with `docker compose down` (add `-v` to wipe the database volume).

## Quick Start (Local development)

### 1. Start MySQL only

```bash
docker compose up -d mysql
```

### 2. Backend setup

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

### 3. Frontend setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Dashboard: http://localhost:5173

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/health` | Health check |
| POST | `/api/v1/searches` | Create search job |
| GET | `/api/v1/searches` | List searches |
| GET | `/api/v1/searches/{id}` | Get search |
| POST | `/api/v1/scraping/start` | Start scraping |
| GET | `/api/v1/scraping/status/{job_id}` | Job status |
| GET | `/api/v1/prospects` | List prospects (filters: city, category, has_website, website_reason) |
| GET | `/api/v1/prospects/stats` | Dashboard stats |
| GET | `/api/v1/prospects/{id}` | Get prospect |

## Website Detection Rules

A business is marked **without website** when:

1. Website field is empty (`no_url`)
2. URL is a social profile only (`social_only`)
3. Homepage returns HTTP 4xx/5xx (`under_construction`)
4. Homepage is a short placeholder page with maintenance / coming-soon markers (`under_construction`)

Otherwise: `valid` → `has_website=true`

Timeouts and connection errors on the homepage check are treated as **`valid`** (`has_website=true`) — the site may simply block automated requests.

## What Gets Stored

- **No website** → full GMB profile saved (address, phone, reviews, Maps link, customer testimonials, etc.) for outreach.
- **Has a website** → only the business name, website flag, reason, and Maps URL are saved so future bulk runs skip them as duplicates.

The Prospects page defaults to businesses **without** a website. Bulk scrape targets count saved **leads** (no website), not minimal dedupe stubs.

## Project Structure

```
backend/app/
  api/          # FastAPI routes
  core/         # Config, logging, roadmap
  database/     # SQLAlchemy session
  models/       # ORM models
  schemas/      # Pydantic schemas
  repositories/ # Data access layer
  services/     # Business logic
  scraper/      # Playwright + website detector
  workers/      # Async job runner

frontend/src/
  api/          # Axios + React Query hooks
  components/   # Reusable UI
  features/     # Feature modules
  pages/        # Dashboard, Search, Prospects
  layouts/      # App shell
```

## Notes

- Scraping uses Playwright against Google Maps. Respect rate limits and Terms of Service.
- Background jobs run in-process via asyncio (`workers/job_runner.py`). Swap for Celery/ARQ when scaling.
- Supports 10,000+ prospects via indexed queries and server-side pagination.
