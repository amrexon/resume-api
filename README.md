# CV API

My CV as a live REST API, with an anonymous request dashboard.

**Stack:** Python 3.12, FastAPI, SQLite, Docker

## Run locally
```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000 (dashboard) and http://localhost:8000/docs (auto-generated API docs).

## Run with Docker
```bash
docker build -t cv-api .
docker run -p 8000:8000 -v cvdata:/data -e VISITOR_SALT=some-long-random-string cv-api
```

## Endpoints
`/api/profile`, `/api/skills`, `/api/experience`, `/api/education`, `/api/certificates`, `/api/projects`, `/api/cv`, `/api/status`, `/api/stats`

## How it works
- CV content lives in `app/data/cv.json`; each endpoint returns one section.
- A middleware logs every `/api/` request (path, status, response time) to SQLite.
- Visitors are anonymized: a salted hash that changes daily. No IP addresses are stored.
- `/api/stats` aggregates the log for the dashboard (requests per hour, average response time, unique visitors).
