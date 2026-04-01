# FlowMind: Adaptive Traffic Signal Optimization with Reinforcement Learning

FlowMind is a Smart City prototype that uses reinforcement learning (RL) to optimize traffic signal behavior at a simulated intersection. The application includes:

- A Q-learning based adaptive signal controller.
- Deep RL options including DQN and PPO.
- A fixed-timer baseline controller.
- Dynamic traffic demand scenarios (rush hours, event spikes, random flows).
- Emergency vehicle modeling with priority-sensitive rewards.
- SUMO-ready network export with backend status visibility.
- In-app SUMO network viewer with downloadable generated XML files.
- Optional live SUMO runtime execution (when `sumo`, `netconvert`, `traci`, and `sumolib` are installed).
- A multi-district web dashboard for training, evaluation, live map playback, and management benchmarking.

## Why This Project Matters

Traditional traffic lights rely on fixed plans that fail under volatile demand. FlowMind demonstrates how an RL agent can adapt in real time and improve outcomes such as:

- Lower average waiting time
- Lower queue lengths
- Higher throughput
- Better emergency handling

## Tech Stack

- Backend: FastAPI + Python
- RL/Simulation: NumPy + custom traffic environment
- Frontend: HTML/CSS/JavaScript + Chart.js

## Project Structure

```text
app/
  main.py              # FastAPI entry point
  models.py            # Request schema
  config.py            # Constants and patterns
  agent.py             # Q-learning, DQN, and PPO agents
  simulation.py        # Environment and demand generation
  sumo.py              # SUMO-ready export and backend status
  service.py           # Training and evaluation pipeline
  templates/
    index.html         # Dashboard page
  static/
    styles.css         # UI styling
    app.js             # Frontend behavior and charts
requirements.txt
README.md
```

## Setup and Run

1. Create a virtual environment (recommended).
1. Install dependencies:

```bash
pip install -r requirements.txt
```

1. Start the app:

```bash
uvicorn app.main:app --reload
```

1. Open:

- <http://127.0.0.1:8000>

## Dashboard Capabilities

The web UI lets you configure and run experiments with:

- District-level sections with ownership and default operating parameters
- RL training episodes and horizon length
- Traffic demand profile
- Fixed baseline cycle
- Service rate and emergency arrival rate
- RL hyperparameters
- Optional real-world benchmark metric overrides

After each run, it shows:

- KPI cards with relative RL improvements
- Time-series charts (queue, throughput, training rewards)
- District flow playback map (roads, intersections, cars, phase over time)
- Detailed metric comparison table (RL vs fixed)
- Benchmark table (RL/fixed versus actual flow)
- District management console showing owner responsibility and latest gains

When `backend` is set to `sumo`, FlowMind now writes full SUMO XML files to:

- `artifacts/sumo/<district_id>/<run_id>/`
  - `<district_id>.nodes.xml`
  - `<district_id>.edges.xml`
  - `<district_id>.connections.xml`
  - `<district_id>.rou.xml`

## API Endpoints

- `GET /` Dashboard page
- `GET /api/health` Health check
- `GET /api/districts` District catalog with layout and ownership metadata
- `GET /api/sumo/status` SUMO availability / export mode status
- `POST /api/run` Run an experiment and return metrics + series

Example request body:

```json
{
  "district_id": "downtown_core",
  "backend": "sumo",
  "algorithm": "ppo",
  "episodes": 260,
  "steps_per_episode": 240,
  "traffic_pattern": "rush_hour_ns",
  "fixed_cycle": 18,
  "service_rate": 3,
  "emergency_rate": 0.02,
  "learning_rate": 0.12,
  "discount_factor": 0.95,
  "epsilon_decay": 0.992,
  "seed": 42,
  "actual_avg_wait": 55.0,
  "actual_avg_queue": 250.0,
  "actual_throughput": 1160.0,
  "actual_emergency_avg_wait": 10.5,
  "actual_clearance_ratio": 0.7
}
```

## Notes and Next Iterations

This prototype now includes multi-intersection district layouts, Tabular Q-learning, DQN, PPO, and connected SUMO-ready network export artifacts.

Current next-stage priorities:

- Live SUMO runtime stepping via TraCI when SUMO is installed
- Persisting generated SUMO files (`nodes`, `edges`, `connections`, `routes`) to a downloadable run package
- Scenario calibration with real detector traces and corridor-level constraints
- Priority corridor and transit-signal-priority policies for emergency and bus fleets
