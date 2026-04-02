# FlowMind

FlowMind is a full-stack traffic-operations platform for running reinforcement-learning traffic simulations, exporting SUMO-ready networks, and replaying generated SUMO visualization frames through a modern web dashboard.

This submission is fully containerized. Reviewers only need Docker and Docker Compose installed locally. Python, Node.js, SUMO, TraCI, and Xvfb are all packaged inside containers.

## Why This Submission Is Easy To Review

- One command starts the full application
- The database is already included
- SUMO is already included
- The frontend and backend are already wired together
- Generated artifacts and playback frames persist through Docker volumes

## Tech Stack

- Backend: FastAPI, SQLAlchemy, NumPy, SUMO/TraCI
- Frontend: Next.js, React, TanStack Query
- Database: SQLite
- Orchestration: Docker Compose

## Architecture

The Compose stack starts two services:

- `backend`
  - FastAPI API on port `8000`
  - SQLite persistence
  - SUMO, `sumo-gui`, `netconvert`, and Xvfb for SUMO export/playback generation
- `frontend`
  - production Next.js server on port `3000`
  - browser UI for simulation, playback, admin, and reporting workflows

Two named volumes are created automatically:

- `flowmind-data`
- `flowmind-artifacts`

These volumes persist:

- the SQLite database
- generated SUMO XML artifacts
- generated playback outputs between runs

## Database

The database is already handled by Docker Compose.

- No separate PostgreSQL or MySQL installation is required
- The backend uses SQLite by default
- Compose sets `DATABASE_URL=sqlite:////app/data/flowmind.db`
- The actual database file lives inside the `flowmind-data` Docker volume

That means reviewers do not need to install or configure a database manually.

## Quick Start

Start the full stack:

```bash
docker compose up --build
```

Or run it in detached mode:

```bash
docker compose up --build -d
```

Open:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- Backend health check: <http://localhost:8000/api/health>

Stop the stack:

```bash
docker compose down
```

Stop and remove persisted data:

```bash
docker compose down -v
```

## Default Login

The backend seeds a default admin account unless you override it:

- Email: `admin@flowmind.local`
- Password: `change-me-now`

You can also create a local account from the auth page.

## 5-Minute Demo Flow

If a reviewer wants the shortest useful walkthrough, this is the path:

1. Start the stack with `docker compose up --build`.
2. Open `http://localhost:3000`.
3. Sign in with the seeded admin account.
4. Go to `Simulation Lab`.
5. Select a district, controller, and backend.
6. Choose `sumo` as the backend.
7. Run a simulation.
8. Inspect the KPI cards and benchmark panels on the simulation page.
9. Open `Playback`.
10. Play the generated SUMO visualization and inspect the exported files.

## Common Commands

Rebuild after code changes:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up --build -d
```

Inspect running services:

```bash
docker compose ps
```

Stream logs:

```bash
docker compose logs -f
```

Service-specific logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## Environment Overrides

The stack works out of the box, but you can override key values before starting Compose.

Example:

```bash
export ADMIN_EMAIL=admin@example.com
export ADMIN_PASSWORD=super-secret
export SESSION_SECRET=replace-me
export JWT_SECRET=replace-me
export OPENAI_API_KEY=sk-...
export GOOGLE_CLIENT_ID=...
export GOOGLE_CLIENT_SECRET=...
docker compose up --build
```

You can also use the sample environment file:

```bash
cp .env.example .env
docker compose up --build
```

Important defaults:

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`
- `FRONTEND_ORIGIN=http://localhost:3000`

## Reviewer Notes

- The first Docker build is slower because the backend image installs SUMO
- Playback visuals are generated per run, so a fresh SUMO simulation produces fresh frames
- Local account authentication works out of the box
- Google OAuth is optional and only needed if credentials are provided
- AI features are optional and require `OPENAI_API_KEY`

## Documentation

- Run/setup guide: [README.md](/home/tarek/Desktop/projects/RL-Traffic/README.md)
- Full usage guide: [docs/USAGE.md](/home/tarek/Desktop/projects/RL-Traffic/docs/USAGE.md)
- Reviewer demo script: [docs/DEMO.md](/home/tarek/Desktop/projects/RL-Traffic/docs/DEMO.md)

## Key Container Files

- [docker-compose.yml](/home/tarek/Desktop/projects/RL-Traffic/docker-compose.yml)
- [Dockerfile.backend](/home/tarek/Desktop/projects/RL-Traffic/Dockerfile.backend)
- [docker/backend/entrypoint.sh](/home/tarek/Desktop/projects/RL-Traffic/docker/backend/entrypoint.sh)
- [web/Dockerfile](/home/tarek/Desktop/projects/RL-Traffic/web/Dockerfile)
- [.env.example](/home/tarek/Desktop/projects/RL-Traffic/.env.example)

## Validation Status

The containerized stack was validated with:

- `docker compose build frontend backend`
- `docker compose up -d`
- backend health check returning `{"status":"ok"}`
- frontend responding successfully on port `3000`
