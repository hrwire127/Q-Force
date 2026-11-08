"""Sample-based QAOA for larger selections using bounded MPS simulation."""
from time import perf_counter
import numpy as np
from qiskit import transpile
from qiskit_aer import AerSimulator
from scipy.optimize import minimize
import quantum_optimizer as qo


def optimize_mps(routes,budget,penalty,*,p,shots,maxiter,seed,restarts,backend_mode,
                 transpilation_level,optimizer_tol):
    started=perf_counter()
    qubo=qo.construct_qubo(routes,budget,penalty)
    circuit,parameters=qo.parameterized_qaoa(qubo,p)
    measured=circuit.copy();qo._add_measurements(measured)
    simulator=AerSimulator(method='matrix_product_state',max_parallel_threads=1,
        matrix_product_state_max_bond_dimension=qo.MPS_BOND_DIMENSION,
        matrix_product_state_truncation_threshold=qo.MPS_TRUNCATION_THRESHOLD,
        mps_sample_measure_algorithm='mps_apply_measure')
    compiled=transpile(measured,simulator,optimization_level=transpilation_level,seed_transpiler=seed)
    reference=qo.classical_reference(routes,budget)
    training_shots=min(shots,256)
    rng=np.random.default_rng(seed)
    history,runs=[],[]
    best_energy,best_angles,best_run=float('inf'),None,None
    training_started=perf_counter()
    for restart in range(restarts):
        initial=rng.uniform(0,[2*np.pi,np.pi]*p)
        run_energy,run_angles,run_evaluations=float('inf'),None,0
        run_started=perf_counter()
        def objective(angles):
            nonlocal run_energy,run_angles,run_evaluations
            bound=compiled.assign_parameters(dict(zip(parameters,map(float,angles))))
            counts=simulator.run(bound,shots=training_shots,seed_simulator=seed).result().get_counts()
            energy=0.
            for key,count in counts.items():
                bits=qo.decode_key(key,len(routes))
                cost=sum(bit*r['cost'] for bit,r in zip(bits,routes))
                value=sum(bit*r['value'] for bit,r in zip(bits,routes))
                energy+=count*(-value+penalty*(cost-budget)**2)/training_shots
            run_evaluations+=1
            history.append(dict(restart=restart,evaluation=len(history)+1,energy=float(energy)))
            if energy<run_energy:run_energy,run_angles=energy,np.array(angles,copy=True)
            return energy
        initial_energy=objective(initial)
        result=minimize(objective,initial,method='COBYLA',options={'maxiter':maxiter,'tol':optimizer_tol})
        runs.append(dict(restart=restart,energie_initiala=initial_energy,energie_finala=run_energy,
            unghiuri_initiale=initial.tolist(),unghiuri_optime=run_angles.tolist(),evaluari=run_evaluations,
            evaluari_scipy=int(result.nfev),status=int(result.status),succes=bool(result.success),
            mesaj=str(result.message),timp_secunde=perf_counter()-run_started))
        if run_energy<best_energy:best_energy,best_angles,best_run=run_energy,run_angles.copy(),restart
    training_seconds=perf_counter()-training_started
    bound=circuit.assign_parameters(dict(zip(parameters,map(float,best_angles))))
    sampling_started=perf_counter()
    counts,resources=qo._sample_counts(bound,shots,seed,backend_mode,optimization_level=transpilation_level)
    sampling_seconds=perf_counter()-sampling_started
    summary=qo._summarize_counts(counts,routes,budget,penalty,reference['valoare_optima'],shots)
    best=summary['best']
    return dict(status='ok' if best else 'no_valid_sample',rute_recomandate=best['rute'] if best else [],
        ids_rute_recomandate=best['ids_rute'] if best else [],bitstring_recomandat=best['bitstring'] if best else None,
        cost_total=best['cost_total'] if best else None,valoare_totala=best['valoare_totala'] if best else None,
        buget=budget,buget_ramas=budget-best['cost_total'] if best else None,valid=best is not None,penalizare=penalty,
        probabilitate_plan_recomandat=best['probabilitate'] if best else 0.,rata_planuri_valide=summary['valid_rate'],
        probabilitate_optim_valid=summary['optimal_rate'],energie_medie=float(best_energy),
        energie_medie_masurata=summary['sampled_energy'],energie_medie_initiala=runs[best_run]['energie_initiala'],
        probabilitate_valida_ideala=None,probabilitate_optim_valid_ideala=None,
        unghiuri_optime=best_angles.tolist(),gamma=best_angles[::2].tolist(),beta=best_angles[1::2].tolist(),
        referinta_clasica=reference,diferenta_valoare=reference['valoare_optima']-best['valoare_totala'] if best else None,
        cel_mai_frecvent_plan=summary['most_frequent'],top_planuri=summary['top'],counts=summary['counts'],
        statevector_probabilities=None,exact_ideal_statistics=None,
        optimizare=dict(metoda='COBYLA',restart_selectat=best_run,rulari=runs,history=history),
        statistici=dict(numar_qubiti=len(routes),qaoa_depth=p,shots=shots,maxiter=maxiter,restarts=restarts,
            evaluari=len(history),timp_antrenare_secunde=training_seconds,timp_masurare_secunde=sampling_seconds,
            timp_total_secunde=perf_counter()-started,seed=seed,backend=backend_mode,
            antrenare='ideal_mps_sampled_expectation',training_shots=training_shots,optimizer_tol=optimizer_tol,
            simulare_zgomot='executata' if backend_mode=='noisy' else 'omisa_mod_ideal',**resources))
