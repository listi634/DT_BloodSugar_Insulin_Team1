# Digital Twin Model Summary

## 1. Short Description of the System
The implemented system is a low-order physiological digital twin for
blood glucose and insulin dynamics. It models four coupled continuous
states:
- Plasma glucose concentration in blood
- Effective insulin level
- Carbohydrate pool (meal absorption reservoir)
- Interstitial glucose (the sensor signal for the controller)

The model is integrated in continuous time over fixed simulation steps
using `scipy.integrate.solve_ivp`, with safety bounds applied to
physiological values after each step.

## 2. Purpose of the Model
The model is designed to:
- Reproduce plausible glucose-insulin trends for teaching and analysis
- Support closed-loop insulin automation with a proportional controller
- Allow user disturbances (meal and sport) to alter trajectories
- Provide a compact, explainable baseline architecture for extension

## 3. System Variables

Compact system notation:

$$
\dot{\mathbf{x}} = f(\mathbf{x}, \mathbf{u}, \mathbf{p}, \mathbf{w}),
\qquad
\mathbf{y} = h(\mathbf{x}, \mathbf{u}, \mathbf{p})
$$

### Inputs `u`
Control and known external inputs that influence dynamics:
- `insulin_rate` (controller output, infused insulin rate)
- `meal_carbs` (queued by user and injected into `carb_pool`)
- `sport_multiplier`, `sport_minutes_remaining` (temporary sensitivity
  modulation from user sport events)

### Outputs `y`
Measurable or exposed outputs:
- `glucose` (plasma glucose)
- `insulin`
- `interstitium` (interstitial glucose, the control signal)
- `insulin_rate`
- `time_minutes`
- Optional: `carb_pool`, sport-related values for diagnostics

### Parameters `p`
Slowly changing/constant model parameters (`ModelConfig`):
- `dt_minutes`
- Basal levels: `glucose_basal`, `insulin_basal`
- Dynamics: `glucose_decay`, `insulin_decay`
- Couplings: `insulin_sensitivity`, `insulin_response_gain`
- Meal dynamics: `meal_absorption_rate`, `carb_to_glucose_gain`
- Interstitium dynamics: `interstitium_tau_minutes` (time constant for
  sensor dynamics)
- Safety clamps: `min_glucose`, `max_glucose`, `min_insulin`,
  `max_insulin`

The current calibration uses a deliberately small meal-to-glucose gain
so that a single meal produces a moderate rise instead of driving the
glucose state directly into the safety clamp.

### States `x`
State stores all information needed to predict future behavior:

$$
\mathbf{x} =
\begin{bmatrix}
G \\
I \\
C \\
G_{\mathrm{int}}
\end{bmatrix}
$$

The current implementation also uses internal delayed compartments for
meal absorption and insulin action. These are hidden model states that
help smooth the replay trace while keeping the public simulator interface
compact.

Simulation metadata that also affects future behavior:
- `time_minutes`
- `sport_multiplier`
- `sport_minutes_remaining`
- `insulin_rate` (held over each step until recomputed)

### Disturbances `w`
Uncontrolled or partially controlled effects:
- Meal ingestion timing and amount (user-triggered disturbance)
- Physical activity events (user-triggered sensitivity disturbance)
- Numerical integration error and model mismatch vs. reality

## 4. What Is Influenced, Measured, and Assumed Constant
- Influenced directly: insulin infusion rate, meal/sport event injection
- Measured/exposed: glucose and insulin trajectories plus the
  interstitial estimate used by the controller
- Treated as constant/slowly varying: model parameters in
  `ModelConfig`

## 5. Time Scale and System Type
- Time scale of interest: minutes
- Core dynamics: continuous-time ODEs
- Execution style: sampled-data hybrid loop
  - Continuous physiology integrated over each discrete step `dt_minutes`
  - Discrete events (meal/sport) and control updates at step boundaries

## 6. Subsystems (Implemented Decomposition)
- Physiology subsystem (`PhysiologyModel`): ODE derivatives and bounded
  state propagation
- Controller subsystem (`ProportionalController`): insulin-rate command
  from corrected interstitial glucose with deadband and rate limits
