# FlowMind

FlowMind is a traffic-operations platform for running reinforcement-learning traffic simulations, exporting SUMO networks, and replaying generated SUMO visualization frames through a Next.js dashboard.

The project is fully containerized. Reviewers only need Docker and Docker Compose installed locally. Python, Node.js, SUMO, and Xvfb are all provided inside the containers.

## Stack

- Backend: FastAPI + SQLAlchemy + NumPy + SUMO/TraCI
- Frontend: Next.js + React + TanStack Query
- Persistence: SQLite in a Docker volume
- Orchestration: Docker Compose

## Quick Start

Run the full application:

```bash
docker compose up --build
```

Open:

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- Backend health: <http://localhost:8000/api/health>

Stop the stack:

```bash
docker compose down
```

Stop and remove all persisted data:

```bash
docker compose down -v
```

## Default Login

The backend seeds an admin user automatically unless you override the values in Compose:

- Email: `admin@flowmind.local`
- Password: `change-me-now`

## What Docker Handles

The Compose stack starts two services:

- `backend`
  - FastAPI API
  - SQLite persistence
  - SUMO, `sumo-gui`, `netconvert`, and Xvfb for SUMO playback generation
- `frontend`
  - production Next.js server
  - browser UI on port `3000`

Two named volumes are created:

- `flowmind-data`
- `flowmind-artifacts`

Those volumes persist the database and generated SUMO outputs between runs.

## Database

The database is already included in the Docker setup.

- No separate PostgreSQL or MySQL installation is required
- The backend uses SQLite by default
- Compose stores it at `sqlite:////app/data/flowmind.db`
- The actual database file lives inside the `flowmind-data` Docker volume

That means reviewers only need Docker and Docker Compose. The application database is created automatically when the backend starts.

## Common Commands

Rebuild after code changes:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up --build -d
```

See logs:

```bash
docker compose logs -f
```

See logs for one service:

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## Environment Overrides

The stack works out of the box, but you can override key values with shell environment variables before starting Compose.

Useful overrides:

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

You can also copy the sample environment file and edit values there:

```bash
cp .env.example .env
docker compose up --build
```

Default browser-facing API URL:

- `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

Default frontend origin expected by the backend:

- `FRONTEND_ORIGIN=http://localhost:3000`

## Project Files Added For Containerization

- [Dockerfile.backend](/home/tarek/Desktop/projects/RL-Traffic/Dockerfile.backend)
- [docker-compose.yml](/home/tarek/Desktop/projects/RL-Traffic/docker-compose.yml)
- [docker/backend/entrypoint.sh](/home/tarek/Desktop/projects/RL-Traffic/docker/backend/entrypoint.sh)
- [.env.example](/home/tarek/Desktop/projects/RL-Traffic/.env.example)
- [web/Dockerfile](/home/tarek/Desktop/projects/RL-Traffic/web/Dockerfile)
- [docs/USAGE.md](/home/tarek/Desktop/projects/RL-Traffic/docs/USAGE.md)

## How To Use The App

The shortest flow is:

1. Start the stack with `docker compose up --build`.
2. Open `http://localhost:3000`.
3. Sign in with the default admin account.
4. Go to `Simulation Lab`.
5. Choose a district, algorithm, and backend.
6. Select `sumo` if you want SUMO exports and playback frames.
7. Run a simulation.
8. Open `Playback` to inspect the generated SUMO visualization.

For the full walkthrough, see [docs/USAGE.md](/home/tarek/Desktop/projects/RL-Traffic/docs/USAGE.md).

## Notes

- The first Docker build takes longer because it installs SUMO into the backend image.
- SUMO playback visuals are regenerated per run, so UI styling changes require a fresh SUMO simulation.
- Local account authentication works out of the box. Google OAuth is optional.
