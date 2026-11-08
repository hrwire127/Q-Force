"""Export standalone evidence plots from frozen JSON (the deck uses editable marks)."""
from pathlib import Path
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "charts"
OUT.mkdir(exist_ok=True)
data = json.loads((HERE / "source_data/experiments_summary.json").read_text(encoding="utf-8"))
runs = {r["name"]: r for r in data["runs"]}
shots = json.loads((HERE / "source_data/shot_sensitivity.json").read_text(encoding="utf-8"))

plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 13,
                     "figure.facecolor": "#0B1730", "axes.facecolor": "#0B1730",
                     "text.color": "#F7F9FC", "axes.labelcolor": "#F7F9FC",
                     "xtick.color": "#AFC3D5", "ytick.color": "#AFC3D5",
                     "axes.edgecolor": "#29415F", "grid.color": "#29415F"})

fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
seeds = [2026, 2027, 2028]
y = np.arange(3)
a = [runs[f"penalty_0_7_seed_{s}"]["samples"]["ideal"]["p_feasible"] for s in seeds]
b = [runs[f"penalty_4_0_seed_{s}"]["samples"]["ideal"]["p_feasible"] for s in seeds]
ax.barh(y - .18, a, .32, color="#DC725E", label="λ = 0.7")
ax.barh(y + .18, b, .32, color="#62D8CE", label="λ = 4.0")
ax.set_yticks(y, seeds); ax.invert_yaxis(); ax.set_xlim(0, .8)
ax.set_xlabel("P(feasible), 2,048 ideal shots"); ax.set_ylabel("Matched seed")
ax.xaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1))
ax.grid(axis="x", alpha=.6); ax.set_axisbelow(True)
ax.legend(frameon=False, labelcolor="#F7F9FC", loc="lower right")
ax.set_title("Stronger penalty fixes exact-model validity; sampling is mixed", loc="left", pad=20)
fig.savefig(OUT / "penalty_feasibility.png", dpi=200, facecolor=fig.get_facecolor()); plt.close(fig)

fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
for seed, color in zip(seeds, ["#62D8CE", "#F6BB67", "#DC725E"]):
    group = sorted((r for r in shots if r["sampling_seed"] == seed), key=lambda r: r["shots"])
    xs = [r["shots"] for r in group]
    ys = [r["p_feasible"] for r in group]
    low = [r["p_feasible"] - r["p_feasible_wilson95"][0] for r in group]
    high = [r["p_feasible_wilson95"][1] - r["p_feasible"] for r in group]
    ax.errorbar(xs, ys, yerr=[low, high], marker="o", color=color, capsize=4, label=str(seed))
exact = runs["penalty_0_7_seed_2026"]["exact_ideal_statistics"]["p_feasible"]
ax.axhline(exact, color="#F7F9FC", linestyle="--", linewidth=1.5, label="exact trained-state probability")
ax.set_xscale("log", base=2); ax.set_xticks([256, 1024, 2048, 4096]); ax.set_xticklabels(["256", "1,024", "2,048", "4,096"])
ax.set_ylim(.35, .65); ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(xmax=1))
ax.set_xlabel("Shots per repeat"); ax.set_ylabel("P(feasible), Wilson 95% interval")
ax.grid(alpha=.6); ax.legend(frameon=False, labelcolor="#F7F9FC", ncol=2)
ax.set_title("More measurements improve precision, not the trained state", loc="left", pad=20)
fig.savefig(OUT / "shot_precision.png", dpi=200, facecolor=fig.get_facecolor()); plt.close(fig)

fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
ns = [5, 7, 8]
states = [2**n for n in ns]
ax.plot(ns, states, "o-", color="#62D8CE", linewidth=3, markersize=10)
for n, v, cities in zip(ns, states, [5, 7, 7]):
    ax.annotate(f"{v} states\n{cities} cities", (n, v), xytext=(10, -15), textcoords="offset points", color="#F7F9FC")
ax.set_xticks(ns); ax.set_xlabel("Binary route decisions = qubits"); ax.set_ylabel("Possible plans")
ax.set_ylim(0, 300); ax.grid(alpha=.6)
ax.set_title("Route decisions drive state-space growth", loc="left", pad=20)
fig.savefig(OUT / "route_state_growth.png", dpi=200, facecolor=fig.get_facecolor()); plt.close(fig)
print(f"Wrote {len(list(OUT.glob('*.png')))} evidence charts to {OUT}")
