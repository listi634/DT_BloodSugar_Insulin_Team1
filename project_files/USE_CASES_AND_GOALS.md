# Use Cases and Project Intent — The project's "soul"

Version: 1.2
Last updated: 2026-05-16

This document expresses why the project exists, who benefits from it,
and what a user should expect to gain. It frames the application as an
engineering and educational tool: an accessible, reproducible surrogate
for exploring glucose–insulin interactions and conservative control
behaviour, not a clinical diagnostic system.

Core proposition
----------------
The project lets clinicians, researchers and informed users take a CGM
trace, replay it in a deterministic digital twin, and run short,
conservative forecasts when an event occurs. The app's value is in
explainability, repeatability, and safe intuition-building about how
meals and insulin influence short-term glucose trends.

Primary personas
----------------
- Diabetes researcher validating model ideas or controller concepts.
- Educator demonstrating effects of meals/insulin in a classroom.
- Power user (patient or coach) exploring scenarios for intuition and
  debugging (not for direct treatment decisions).

Representative use-cases (concise)
----------------------------------
1) Validation & replay: load a GlucoBench window, run the estimator,
   and compare simulated interstitial glucose to reference CGM. Produce
   JSONL logs and metric results for reproducibility.

2) Meal-triggered conservative forecast: when a meal is encountered in
   a replay, pause and offer a short open-loop prediction overlay so the
   user can inspect possible near-term trajectories.

3) Standalone what‑if: from any live state, apply a planned meal and an
   optional bolus, then run a conservative forecast to inspect trend
   direction and timing (again: not treatment advice).

4) Developer harness: generate reproducible scenarios (CSV/JSONL) for
   automated tests and controller tuning experiments.

What the project delivers (results)
-----------------------------------
- Deterministic replay aligned to benchmark CGM windows (tunable
  estimator).
- Short-horizon forecast overlays and numeric comparison metrics
  (RMSE, MAE, MARD, peak-time error) for scenario evaluation.
- Structured artifacts (JSONL logs, CSV summaries, PNGs) to enable
  offline analysis and continuous integration tests.

Hard limits and explicit non-goals
---------------------------------
- This is not a patient‑specific model: personalization is out-of-scope
  for V1.
- It is not a medical device and must not be used for dosing
  recommendations. UI and documentation must present this disclaimer.
- The model uses simplified insulin and meal kinetics with linear action
  terms; it will not capture complex physiology such as multi-phase
  insulin sensitivity changes or meal composition effects.

Ethical and privacy considerations
---------------------------------
- Mark all outputs as educational only and require an explicit
  disclaimer in the GUI and README.
- Treat CGM and event logs as sensitive: the repository contains only
  anonymized benchmark windows; users must follow institutional policies
  for personal data.

Success criteria (how we judge good outcomes)
--------------------------------------------
- Reproducible validation: the repository can replay at least one
  canonical GlucoBench window and produce the same JSONL/CSV summary
  artifacts across runs.
- Conservative forecasts provide useful qualitative guidance on trend
  direction and timing without making overconfident claims.
- The codebase is approachable: a new developer can run verification,
  run a replay, and inspect generated logs within 30 minutes.

Future directions (short list)
-----------------------------
- Add optional personalization (parameter identification) with clear
  safety guards.
- Extend the estimator into a full state-and-parameter filter for
  research experiments.
- Add secure storage and anonymized sharing for collaborative
  validation studies.

---

Owner: project maintainers

