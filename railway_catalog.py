"""Extended catalogue shared by UI, CLI, maps and reports.
Core physical IDs 0-11 remain the original board. Border costs follow zus.
"""
from railway_data import ROUTES as CORE_ROUTES, POSITIONS as CORE_POSITIONS
from railway_data import DEFAULT_BUDGET, DEMO_IDS

POSITIONS = {**CORE_POSITIONS,
    "Satu Mare": (22.8857, 47.7928), "Budapesta": (19.0402, 47.4979),
    "Sofia": (23.3219, 42.6977), "Belgrad": (20.4489, 44.7866),
    "Chișinău": (28.8638, 47.0105), "Cernăuți": (25.9358, 48.2915)}
ROUTES = [{**r, "international": False, "border_cost": 0} for r in CORE_ROUTES]
ROUTES.append(dict(id=12,cities=("Satu Mare","Cluj-Napoca"),cost=3,value=6,
                   international=False,border_cost=0))
INTERNATIONAL_EDGES = [
    ("Timișoara","Budapesta",4,8,1), ("București","Sofia",4,7,1),
    ("Timișoara","Belgrad",3,9,1), ("Iași","Chișinău",3,10,1),
    ("Iași","Cernăuți",4,11,1), ("Satu Mare","Budapesta",4,8,1)]
for start,end,cost,value,border in INTERNATIONAL_EDGES:
    ROUTES.append(dict(id=len(ROUTES),cities=(start,end),cost=cost+border,value=value,
                       international=True,border_cost=border))
demo_routes = [r for r in ROUTES if r["id"] in DEMO_IDS]
