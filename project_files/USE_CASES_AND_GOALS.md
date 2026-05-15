# Use Cases and High-Level Goals

Version: 1.1
Last Updated: 2026-05-14

Purpose
-------
This document captures the canonical, high-level use cases and goals for
the Digital Twin for Blood Sugar and Insulin project. It is intentionally
non-prescriptive: implementation details, parameter choices, integration
strategies, and numerical bounds are left open for research and iteration.

Keep this file up-to-date whenever the project scope, user-facing
workflows, or model assumptions change. Future coding agents and reviewers
must consult this document before implementing features that affect the
simulation behavior or user experience.

Primary persona
---------------
- Diabetes patient or researcher wearing a CGM sensor and interested in
  predicting and understanding glucose responses to meals and activity.

High-level goal
---------------
Provide a realistic, easy-to-run digital twin that (1) reproduces measured
interstitial glucose time series when operating on a replayed GlucoBench
window, and (2) when a meal event arrives, can optionally run a short-term
free-run prediction without ingesting additional benchmark data.

Virtual & physical entities
---------------------------
- Physical: Human subject with CGM (interstitial glucose) and event
  logging (meals). Units: mg/dL (primary) and mmol/L (supported).
- Virtual: Low-order grey-box compartmental model (E-DES style) representing
  stomach/intestine, plasma glucose & insulin, and interstitium. The model
  uses a two-compartment meal absorption path and is a tool for state
  estimation (insulin inference), short-term prediction, and replay-based
  validation.

Primary use-cases
------------------
1. Replay / Validation run
   - Load recorded CGM time series and associated meal events.
   - Run estimator to infer unobserved states (e.g., insulin) and compare
     simulated interstitial glucose with recorded CGM traces.
   - Use metrics (RMSE, MAE, oscillation counts, hypoglycemia/
     hyperglycemia detection) for evaluation.

2. Meal-triggered prediction
   - When a meal event is reached during replay, pause the simulation and
     allow the user to continue or run a short-term prediction.
   - The prediction runs forward without ingesting new benchmark data and
     leaves a background overlay for comparison.

3. Developer / Offline analysis
   - Use the model to generate reproducible scenarios for testing,
     controller tuning, and sensitivity analysis.

Data & events
-------------
- Expected inputs: CGM time series (timestamp, glucose), event rows for
  meals (timestamp, carbs), and recorded insulin bolus entries when
  available (timestamp, bolus units).
- Reference datasets are kept in the `data/` folder and should be used as
  canonical examples.

Acceptance criteria (high-level)
--------------------------------
- The project must provide replayed GlucoBench runs and meal-triggered
  prediction overlays via the GUI and CLI.
- Deterministic loop order must be preserved: apply events → controller →
  integrate → save history.
- The simulator must expose a reproducible example scenario (small CSV
  snippet) that can act as a golden test for future changes.
- Phase 1 validation should remain reproducible through the generated
  validation windows and metrics artifacts in `project_files/phase1_results`.

Developer rules
---------------
- Consult this file before making feature or API changes that affect the
  simulation's semantics or user-facing flows.
- When model structure, event formats, or UX flows change, update:
  - `project_files/model_summary.md`
  - `project_files/simulation_summary.md`
  - `project_files/USE_CASES_AND_GOALS.md`
- Keep the use-case document high-level — avoid hardcoding numerical
  implementation choices here.

Safety & privacy
-----------------
- This project is a research tool and not a medical device. All
  recommendations are advisory and must carry a clear disclaimer in the
  UI.
- Treat CGM traces and timestamps as sensitive data; follow institutional
  policies for PHI if present.

Change log & ownership
----------------------
- Owner: Project maintainers
- 2026-05-03: Created initial high-level use-case and goals document.
