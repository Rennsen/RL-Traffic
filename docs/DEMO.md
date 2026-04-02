# FlowMind Demo Script

This file is a short reviewer script for demonstrating the project quickly and consistently.

## Goal

Show that the application:

- starts in containers
- supports authentication
- runs a traffic simulation
- produces SUMO-backed outputs
- replays generated playback frames in the web UI

## Demo Setup

Start the stack:

```bash
docker compose up --build -d
```

Check services:

```bash
docker compose ps
curl http://localhost:8000/api/health
```

Open:

- Frontend: <http://localhost:3000>
- Backend: <http://localhost:8000>

## Demo Flow

1. Open the auth page and sign in with:
   - `admin@flowmind.local`
   - `change-me-now`
2. Land on the dashboard and point out:
   - district overview
   - alerts
   - AI summary area
3. Open `Simulation Lab`.
4. Choose:
   - any district
   - any RL controller
   - backend = `sumo`
5. Run a simulation.
6. Highlight:
   - wait/queue/throughput metrics
   - RL vs fixed comparison
   - benchmark vs actual panel
7. Open `Playback`.
8. Press play and show:
   - SUMO GUI frame playback
   - step controls
   - generated files
   - XML preview panels
9. Optionally open:
   - `Reports`
   - `Executive`
   - `Admin`

## What To Say

Useful submission summary:

> FlowMind packages the full traffic-simulation workflow into Docker Compose. The reviewer does not need to install Python, Node.js, SUMO, or a database manually. The app supports authenticated traffic simulation runs, SUMO artifact generation, and browser-based playback of generated SUMO frames.

## Reset Between Demos

Stop services:

```bash
docker compose down
```

Reset all persisted state:

```bash
docker compose down -v
```
