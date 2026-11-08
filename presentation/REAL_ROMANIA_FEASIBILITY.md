# Future research: a real Romanian railway subnetwork

**Status:** research roadmap, separate from the fictional costs and scores used in Quantum Railways. Sources checked 8 November 2026. The current app does not contain real line-level construction costs, passenger demand or timetable constraints.

| Source | What it can support | Access / limitations |
|---|---|---|
| [CFR SA Network Statement 2026](https://cfr.ro/download-drr-2026-network-statement/) and [Annex 5](https://cfr.ro/files/ddr/EN%202026/Annex%205%20.pdf) | Official network overview, station/operating-point context, line characteristics and annex maps. Annex 5 reports 10,615 km of lines, 4,031 electrified km, 7,600 single-track km, 2,919 double-track km and 896 operating points in its stated period. | Public PDF; each figure needs its annex definition/date. Reuse terms are not established by the download page, so verify licence before republishing derived data or maps. |
| [ERA RINF dataset explorer](https://rinf.data.era.europa.eu/dataset-explorer) and [ERA RINF overview](https://www.era.europa.eu/cs/node/1665) | Infrastructure records, operational points, sections of line and track attributes; Romania `RO-0053.zip` was listed with a September 2025 publication date. | Public access, but topology/connectivity and coverage require validation. Check current dataset licence and terms before redistribution. An attribute dataset is not automatically a clean routable graph. |
| [Eurostat railway line data](https://ec.europa.eu/eurostat/databrowser/view/rail_if_line_tr/default/table) and [speed data](https://ec.europa.eu/eurostat/databrowser/product/view/RAIL_IF_LINE_SP) | Official aggregate cross-checks and reported speed categories. | National/regional aggregates are not route-level investment costs. Definitions and reporting years can differ from CFR. |

## Feasible staged study

1. Obtain CFR/ERA station and segment data and document legal reuse terms.
2. Build a topology-checked graph; reconcile names, coordinates, line sections, direction, electrification, track count and speeds.
3. Choose a small regional corridor or handful of proposed investments. Avoid a naive all-station QAOA model: `n` binary decisions imply `2ⁿ` basis states, and the current local comparison is capped at eight active routes.
4. Define a specific public-interest question, such as modernization choices under a published investment cap or resilience under a closure.
5. Use published project documents for investment costs. Define a transparent benefit metric from accessibility, travel-time, demand or resilience evidence; label assumptions explicitly. Distance alone cannot establish construction cost or return.
6. Produce an exact/classical benchmark for the restricted case, then a mathematically matched small QUBO/Ising/QAOA experiment.
7. Compare **valid** plans, resource use and model limitations; investigate decomposition before scaling.

There is insufficient verified, harmonized station/segment cost and benefit data in the current repository for an honest real-data proof of concept. The deck therefore presents a source-grounded roadmap rather than invented Romanian project economics.
