"""Export manuscript figures from formal results with recorded provenance."""
from pathlib import Path
import json
import runpy
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "figures"
OUT.mkdir(exist_ok=True)

def read(relative):
    return json.loads((ROOT / relative).read_text())

def record(relative, pointer, units):
    value = read(relative)
    for token in pointer.split("/")[1:]:
        token = token.replace("~1", "/").replace("~0", "~")
        value = value[int(token)] if isinstance(value, list) else value[token]
    return {"source": relative, "json_pointer": pointer, "value": value, "units": units}

data = {"source_contrasts": [], "update_layers": []}
for label, relative, pointer, interval in [
    ("Stieger 62: other", "experiments/feedback_retention_v3/results/eeg/analysis.json",
     "/cohorts/stieger62/paired_contrasts/other_minus_own/all/future_ba", "conditional_interval"),
    ("Stieger 62: mixed", "experiments/feedback_retention_v3/results/eeg/analysis.json",
     "/cohorts/stieger62/paired_contrasts/mixed_minus_own/all/future_ba", "conditional_interval"),
    ("Farabbi 12: other", "experiments/confirmation_prior_constraints_v4/results/confirmation/analysis.json",
     "/comparisons/other_minus_own/future_ba", "interval"),
    ("Farabbi 12: mixed", "experiments/confirmation_prior_constraints_v4/results/confirmation/analysis.json",
     "/comparisons/mixed_minus_own/future_ba", "interval"),
]:
    item = record(relative, pointer, "balanced-accuracy proportion; multiply by 100 for percentage points")
    item.update(label=label, interval_key=interval)
    data["source_contrasts"].append(item)

relative = "experiments/reliability_budget_v1/analysis/dynamics/analysis.json"
for condition in ["observable__A_abrupt", "observable__C_abrupt"]:
    for method in ["state_only", "state_A", "state_C"]:
        item = record(relative, f"/rows/{condition}/{method}__periodic/pre_full_mse/mean", "full-state mean squared error")
        item.update(condition=condition, method=method)
        data["update_layers"].append(item)

plt.rcParams.update({"font.size": 10, "font.family": "DejaVu Sans", "pdf.fonttype": 42,
                     "axes.spines.top": False, "axes.spines.right": False})
fig, ax = plt.subplots(figsize=(6.6, 3.8), layout="constrained")
x = np.arange(3)
for offset, condition, label, color in [
    (-.19, "observable__A_abrupt", "Abrupt dynamics change", "#397ca8"),
    (.19, "observable__C_abrupt", "Abrupt observation-map change", "#df943a"),
]:
    values = [e["value"] for e in data["update_layers"] if e["condition"] == condition]
    ax.bar(x+offset, values, width=.36, label=label, color=color)
ax.set(xticks=x, xticklabels=["State", "State + A", "State + C"], ylim=(0, 1.55),
       xlabel="Allowed update", ylabel="Mean full-state squared error")
ax.legend(loc="lower left", bbox_to_anchor=(0, 1.02), frameon=False, fontsize=9)
ax.grid(axis="y", color="0.9")
ax.set_axisbelow(True)
for extension in ["pdf", "png"]:
    fig.savefig(OUT / f"update_layers.{extension}", dpi=220)
plt.close(fig)
(OUT / "figure_data.json").write_text(json.dumps(data, indent=2)+"\n")
print("Exported the update-location figure and aggregate source provenance.")

if __name__ == "__main__":
    for name in ("figure_assets_eeg.py", "figure_assets_retention.py", "figure_assets_dynamics.py", "figure_assets_source.py",
                 "reviewer_revision/generate_lee_primary_figure.py"):
        runpy.run_path(str(Path(__file__).resolve().parent / name), run_name="__main__")
