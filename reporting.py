"""Exports derived only from a completed experiment snapshot."""
from __future__ import annotations
from html import escape
from io import BytesIO

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages


def html_report(result):
    c, q, m, s = result["classical"], result["quantum"], result["qubo_minimum"], result["statistics"]
    rows = "".join(f"<tr><td>{escape(r['cities'][0])} – {escape(r['cities'][1])}</td><td>{r['cost']}</td><td>{r['value']}</td></tr>" for r in result["routes"])
    return f"""<!doctype html><meta charset=utf-8><title>Quantum Railways report</title>
<style>body{{font:16px system-ui;max-width:900px;margin:32px auto}}table{{border-collapse:collapse}}td,th{{border:1px solid #ccc;padding:7px}}.warn{{color:#a22}}</style>
<h1>Quantum Railways — experiment report</h1><p>Simulated locally; no hardware credentials or tokens are included.</p>
<h2>Configuration</h2><pre>{escape(str(result['config']))}</pre><h2>Routes</h2><table><tr><th>Route</th><th>Cost</th><th>Score</th></tr>{rows}</table>
<h2>Results</h2><ul><li>Exact classical: score {c['punctaj_total']}, cost {c['cost_total']}, bits {c['vector_binar']}</li>
<li>QUBO minimum: score {m['valoare_totala']}, cost {m['cost_total']}, energy {m['energie']:.3f} <span class=warn>({'valid' if m['valid'] else 'invalid: over budget'})</span></li>
<li>Best feasible QAOA sample: score {q['valoare_totala']}, cost {q['cost_total']}, bits {q['bitstring_recomandat']}</li>
<li>Most frequent measured plan: {q['cel_mai_frecvent_plan']['bitstring']}</li></ul>
<h2>Statistics</h2><pre>{escape(str(s))}</pre><p>Energy optimization is not equivalent to budget feasibility for this squared-penalty model.</p>"""


def pdf_report(result):
    buffer = BytesIO()
    with PdfPages(buffer) as pdf:
        fig, ax = plt.subplots(figsize=(8.27, 11.69)); ax.axis("off")
        c, q, m, s = result["classical"], result["quantum"], result["qubo_minimum"], result["statistics"]
        lines = ["Quantum Railways — experiment report", "", f"Configuration: {result['config']}", "",
                 f"Classical optimum: score {c['punctaj_total']}, cost {c['cost_total']}",
                 f"QUBO minimum: score {m['valoare_totala']}, cost {m['cost_total']}, valid={m['valid']}",
                 f"Best feasible QAOA: score {q['valoare_totala']}, cost {q['cost_total']}",
                 f"P(feasible): {s['p_feasible']:.2%}; P(optimal feasible): {s['p_optimal_feasible']:.2%}",
                 "", "Local simulation only. Energy and feasibility are reported separately."]
        ax.text(.06, .95, "\n".join(lines), va="top", family="monospace", wrap=True); pdf.savefig(fig); plt.close(fig)
    return buffer.getvalue()
