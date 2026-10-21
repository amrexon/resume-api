# CV API

My CV as a live REST API, with an anonymous request dashboard.

**Live:** https://rexelebe.de · **API docs:** https://rexelebe.de/docs

**Stack:** Python 3.12, FastAPI, SQLite, Docker, Caddy (automatic HTTPS), Ubuntu 26.04 on a Hetzner Cloud server

## Architecture

```
Browser ──HTTPS──▶ Caddy (TLS via Let's Encrypt, ports 80/443)
                      │
                      ▼
                 FastAPI app (port 8000, internal only)
                      │
                      ▼
                 SQLite (Docker volume)
```

- **Caddy** terminates HTTPS, renews certificates automatically and redirects `www` and plain HTTP to `https://rexelebe.de`.
- **FastAPI** serves the CV endpoints in English and German (`cv.json`, `cv.de.json`), the dashboard and auto-generated API docs.
- **SQLite** stores an anonymous request log in a Docker volume, so stats survive restarts and redeploys.
- A **Hetzner Cloud firewall** only allows SSH (22), HTTP (80) and HTTPS (443).

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /api/profile` | Name, summary, languages |
| `GET /api/skills` | Technical skills |
| `GET /api/experience` | Work experience |
| `GET /api/education` | Education |
| `GET /api/certificates` | Certificates |
| `GET /api/projects` | Projects |
| `GET /api/cv` | Everything at once |
| `GET /api/status` | Health check |
| `GET /api/stats` | Anonymous usage statistics |

All CV endpoints accept an optional `lang` parameter: English is the default, `?lang=de` returns German. The dashboard has an EN/DE switch, and `https://rexelebe.de/?lang=de` opens it in German.

Try it: `curl https://rexelebe.de/api/skills` or `curl https://rexelebe.de/api/skills?lang=de`

## Privacy

No IP addresses are stored. Visitors are counted with a salted hash that changes every day, and no cookies are set.

## Run locally

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Open http://localhost:8000 (dashboard) and http://localhost:8000/docs (API docs).

## Deploy (server)

```bash
git clone https://github.com/amrexon/resume-api.git && cd resume-api
docker volume create cvdata
echo "VISITOR_SALT=$(openssl rand -hex 32)" > .env
docker compose up -d --build
```
To update after a change: `git pull && docker compose up -d --build`
