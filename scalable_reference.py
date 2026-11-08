"""Exact cost-based references without allocating one object per binary plan."""
from math import isclose, sqrt

import quantum_optimizer as qo


class CostReference:
    """Count plans exactly; retain bounded representatives, never all tied vectors.

    Costs are integer construction costs, as required by the shared scenario.
    The main feasible plan uses Sabina's input-vector lexicographic tie rule.
    QUBO minima use the existing Qiskit-key tie rule.
    """
    REPRESENTATIVES = 64

    def __init__(self, routes, budget, penalty):
        self.routes, self.budget, self.penalty = qo._problem(routes, budget, penalty)
        self.n = len(self.routes)
        self.plan_count = 1 << self.n
        self.profile_max = min(100, max(budget + 1, sum(r['cost'] for r in self.routes)))
        # E(empty)=penalty*B² is an upper bound on the global minimum. At any
        # larger cost than this bound even the sum of ALL values cannot win.
        energy_bound = budget + int(sqrt(sum(r['value'] for r in self.routes) / penalty + budget**2)) + 2
        self.cost_cap = min(sum(r['cost'] for r in self.routes), max(self.profile_max, energy_bound))
        states = {0: dict(count=1, best=0, best_count=1, lex=0, qmask=0, top=[(0, 0)])}
        self.states_evaluated = 0
        for index, route in enumerate(self.routes):
            following = {cost: dict(state) for cost, state in states.items()}
            lexbit, qbit = 1 << (self.n - 1 - index), 1 << index
            for cost, state in states.items():
                self.states_evaluated += 1
                new_cost = cost + route['cost']
                if new_cost > self.cost_cap:
                    continue
                taken = [(value + route['value'], mask | lexbit) for value, mask in state['top']]
                value = state['best'] + route['value']
                current = following.get(new_cost)
                if current is None:
                    following[new_cost] = dict(count=state['count'], best=value,
                        best_count=state['best_count'], lex=state['lex'] | lexbit,
                        qmask=state['qmask'] | qbit, top=taken)
                    continue
                current['count'] += state['count']
                current['top'] = sorted(set(current['top'] + taken), key=lambda item: (-item[0], item[1]))[:self.REPRESENTATIVES]
                if value > current['best']:
                    current.update(best=value, best_count=state['best_count'],
                                   lex=state['lex'] | lexbit, qmask=state['qmask'] | qbit)
                elif value == current['best']:
                    current['best_count'] += state['best_count']
                    current['lex'] = min(current['lex'], state['lex'] | lexbit)
                    current['qmask'] = min(current['qmask'], state['qmask'] | qbit)
            states = following
        self.states = states
        feasible = [(cost, state) for cost, state in states.items() if cost <= budget]
        main_cost, main = min(feasible, key=lambda item: (-item[1]['best'], item[0], item[1]['lex']))
        self.classical = self.from_mask(main['lex'])
        self.feasible_count = sum(state['count'] for _, state in feasible)
        self.optimal_count = sum(state['best_count'] for _, state in feasible if state['best'] == main['best'])
        minimum_cost, minimum = min(states.items(), key=lambda item: (
            -item[1]['best'] + penalty * (item[0] - budget)**2, item[1]['qmask']))
        self.minimum = self.plan(qo.decode_key(format(minimum['qmask'], f'0{self.n}b'), self.n))
        minimum_costs = [(cost, state) for cost, state in states.items() if isclose(
            -state['best'] + penalty * (cost-budget)**2, self.minimum['energie'], rel_tol=0, abs_tol=1e-9)]
        self.minimum_count = sum(state['best_count'] for _, state in minimum_costs)
        optimal_masks = [(cost, mask) for cost, state in feasible if state['best'] == main['best']
                         for value, mask in state['top'] if value == main['best']]
        self.optima = [self.from_mask(mask) for _, mask in sorted(optimal_masks)[:self.REPRESENTATIVES]]
        minima = [self.from_mask(mask) for _, state in minimum_costs
                  for value, mask in state['top'] if value == state['best']]
        by_key = {p['bitstring']: p for p in minima + [self.minimum]}
        self.minima = [by_key[key] for key in sorted(by_key)[:self.REPRESENTATIVES]]

    def plan(self, bits):
        if len(bits) != self.n or any(bit not in (0, 1) for bit in bits):
            raise ValueError('One binary decision is required per route')
        selected = [route for route, bit in zip(self.routes, bits) if bit]
        cost, value = sum(r['cost'] for r in selected), sum(r['value'] for r in selected)
        return dict(bits=list(bits), bitstring=''.join(map(str, reversed(bits))),
                    ids_rute=[r['id'] for r in selected], rute=selected, cost_total=cost,
                    valoare_totala=value, valid=cost <= self.budget,
                    energie=float(-value + self.penalty * (cost-self.budget)**2))

    def from_mask(self, mask):
        return self.plan([int(bit) for bit in format(mask, f'0{self.n}b')])

    def summarize(self, counts):
        if not counts or any(type(value) is not int or value < 0 for value in counts.values()) or sum(counts.values()) <= 0:
            raise ValueError('Expected positive measurement counts')
        total = sum(counts.values())
        rows = [dict(self.plan(qo.decode_key(key, self.n)), count=count, probability=count/total)
                for key, count in counts.items() if count]
        rows.sort(key=lambda p: (-p['count'], p['bitstring']))
        feasible = [p for p in rows if p['valid']]
        return dict(distribution=rows, most_frequent=rows[0],
            best_feasible=min(feasible, key=lambda p: (-p['valoare_totala'], p['cost_total'], p['bitstring']), default=None),
            p_feasible=sum(p['probability'] for p in feasible),
            p_optimal_feasible=sum(p['probability'] for p in feasible if p['valoare_totala'] == self.classical['valoare_totala']),
            p_model_minimum=sum(p['probability'] for p in rows if isclose(p['energie'], self.minimum['energie'], abs_tol=1e-9, rel_tol=0)),
            over_budget_rate=sum(p['probability'] for p in rows if not p['valid']),
            mean_true_score=sum(p['probability'] * p['valoare_totala'] for p in rows),
            mean_construction_cost=sum(p['probability'] * p['cost_total'] for p in rows),
            expected_energy=sum(p['probability'] * p['energie'] for p in rows))

    def public(self, plan):
        return dict(vector_binar=plan['bits'], cost_total=plan['cost_total'], punctaj_total=plan['valoare_totala'])

    def selected(self, plan):
        return [dict(id=r['id'], nume=' — '.join(r['cities']), cost=r['cost'], puncte=r['value']) for r in plan['rute']]

    def classical_result(self):
        return dict(self.public(self.classical), rute_selectate=self.selected(self.classical),
            buget_ramas=self.budget-self.classical['cost_total'], planuri_evaluate=self.plan_count,
            solutii_optime=[self.public(p) for p in self.optima], numar_solutii_optime=self.optimal_count,
            metoda='exact cost dynamic programming', stari_calculate=self.states_evaluated)

    def analysis(self):
        ranked = sorted(((-value, cost, mask) for cost, state in self.states.items() if cost <= self.budget
                         for value, mask in state['top']))
        def alternative(mask):
            plan = self.from_mask(mask)
            return dict(self.public(plan), rute_selectate=self.selected(plan), buget_ramas=self.budget-plan['cost_total'],
                        pierdere_punctaj=self.classical['valoare_totala']-plan['valoare_totala'],
                        economie_cost=self.classical['cost_total']-plan['cost_total'])
        cheaper = next((mask for _, cost, mask in ranked if cost < self.classical['cost_total']), None)
        frontier, highest = [], -1
        for cost, state in sorted(self.states.items()):
            if cost <= self.budget and state['best'] > highest:
                plan = self.from_mask(state['lex'])
                frontier.append(dict(self.public(plan), rute_selectate=self.selected(plan), buget_ramas=self.budget-cost))
                highest = state['best']
        profile = []
        for budget in range(self.profile_max + 1):
            cost, state = min(((c, s) for c, s in self.states.items() if c <= budget),
                             key=lambda item: (-item[1]['best'], item[0], item[1]['lex']))
            plan = self.from_mask(state['lex'])
            gain = state['best']-profile[-1]['punctaj_total'] if profile else 0
            profile.append(dict(self.public(plan), buget=budget, buget_ramas=budget-cost,
                rute_selectate=self.selected(plan), numar_solutii_optime=sum(s['best_count'] for c, s in self.states.items()
                    if c <= budget and s['best'] == state['best']), castig_marginal=gain, este_salt_maxim=False))
        max_gain = max(p['castig_marginal'] for p in profile)
        for point in profile:
            point['este_salt_maxim'] = bool(point['buget'] and max_gain > 0 and point['castig_marginal'] == max_gain)
        names = ', '.join(' — '.join(r['cities']) for r in self.classical['rute']) or 'nicio rută'
        summary = (f"Pentru bugetul {self.budget}, optimul a fost calculat exact prin programare dinamică. "
            f"Planul selectează {names}, costă {self.classical['cost_total']} și oferă "
            f"{self.classical['valoare_totala']} puncte. Niciun plan valid nu are punctaj mai mare. "
            f"Există {self.optimal_count} soluții optime și {self.feasible_count} planuri fezabile. "
            "Numărarea este exactă; tabelele afișează reprezentanți ai soluțiilor.")
        return dict(result=self.classical_result(), explanation=dict(rezumat=summary, rute_selectate=names,
                indicatori=dict(numar_solutii_optime=self.optimal_count)),
            audit=dict(planuri_evaluate=self.plan_count, planuri_valide=self.feasible_count,
                planuri_peste_buget=self.plan_count-self.feasible_count, planuri_cu_rute_blocate=0,
                frontiera_pareto=frontier, alternative=[alternative(mask) for _, _, mask in ranked[:3]]),
            alternatives=dict(planuri=[alternative(mask) for _, _, mask in ranked[:3]],
                solutii_optime=[alternative(int(''.join(map(str,p['bits'])),2)) for p in self.optima],
                alternativa_mai_ieftina=alternative(cheaper) if cheaper is not None else None),
            pareto=frontier, budget_profile=profile, decision_ids=[r['id'] for r in self.routes],
            tie_policy='maximum score, minimum cost, lexicographic input-order bit vector',
            representatives_complete=self.optimal_count == len(self.optima))

    def audit_plan(self, bits):
        plan = self.plan(bits)
        return dict(self.public(plan), respecta_bugetul=plan['valid'], respecta_blocajele=True,
            este_valid=plan['valid'], include_ruta_blocata=False, rute_selectate=self.selected(plan),
            este_optim_global=plan['valid'] and plan['valoare_totala'] == self.classical['valoare_totala'],
            diferenta_punctaj_fata_de_optim=plan['valoare_totala']-self.classical['valoare_totala'],
            diferenta_cost_fata_de_referinta=plan['cost_total']-self.classical['cost_total'],
            punctaj_optim_clasic=self.classical['valoare_totala'], numar_solutii_optime=self.optimal_count)

    def audit_distribution(self, counts):
        summary = self.summarize(counts)
        leader = min(summary['distribution'], key=lambda p: (-p['count'], p['bits']))
        return dict(format_distributie='numarari', total_masurari=sum(counts.values()),
            probabilitate_planuri_valide=summary['p_feasible'], probabilitate_solutii_optime=summary['p_optimal_feasible'],
            punctaj_mediu=summary['mean_true_score'], cost_mediu=summary['mean_construction_cost'],
            cel_mai_frecvent_plan=self.audit_plan(leader['bits']))
