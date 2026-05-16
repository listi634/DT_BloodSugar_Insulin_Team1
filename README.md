# DT_BloodSugar_Insulin_Team1 — Project Manual

This repository contains a compact, explainable digital twin for
glucose–insulin dynamics used for CGM replay, conservative short-horizon
prediction, and validation experiments. The codebase is organized for
developer clarity and verification-first workflows.

Supported Python: 3.13

---

## Quick start

Installation (recommended virtual environment):

```bash
pipenv install --dev
pipenv shell
```

Run the GUI application:

```bash
python -m src.main
```

Run verification (must pass before commits):

PowerShell:
```powershell
.\scripts\verify.ps1
```

POSIX (bash):
```bash
python scripts/verify.py
```

Run tests:

```bash
pytest tests/ -v --tb=short
```

---

## What this project contains (concise)

- Core model & simulation: `src/core/` (model, simulator, controller,
    integrator, state containers).
- GUI: `src/gui/` (CustomTkinter app, plot frame, control panel).
- Tools and verification: `scripts/` (formatting, linting, tests runner).
- Data: `data/` (benchmark CGM windows used for validation).
- Documentation: `project_files/` (model & simulation summaries,
    use-cases, validation artifacts).

---

## Files and responsibilities

- `src/core/model.py` — compartmental ODE model, unit conversions and
    safety clamps.
- `src/core/simulator.py` — deterministic step loop, event application,
    estimator and controller orchestration.
- `src/core/controller.py` — conservative proportional controller with
    deadband and rate limiting.
- `src/core/integrator.py` — helper wrapper around `scipy.integrate`.
- `src/core/state.py` — typed containers for SimulationState and
    SimulationSnapshot.
- `src/gui/app.py` — application bootstrap and main window.
- `src/gui/plot_frame.py` — Matplotlib embedding and live history
    visualization.
- `src/gui/control_panel.py` — user controls: queue meal, queue bolus,
    set basal, start/stop.
- `scripts/verify.py|.ps1|.bat` — run `black`, `pylint`, `mypy`, `pytest`.

See doc files in `project_files/` for model and simulation technical
descriptions:

- `project_files/model_summary.md` — equations, units, controller,
    estimator, limits.
- `project_files/simulation_summary.md` — runtime loop, modes, artifacts.
- `project_files/USE_CASES_AND_GOALS.md` — high-level intent, personas,
    limits, and acceptance criteria.

---

## Running common tasks

Start GUI (development):
```bash
python -m src.main
```

Run a single-step simulation from a script (example):
```python
from src.core.simulator import GlucoseSimulator
sim = GlucoseSimulator()
snapshot = sim.step()
print(snapshot.time_minutes, snapshot.glucose)
```

Run validation replay (example CLI flow):
1. Preload a window from `data/` via the GUI.
2. Start replay and choose prediction when prompted.
3. After run, see JSONL and CSV artifacts under
         `project_files/validation_logs/`.

## Utility scripts (analysis & tuning)

This repository includes a few convenience scripts useful for
analysis, parameter tuning, and baseline statistics. They are
developer-oriented and intended to be run from the repository root.

- `scripts/tune_parameters.py` — Grid-search tuning of model and
    estimator parameters against one or more GlucoBench validation
    windows. Use this to explore how small changes to
    `ModelConfig`/`EstimatorConfig` affect replay error and to produce a
    candidate parameter set for further manual inspection.

    Example usage:

    ```bash
    # Run default quick sweep over bundled example windows
    python scripts/tune_parameters.py

    # Tune against a specific window (user U001, 2024-09-01 to 2024-09-09)
    python scripts/tune_parameters.py --window U001 2024-09-01 2024-09-09

    # Override parameter grid on the command line
    python scripts/tune_parameters.py --parameter model.glucose_decay=0.01,0.015,0.02
    ```

    When to use: after you have replay logs or want to calibrate the
    default behavior on a representative validation window. The script
    replays the selected windows, computes prediction metrics, and prints
    the best-scoring candidate. Use results as a starting point —
    manual inspection and safety checks are recommended before reusing
    tuned values.

- `scripts/compute_user_stats.py` — Compute per-user baseline
    statistics (median glucose, percentiles, average meals/insulin) from
    the bundled GlucoBench CSV. It writes `project_files/user_baselines.csv`.

    Usage:

    ```bash
    python scripts/compute_user_stats.py
    ```

    When to use: to generate quick summary baselines for each user in the
    dataset, for example to seed `glucose_basal` values or to guide
    profile selection when preloading validation windows.

---

## Verification and contribution workflow

All contributors must run the verification pipeline before committing:

1. Format with Black and isort (automatic in `scripts/verify`).
2. Lint with `pylint` and fix issues flagged by the project's rules.
3. Type-check with `mypy` (project uses strict mode).
4. Run unit tests with `pytest`.

Use the provided scripts to avoid local tooling mismatch:

```powershell
.\scripts\verify.ps1
```

---

## Data and privacy

- Benchmark data (GlucoBench windows) live in `data/`. They are used
    as validation examples only and must be handled according to local
    privacy rules if replaced with real PHI.

## Extending the project

- To add personalization: implement a parameter-identification module
    that updates `ModelConfig` and provide clear unit tests and safety
    checks.
- To add a new estimator: subclass `ExtendedKalmanFilterEstimator` and
    keep the same `predict/update` interface used by `GlucoseSimulator`.

---

## Troubleshooting

- If `black` is missing: install dev dependencies via `pipenv
    install --dev`.
- If `pytest` fails after a change: run the failing test directly to
    obtain a focused traceback.

---

## Contact and ownership

Owner: project maintainers (see repo contributors). Use issues and PRs
for changes; include verification output in PR descriptions.

---

Last updated: 2026-05-16

