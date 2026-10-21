"""CV API: my CV as a REST API, with request logging and a live dashboard."""
import datetime as dt
import hashlib
import json
import os
import sqlite3
import time
from contextlib import closing
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

BASE = Path(__file__).parent
DB_PATH = os.environ.get("DB_PATH", str(BASE / "data" / "requests.db"))
SALT = os.environ.get("VISITOR_SALT", "change-me")
# CV content per language: English is the default, German is optional via ?lang=de
CV = {
    "en": json.loads((BASE / "data" / "cv.json").read_text(encoding="utf-8")),
    "de": json.loads((BASE / "data" / "cv.de.json").read_text(encoding="utf-8")),
}
# Both language files must have the same sections, or the API would answer differently per language
assert set(CV["en"]) == set(CV["de"]), "cv.json and cv.de.json must have the same sections"
Lang = Literal["en", "de"]
LANG_HELP = "Language of the content: en (English, default) or de (German)"
STARTED = time.time()

app = FastAPI(
    title="Rexon Elebe – CV API",
    description="My CV as a live REST API. Visitors are counted anonymously (hashed, no IP addresses stored).",
    version="1.0.0",
)


def db():
    return closing(sqlite3.connect(DB_PATH))


def init_db():
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with db() as con:
        con.execute(
            "CREATE TABLE IF NOT EXISTS requests ("
            "id INTEGER PRIMARY KEY, ts TEXT, path TEXT, status INTEGER, ms REAL, visitor TEXT)"
        )
        con.commit()


init_db()


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    path = request.url.path
    if path.startswith("/api/") and path != "/api/stats":
        ms = (time.perf_counter() - start) * 1000
        # Anonymous visitor id: salted hash that changes every day, raw IP is never stored
        ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "")
        ip = ip.split(",")[0].strip()
        ua = request.headers.get("user-agent", "")
        visitor = hashlib.sha256(f"{SALT}{dt.date.today()}{ip}{ua}".encode()).hexdigest()[:12]
        with db() as con:
            con.execute(
                "INSERT INTO requests (ts, path, status, ms, visitor) VALUES (?,?,?,?,?)",
                (dt.datetime.utcnow().isoformat(timespec="seconds"), path[:100], response.status_code, round(ms, 1), visitor),
            )
            con.commit()
    return response


def _register(name: str):
    def handler(lang: Lang = Query("en", description=LANG_HELP)):
        return CV[lang][name]
    app.get(f"/api/{name}", tags=["CV"], summary=f"Get {name}", name=name)(handler)


for _name in ["profile", "skills", "experience", "education", "certificates", "projects"]:
    _register(_name)


@app.get("/api/cv", tags=["CV"], summary="Get the whole CV")
def full_cv(lang: Lang = Query("en", description=LANG_HELP)):
    return CV[lang]


@app.get("/api/status", tags=["System"], summary="Health check")
def status():
    with db() as con:
        con.execute("SELECT 1")
    return {"status": "ok", "database": "connected", "uptime_seconds": int(time.time() - STARTED), "version": app.version}


@app.get("/api/stats", tags=["System"], summary="Anonymous usage statistics")
def stats():
    now = dt.datetime.utcnow()
    day_ago = (now - dt.timedelta(hours=24)).isoformat(timespec="seconds")
    week_ago = (now - dt.timedelta(days=7)).isoformat(timespec="seconds")
    with db() as con:
        total = con.execute("SELECT COUNT(*) FROM requests").fetchone()[0]
        last_24h = con.execute("SELECT COUNT(*) FROM requests WHERE ts >= ?", (day_ago,)).fetchone()[0]
        avg_ms = con.execute("SELECT AVG(ms) FROM requests WHERE ts >= ?", (day_ago,)).fetchone()[0] or 0
        visitors = con.execute("SELECT COUNT(DISTINCT visitor) FROM requests WHERE ts >= ?", (week_ago,)).fetchone()[0]
        rows = con.execute("SELECT ts FROM requests WHERE ts >= ?", (day_ago,)).fetchall()
        recent = con.execute("SELECT ts, path, status, ms FROM requests ORDER BY id DESC LIMIT 8").fetchall()
    hourly = [0] * 24
    for (ts,) in rows:
        age_h = int((now - dt.datetime.fromisoformat(ts)).total_seconds() // 3600)
        if 0 <= age_h < 24:
            hourly[23 - age_h] += 1
    return {
        "total": total,
        "last_24h": last_24h,
        "avg_ms": round(avg_ms, 1),
        "visitors_7d": visitors,
        "uptime_seconds": int(time.time() - STARTED),
        "hourly": hourly,
        "recent": [{"ts": r[0], "path": r[1], "status": r[2], "ms": r[3]} for r in recent],
    }


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(BASE / "static" / "index.html")


@app.get("/impressum", include_in_schema=False)
def impressum():
    return FileResponse(BASE / "static" / "impressum.html")


app.mount("/static", StaticFiles(directory=BASE / "static"), name="static")
