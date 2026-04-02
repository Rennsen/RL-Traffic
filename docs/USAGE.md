# FlowMind Usage Guide

This guide assumes the app is already running through Docker Compose.

## URLs

- Frontend: <http://localhost:3000>
- Backend API: <http://localhost:8000>
- Health check: <http://localhost:8000/api/health>

## First Login

Use the seeded admin account unless you changed it in Compose:

- Email: `admin@flowmind.local`
- Password: `change-me-now`

You can also create a local account from the auth page.

## Main Workflow

1. Open the dashboard at `http://localhost:3000`.
2. Sign in.
3. Use the district selector in the top bar to switch between traffic districts.
4. Open `Simulation Lab` to configure and run experiments.
5. Choose:
   - a district
   - a controller algorithm
   - `sumo` as backend if you want SUMO exports and playback snapshots
6. Run the simulation.
7. Review KPIs, comparisons, and district metrics.
8. Open `Playback` to inspect the generated SUMO visualization frames.

## Key Pages

### Dashboard

Use this page for a high-level operational summary:

- latest runs
- district health
- recent improvements
- quick access to simulations and playback

### Simulation Lab

Use this page to configure runs:

- district selection
- RL algorithm selection
- backend mode (`internal` or `sumo`)
- traffic pattern
- episode/step counts
- RL hyperparameters
- emergency and service-rate settings

If you want SUMO artifacts and playback visuals, always select the `sumo` backend before starting the run.

### Playback

Use this page to view generated SUMO frames:

- play and pause the simulation
- scrub through frames
- inspect vehicle flow and step metrics
- review generated SUMO XML previews and downloadable files

If playback looks unchanged after a new code change, run a fresh SUMO simulation so new snapshots are generated.

### Admin / Reports / Executive Views

These pages expose:

- run approvals
- audit and activity trails
- leaderboard and team metrics
- reports and benchmarks

## Generated Data

The backend writes persistent data to Docker volumes:

- SQLite database
- SUMO artifacts
- generated playback frames

SUMO artifacts include files such as:

- `nodes.xml`
- `edges.xml`
- `connections.xml`
- `routes.xml`

## Optional AI Features

If you provide `OPENAI_API_KEY` when running Compose, the AI summary/chat routes in the frontend can be used. Without that key, the core traffic simulation product still works normally.

## Resetting Data

To clear all persisted app state:

```bash
docker compose down -v
```

This removes the database volume and artifact volume.
