"""Datele fictive din Quantum_Railways_Labb.ipynb, ramura GitHub zus.

ID-urile și costurile totale corespund listei ROUTES din celula de date.
Rutele internaționale includ deja costul de frontieră în câmpul cost.
"""

POSITIONS = {
    "Iași": (27.6, 47.16667),
    "București": (26.10626, 44.43225),
    "Cluj-Napoca": (23.6, 46.76667),
    "Timișoara": (21.22571, 45.75372),
    "Satu Mare": (22.8857, 47.7928),
    "Brașov": (25.60613, 45.64861),
    "Sibiu": (24.15, 45.8),
    "Craiova": (23.8, 44.31667),
    "Constanța": (28.63432, 44.18073),
    "Budapesta": (19.0402, 47.4979),
    "Sofia": (23.3219, 42.6977),
    "Belgrad": (20.4489, 44.7866),
    "Chișinău": (28.8638, 47.0105),
    "Cernăuți": (25.9358, 48.2915),
}

EDGE_DATA = [
    ("Iași", "Brașov", 2, 4),
    ("Iași", "Cluj-Napoca", 3, 6),
    ("Cluj-Napoca", "Brașov", 2, 5),
    ("Timișoara", "Cluj-Napoca", 4, 7),
    ("Timișoara", "Sibiu", 3, 6),
    ("Sibiu", "Brașov", 2, 4),
    ("Brașov", "București", 4, 9),
    ("Sibiu", "Craiova", 2, 4),
    ("București", "Constanța", 4, 7),
    ("Craiova", "București", 2, 5),
    ("Cluj-Napoca", "Sibiu", 2, 4),
    ("Iași", "Constanța", 6, 11),
    ("Satu Mare", "Cluj-Napoca", 3, 6),
]

INTERNATIONAL_EDGES = [
    ("Timișoara", "Budapesta", 4, 8, 0),
    ("București", "Sofia", 4, 7, 0),
    ("Timișoara", "Belgrad", 3, 9, 2),
    ("Iași", "Chișinău", 3, 10, 2),
    ("Iași", "Cernăuți", 4, 11, 3),
    ("Satu Mare", "Budapesta", 4, 8, 0),
]

ROUTES = [
    {
        "id": index,
        "cities": (start, end),
        "cost": cost,
        "value": value,
        "border_cost": 0,
        "international": False,
    }
    for index, (start, end, cost, value) in enumerate(EDGE_DATA)
]

for start, end, cost, value, border_cost in INTERNATIONAL_EDGES:
    ROUTES.append(
        {
            "id": len(ROUTES),
            "cities": (start, end),
            "cost": cost + border_cost,
            "value": value,
            "border_cost": border_cost,
            "international": True,
        }
    )

# Notebook-ul selectează toate rutele și cere bugetul prin input().
DEMO_IDS = list(range(len(ROUTES)))
demo_routes = [ROUTES[route_id] for route_id in DEMO_IDS]
DEFAULT_BUDGET = 7  # Valoare inițială a interfeței, nu o constantă din noul notebook.
