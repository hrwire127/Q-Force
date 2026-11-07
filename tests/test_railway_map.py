import json
from pathlib import Path

import networkx as nx
import plotly.graph_objects as go
import pytest

from railway_data import DEFAULT_BUDGET, DEMO_IDS, POSITIONS, ROUTES
from railway_map import (COLORS, calculeaza_plan, construieste_graf,
                         deseneaza_harta, ids_din_decizii,
                         recomandare_din_masuratori, starea_rutei, valideaza_date)


def test_date_din_notebook():
    notebook = json.loads(Path("validation/baseline_notebook.ipynb").read_text(encoding="utf-8"))
    board = next("".join(cell["source"]) for cell in notebook["cells"]
                 if "EDGE_DATA =" in "".join(cell.get("source", [])))
    assert "DEMO_IDS=[0,1,2,6,8]" in board
    assert len(POSITIONS) == 8
    assert len(ROUTES) == 12
    assert ROUTES[6] == {"id": 6, "cities": ("Brașov", "București"), "cost": 4, "value": 9}


def test_graf_noduri_muchii_si_atribute():
    graph = construieste_graf(ROUTES, rute_alese=[6], rute_blocate=[6])
    assert isinstance(graph, nx.MultiGraph)
    assert graph.number_of_nodes() == 8
    assert graph.number_of_edges() == 12
    assert graph.nodes["Iași"]["pos"] == POSITIONS["Iași"]
    assert graph["Brașov"]["București"][6]["status"] == "blocată"


def test_rute_paralele_raman_distincte():
    routes = [ROUTES[0], {**ROUTES[0], "id": 99}]
    assert construieste_graf(routes).number_of_edges() == 2


@pytest.mark.parametrize("bad,pattern", [
    ([{**ROUTES[0], "id": 1}, {**ROUTES[1], "id": 1}], "duplicat"),
    ([{**ROUTES[0], "cities": ("Iași", "Oraș lipsă")}], "Oraș lipsă"),
    ([{**ROUTES[0], "cost": "2"}], "cost"),
    ([{**ROUTES[0], "value": float("nan")}], "value"),
])
def test_date_invalide(bad, pattern):
    with pytest.raises(ValueError, match=pattern):
        valideaza_date(bad)


def test_decizii_folosesc_id_fizic_si_endianness_qiskit():
    assert ids_din_decizii([1, 0, 0, 1, 0], DEMO_IDS) == [0, 6]
    assert ids_din_decizii("01001", DEMO_IDS) == [0, 6]
    with pytest.raises(ValueError):
        ids_din_decizii("0101", DEMO_IDS)


def test_plan_buget_blocaj_si_date_nemodificate():
    before = json.dumps(ROUTES, ensure_ascii=False)
    assert calculeaza_plan(ROUTES, [], [], DEFAULT_BUDGET)["cost"] == 0
    all_plan = calculeaza_plan(ROUTES, [r["id"] for r in ROUTES], [], 100)
    assert all_plan["numar_active"] == 12
    plan = calculeaza_plan(ROUTES, [0, 1, 2], [], 7)
    assert (plan["cost"], plan["beneficiu"], plan["valid"]) == (7, 15, True)
    assert not calculeaza_plan(ROUTES, [0, 1, 2], [], 6)["valid"]
    blocked = calculeaza_plan(ROUTES, [0, 1, 2], [1], 7)
    assert blocked["active_ids"] == [0, 2]
    assert (blocked["cost"], blocked["beneficiu"], blocked["conflicte"]) == (4, 9, {1})
    assert json.dumps(ROUTES, ensure_ascii=False) == before


def test_recomandare_din_rezultate_salvate():
    results = json.loads(Path("railway_results.json").read_text(encoding="utf-8"))
    assert recomandare_din_masuratori(results["ideal_counts"], ROUTES, DEMO_IDS, 7) == [0, 1, 2]


def test_figura_culori_hover_si_prioritate():
    figure = deseneaza_harta(ROUTES, [0, 6], [6])
    assert isinstance(figure, go.Figure)
    assert figure.layout.uirevision == "romania-retea"
    assert starea_rutei(6, [6], [6]) == "blocată"
    assert any(getattr(trace.line, "color", None) == COLORS["selectată"]
               for trace in figure.data if hasattr(trace, "line"))
    blocked = [trace for trace in figure.data if "Ruta 6" in (trace.hovertemplate or "")]
    assert blocked[0].line.color == COLORS["blocată"]
    assert "Beneficiu" in blocked[0].hovertemplate
    assert "București" in blocked[0].hovertemplate
    assert isinstance(deseneaza_harta(ROUTES, fundal_online=False), go.Figure)
