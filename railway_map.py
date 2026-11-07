"""Validare, model de rețea și hartă Plotly pentru Quantum Railways."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from math import isfinite

import networkx as nx
import plotly.graph_objects as go

from railway_data import POSITIONS

COLORS = {"selectată": "#10B981", "nealeasă": "#94A3B8", "blocată": "#EF4444"}


def valideaza_date(rute: Sequence[Mapping], pozitii: Mapping | None = None) -> None:
    """Ridică ValueError cu locația exactă a primei date invalide."""
    pozitii = POSITIONS if pozitii is None else pozitii
    if not isinstance(pozitii, Mapping):
        raise ValueError("Pozițiile trebuie să fie un dicționar de orașe.")
    for oras, coordonate in pozitii.items():
        if (not isinstance(oras, str) or not oras or
            not isinstance(coordonate, (tuple, list)) or len(coordonate) != 2 or
            any(isinstance(x, bool) or not isinstance(x, (int, float)) or not isfinite(x)
                for x in coordonate) or
            not (-180 <= coordonate[0] <= 180 and -90 <= coordonate[1] <= 90)):
            raise ValueError(f"Coordonate invalide pentru orașul {oras!r}.")
    ids = set()
    for index, ruta in enumerate(rute):
        label = f"Ruta de la poziția {index}"
        if not isinstance(ruta, Mapping):
            raise ValueError(f"{label}: format invalid.")
        route_id = ruta.get("id")
        if isinstance(route_id, bool) or not isinstance(route_id, int) or route_id in ids:
            raise ValueError(f"{label}: ID lipsă, invalid sau duplicat ({route_id!r}).")
        ids.add(route_id)
        label = f"Ruta {route_id}"
        cities = ruta.get("cities")
        if not isinstance(cities, (tuple, list)) or len(cities) != 2:
            raise ValueError(f"{label}: câmpul cities trebuie să conțină două orașe.")
        for city in cities:
            if not isinstance(city, str) or city not in pozitii:
                raise ValueError(f"{label}: lipsesc coordonatele orașului {city!r}.")
        for field in ("cost", "value"):
            number = ruta.get(field)
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not isfinite(number):
                raise ValueError(f"{label}: {field} trebuie să fie numeric și finit.")


def starea_rutei(route_id: int, rute_alese=(), rute_blocate=()) -> str:
    if route_id in rute_blocate:
        return "blocată"
    return "selectată" if route_id in rute_alese else "nealeasă"


def construieste_graf(rute, pozitii=None, rute_alese=None, rute_blocate=None) -> nx.MultiGraph:
    pozitii = POSITIONS if pozitii is None else pozitii
    valideaza_date(rute, pozitii)
    graf = nx.MultiGraph()
    for oras, (lon, lat) in pozitii.items():
        graf.add_node(oras, lon=lon, lat=lat, pos=(lon, lat))
    for ruta in rute:
        start, end = ruta["cities"]
        graf.add_edge(start, end, key=ruta["id"], id=ruta["id"],
                      cost=ruta["cost"], value=ruta["value"],
                      status=starea_rutei(ruta["id"], rute_alese or (), rute_blocate or ()))
    return graf


def ids_din_decizii(bits, decision_route_ids) -> list[int]:
    """Transformă deciziile x0...xn în ID-uri; un șir Qiskit are x0 la dreapta."""
    if isinstance(bits, str):
        cleaned = bits.replace(" ", "")
        if set(cleaned) - {"0", "1"}:
            raise ValueError("Șirul de măsurare conține caractere non-binare.")
        bits = [int(char) for char in cleaned[::-1]]
    if (len(bits) != len(decision_route_ids) or len(set(decision_route_ids)) != len(decision_route_ids)
        or any(bit not in (0, 1) for bit in bits)):
        raise ValueError("Este necesară o decizie binară pentru fiecare ID unic de rută.")
    return [route_id for bit, route_id in zip(bits, decision_route_ids) if bit == 1]


def calculeaza_plan(rute, rute_alese=(), rute_blocate=(), buget=0) -> dict:
    valideaza_date(rute)
    if isinstance(buget, bool) or not isinstance(buget, (int, float)) or not isfinite(buget) or buget < 0:
        raise ValueError("Bugetul trebuie să fie un număr finit și nenegativ.")
    selected, blocked = set(rute_alese), set(rute_blocate)
    valid_ids = {ruta["id"] for ruta in rute}
    if (selected | blocked) - valid_ids:
        raise ValueError("Selecția sau blocajul conține un ID de rută inexistent.")
    active = [ruta for ruta in rute if ruta["id"] in selected - blocked]
    cost = sum(ruta["cost"] for ruta in active)
    return {"cost": cost, "beneficiu": sum(ruta["value"] for ruta in active),
            "active_ids": [ruta["id"] for ruta in active], "numar_active": len(active),
            "numar_blocate": len(blocked), "conflicte": selected & blocked,
            "valid": cost <= buget, "buget": buget}


def recomandare_din_masuratori(counts: Mapping[str, int], rute, decision_route_ids, buget) -> list[int]:
    """Alege cel mai bun plan fezabil *observat*, fără a rula din nou QAOA."""
    by_id = {ruta["id"]: ruta for ruta in rute}
    if any(route_id not in by_id for route_id in decision_route_ids):
        raise ValueError("Un ID din ordinea deciziilor lipsește din date.")
    candidates = []
    for key, frequency in counts.items():
        if isinstance(frequency, bool) or not isinstance(frequency, int) or frequency < 0:
            raise ValueError(f"Frecvență invalidă pentru {key!r}.")
        ids = ids_din_decizii(key, decision_route_ids)
        if frequency <= 0:
            continue
        cost = sum(by_id[i]["cost"] for i in ids)
        if cost <= buget:
            benefit = sum(by_id[i]["value"] for i in ids)
            candidates.append((benefit, frequency, -cost, ids))
    return max(candidates, default=(0, 0, 0, []))[-1]


def deseneaza_harta(rute, rute_alese=None, rute_blocate=None, pozitii=None,
                    *, fundal_online=True, arata_nealese=True) -> go.Figure:
    """Construiește harta; coordonatele liniilor sunt segmente schematice."""
    pozitii = POSITIONS if pozitii is None else pozitii
    graf = construieste_graf(rute, pozitii, rute_alese, rute_blocate)
    fig = go.Figure()
    seen = set()
    for ruta in rute:
        status = starea_rutei(ruta["id"], rute_alese or (), rute_blocate or ())
        if status == "nealeasă" and not arata_nealese:
            continue
        start, end = ruta["cities"]
        lon1, lat1 = pozitii[start]
        lon2, lat2 = pozitii[end]
        color = COLORS[status]
        hover = (f"<b>Ruta {ruta['id']} — {start} → {end}</b><br>"
                 f"Cost: {ruta['cost']} unități<br>Beneficiu: {ruta['value']} puncte<br>"
                 f"Stare: {status.capitalize()}<extra></extra>")
        fig.add_trace(go.Scattermap(
            lon=[lon1, lon2], lat=[lat1, lat2], mode="lines",
            line={"color": color, "width": 5 if status != "nealeasă" else 2.5},
            name=status.capitalize(), legendgroup=status, showlegend=status not in seen,
            hovertemplate=hover,
        ))
        seen.add(status)
        # O zonă de hover mai mare face și liniile subțiri ușor de inspectat.
        fractions = (0.2, 0.35, 0.5, 0.65, 0.8)
        fig.add_trace(go.Scattermap(
            lon=[lon1 + (lon2 - lon1) * t for t in fractions],
            lat=[lat1 + (lat2 - lat1) * t for t in fractions],
            mode="markers", marker={"size": 13, "color": color, "opacity": 0.01},
            showlegend=False, hovertemplate=hover,
        ))
        if status == "blocată":
            fig.add_trace(go.Scattermap(
                lon=[(lon1 + lon2) / 2], lat=[(lat1 + lat2) / 2], mode="markers",
                marker={"size": 15, "color": color, "symbol": "cross"},
                showlegend=False, hovertemplate=hover,
            ))
    fig.add_trace(go.Scattermap(
        lon=[graf.nodes[city]["lon"] for city in graf.nodes],
        lat=[graf.nodes[city]["lat"] for city in graf.nodes],
        text=list(graf.nodes), mode="markers+text", textposition="top center",
        textfont={"color": "#F8FAFC" if fundal_online else "#10243B", "size": 12},
        marker={"size": 10, "color": "#2DD4BF"}, name="Orașe",
        hovertemplate="<b>%{text}</b><extra></extra>",
    ))
    lons = [pos[0] for pos in pozitii.values()]
    lats = [pos[1] for pos in pozitii.values()]
    span = max(max(lons) - min(lons), (max(lats) - min(lats)) * 1.7, 0.5)
    zoom = max(4.5, min(7.5, 7 - span / 4))
    fig.update_layout(
        map={"style": "carto-darkmatter" if fundal_online else "white-bg",
             "center": {"lon": (min(lons) + max(lons)) / 2,
                        "lat": (min(lats) + max(lats)) / 2}, "zoom": zoom},
        uirevision="romania-retea", height=610, margin={"l": 0, "r": 0, "t": 8, "b": 0},
        paper_bgcolor="#0B1730", plot_bgcolor="#0B1730",
        font={"color": "#E2E8F0"},
        legend={"orientation": "h", "y": 0.02, "x": 0.02,
                "bgcolor": "rgba(11,23,48,.82)"},
    )
    return fig