- Estimation subsystem (`ExtendedKalmanFilterEstimator`): finite-
  difference EKF scaffold that corrects interstitial glucose before the
  controller sees it
- Event subsystem (`PendingEvents`): meal/sport buffering and
  deterministic application
- Integration subsystem (`SolveIvPIntegrator`): one-step numerical solve
  with validated solver config

```mermaid
flowchart LR
    U[User Events: Meal / Sport] --> E[Pending Event Application]
    E --> C[Proportional Controller]
    C --> M[Physiology ODE Model]
    M --> I[solve_ivp Integrator]
    I --> S[Next Simulation State]
```

## 7. Model Equations
Let:

$$
\begin{aligned}
G &:= \text{plasma glucose}, \\
I &:= \text{insulin}, \\
C &:= \text{carbohydrate pool}, \\
G_{\mathrm{int}} &:= \text{interstitial glucose (CGM signal)}, \\
u_I &:= \text{commanded insulin rate}, \\
s &:= \text{effective sport sensitivity multiplier},\; s \ge 1
\end{aligned}
$$

Continuous-time dynamics:

$$
\frac{dG}{dt} = -k_g\,(G-G_b) - (S_I\,s)\,\max(0, I-I_b) + k_c\,C
$$

$$
\frac{dI}{dt} = -k_i\,(I-I_b) + k_r\,\max(0, G-G_b) + u_I
$$

$$
\frac{dC}{dt} = -k_a\,C
$$

$$
\frac{dG_{\mathrm{int}}}{dt} = \frac{G - G_{\mathrm{int}}}{\tau}
$$

Hidden internal compartments used by the current implementation:

$$
\frac{dC_{\mathrm{gut}}}{dt} = -k_{\mathrm{gut}}\,C_{\mathrm{gut}}
$$

$$
\frac{dC_{\mathrm{int}}}{dt} = k_{\mathrm{gut}}\,C_{\mathrm{gut}} -
k_{\mathrm{abs}}\,C_{\mathrm{int}}
$$

$$
\frac{dA_I}{dt} = \frac{\max(0, I-I_b) - A_I}{\tau_I}
$$

where the glucose equation consumes the delayed intestinal carbohydrate
pool and the delayed insulin-action term instead of reacting instantly to
the raw insulin state.

with parameter mapping:

$$
\begin{aligned}
k_g &= \texttt{glucose\_decay}, &
k_i &= \texttt{insulin\_decay}, \\
S_I &= \texttt{insulin\_sensitivity}, &
k_r &= \texttt{insulin\_response\_gain}, \\
k_a &= \texttt{meal\_absorption\_rate}, &
k_c &= \texttt{carb\_to\_glucose\_gain}, \\
G_b &= \texttt{glucose\_basal}, &
I_b &= \texttt{insulin\_basal}, \\
\tau &= \texttt{interstitium\_tau\_minutes} &
\end{aligned}
$$

Post-step safety projection:

$$
G \leftarrow \operatorname{clamp}(G, G_{\min}, G_{\max}),
\qquad
I \leftarrow \operatorname{clamp}(I, I_{\min}, I_{\max}),
\qquad
C \leftarrow \max(0, C)
$$

Sport effect decay at step level:

$$
t_{\mathrm{sport}} \leftarrow
\max\bigl(0,\, t_{\mathrm{sport}}-\Delta t\bigr)
$$

If the remaining sport time reaches zero:

$$
s \leftarrow 1.0
$$

## 8. Notes and Limitations
- This is a grey-box educational model, not a clinical-grade patient
  model.
- The EKF scaffold is an intermediate observer layer for simulation and
  validation, not a personalized clinical estimator.
- It intentionally favors robustness and explainability over high-order
  physiological fidelity.
- Meal response is tuned conservatively for benchmark replay; repeated
  meals are expected to accumulate gradually rather than spike the
  system in one step.
- Dataset insulin therapy columns, when present, are replay context or
  diagnostics; they are not the same thing as the model's internal
  insulin state.
- If therapy-aware replay is enabled, dataset insulin values can be used
  as causal exogenous inputs for comparison, but that remains a replay
  convention rather than a change to the physiology state definition.
- The current model deliberately adds delayed absorption and delayed
  insulin action to reduce replay spikes and improve CGM alignment.
