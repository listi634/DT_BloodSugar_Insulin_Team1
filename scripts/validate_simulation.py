import json, numpy as np
from pathlib import Path
p = Path("logs/U004_2024-09-03_00-00-00_to_2024-09-04_23-59-59_replay.jsonl")
meas, sim = [], []
for line in p.read_text().splitlines():
    rec = json.loads(line)
    if rec.get("type")=="step":
        mg = rec.get("measured_glucose_mmol_l")
        inter = rec["simulation_state"].get("interstitium")
        if mg is not None and inter is not None:
            meas.append(mg); sim.append(inter)
meas = np.array(meas); sim = np.array(sim)
err = sim - meas
rmse = np.sqrt((err**2).mean())
mae = np.abs(err).mean()
mard = (np.abs(err)/meas).mean()*100
# lag via xcorr
xc = np.correlate(sim - sim.mean(), meas - meas.mean(), mode="full")
lag = xc.argmax() - (len(meas)-1)
print("RMSE", rmse, "MAE", mae, "MARD%", mard, "lag[min]", lag)