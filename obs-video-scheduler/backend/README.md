# OBS Video Scheduler backend (FastAPI)

A lightweight replacement for the legacy servlet/Thrift stack. Provides RESTful endpoints for managing items, schedules, contest timing, and OBS control via obs-websocket.

## Running locally

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Docker

```bash
cd backend
docker build -t obs-video-scheduler .
docker run --rm -p 8000:8000 -e OBS_SCHEDULER_OBS_PASSWORD=secret obs-video-scheduler
```

Configuration is driven by environment variables with the prefix `OBS_SCHEDULER_` (for example `OBS_SCHEDULER_DATABASE_URL`).
