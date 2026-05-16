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
- Diabetes patient, coach, or researcher who already has CGM traces and
  wants to replay them, validate a lightweight model, and explore
  conservative what-if scenarios after meals or activity.

High-level goal
---------------
Provide a realistic, easy-to-run CGM replay tool that (1) aligns with
measured interstitial glucose time series during GlucoBench validation
runs, and (2) when an event occurs, can optionally launch a short,
conservative free-run prediction without ingesting new benchmark data.

Virtual & physical entities
---------------------------
- Physical: Human subject with CGM (interstitial glucose) and event
  logging (meals, optional bolus records). Units: mg/dL (primary) and
  mmol/L (supported).
- Virtual: Low-order grey-box compartmental model representing
  stomach/intestine, glucose, insulin, and interstitium. The model is a
  replay-and-forecast surrogate, not a clinically validated physiology
  simulator.

Primary use-cases
------------------
1. Replay / Validation run
   - Load recorded CGM time series and associated meal / bolus events.
   - Run the estimator to infer latent states and compare simulated
     interstitial glucose against the recorded CGM trace.
   - Use metrics such as RMSE, MAE, oscillation counts, and hypo-/
     hyperglycemia detection to judge replay quality.
   - Write an AI-friendly JSONL replay log with simulated plasma glucose,
     interstitium, insulin, and the measured benchmark values used in the
     validation window so the run can be analyzed later.

2. Meal-triggered prediction
   - When a meal event is reached during replay, pause the simulation and
     allow the user to continue or launch a short-term prediction.
   - The prediction runs forward without ingesting further benchmark data
     and leaves a background overlay for visual comparison.
   - After the prediction window completes, show a compact summary with
     RMSE, MARD, and peak-time error against the reference glucose data.

3. Standalone what-if prediction
   - Let the user run a short open-loop forecast from the current state
     without requiring a replay meal event.
   - Accept planned meal carbohydrates and an optional bolus so the user
     can inspect a conservative future trajectory.

4. Conservative what-if analysis
   - Let the user test small meal or bolus changes and inspect the trend
     direction rather than interpret the output as a clinical dose
     recommendation.
   - Keep the scenario intentionally conservative so the app is useful
     for intuition building, parameter sensitivity checks, and model
     debugging.

4. Developer / Offline analysis
   - Use the model to generate reproducible scenarios for testing,
     controller tuning, and sensitivity analysis.

Data & events
-------------
- Expected inputs: CGM time series (timestamp, glucose), event rows for
  meals (timestamp, carbs), and recorded insulin bolus entries when
  available (timestamp, bolus units).
- Reference datasets are kept in the `data/` folder and should be used as
  canonical examples.
- The benchmark data should be treated as replay/validation material, not
  as proof that every meal has a large immediate glucose spike.

Acceptance criteria (high-level)
--------------------------------
- The project must provide replayed GlucoBench runs and meal-triggered
  prediction overlays and a standalone prediction control via the GUI
  and CLI.
- Deterministic loop order must be preserved: apply events → controller →
  integrate → save history.
- The simulator must expose a reproducible example scenario (small CSV
  snippet) that can act as a golden test for future changes.
- Phase 1 validation should remain reproducible through the generated
  validation windows and metrics artifacts in `project_files/phase1_results`.

Success for the project means the app can explain and replay CGM behavior
well enough to support comparison, sensitivity analysis, and cautious
future prediction. It does not need to promise clinical-grade meal
physiology.

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
- Insulin and meal inputs should be framed as scenario inputs for replay
  and what-if analysis, not as prescriptive treatment advice.
- Treat CGM traces and timestamps as sensitive data; follow institutional
  policies for PHI if present.

Change log & ownership
----------------------
- Owner: Project maintainers
- 2026-05-03: Created initial high-level use-case and goals document.
