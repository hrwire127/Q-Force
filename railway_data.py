"""Datele fictive ale rețelei din Quantum_Railways_Labb.ipynb.

Coordonatele sunt (longitudine, latitudine). Costurile și beneficiile sunt
unități didactice, iar liniile dintre orașe nu sunt trasee feroviare reale.
"""

POSITIONS = {
    "Iași": (27.6, 47.16667),
    "București": (26.10626, 44.43225),
    "Cluj-Napoca": (23.6, 46.76667),
    "Timișoara": (21.22571, 45.75372),
    "Brașov": (25.60613, 45.64861),
    "Sibiu": (24.15, 45.8),
    "Craiova": (23.8, 44.31667),
    "Constanța": (28.63432, 44.18073),
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
]

ROUTES = [
    {"id": index, "cities": (start, end), "cost": cost, "value": value}
    for index, (start, end, cost, value) in enumerate(EDGE_DATA)
]

DEMO_IDS = [0, 1, 2, 6, 8]
DEFAULT_BUDGET = 7
