import fs from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { pathToFileURL } from 'node:url';

const here = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(?=[A-Za-z]:)/, ''));
const runtimeRoot = process.env.RUNTIME_NODE_MODULES || 'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/node/node_modules';
const { Presentation, PresentationFile } = await import(pathToFileURL(path.join(runtimeRoot, '@oai/artifact-tool/dist/artifact_tool.mjs')).href);
const summary = JSON.parse(await fs.readFile(path.join(here, 'source_data/experiments_summary.json'), 'utf8'));
const runs = Object.fromEntries(summary.runs.map(r => [r.name, r]));
const shots = summary.shot_sensitivity || JSON.parse(await fs.readFile(path.join(here, 'source_data/shot_sensitivity.json'), 'utf8'));
let hardware=null;
try { const candidate=JSON.parse(await fs.readFile(path.join(here,'source_data/ibm_verified_result.json'),'utf8'));if(candidate.validation==='verified'&&candidate.job_id==='dbnpc00ou4as73b4u830')hardware=candidate; } catch {}
const C = {navy:'#0B1730', blue:'#142B4B', teal:'#0D9488', mint:'#62D8CE', coral:'#DC725E', gold:'#F6BB67', white:'#F7F9FC', muted:'#AFC3D5', dark:'#071124', line:'#29415F'};
const p = Presentation.create({slideSize:{width:1280,height:720}});
const noLine = {style:'solid',fill:'none',width:0};
const P = (x,y,w,h)=>({left:x,top:y,width:w,height:h});
function box(s,x,y,w,h,fill=C.blue,r=0,stroke='none',sw=0){return s.shapes.add({geometry:r?'roundRect':'rect',position:P(x,y,w,h),fill,line:{style:'solid',fill:stroke,width:sw}})}
function txt(s,t,x,y,w,h,size=24,color=C.white,bold=false,align='left'){
  let q=s.shapes.add({geometry:'textbox',position:P(x,y,w,h),fill:'none',line:noLine});q.text=String(t);q.text.style={fontFamily:'Arial',fontSize:size,color,bold,alignment:align,verticalAlignment:'middle',wrap:true};return q;
}
function pill(s,t,x,y,w,fill=C.teal,color=C.white){box(s,x,y,w,32,fill,15);txt(s,t,x,y+3,w,26,14,color,true,'center')}
function base(section,title,kicker=''){
  const s=p.slides.add();s.background.fill=C.navy;
  for(let x=0;x<1280;x+=80) box(s,x,0,1,720,'#14243D');
  for(let y=0;y<720;y+=80) box(s,0,y,1280,1,'#14243D');
  box(s,0,0,1280,9,C.teal);txt(s,section.toUpperCase(),62,37,600,25,14,C.mint,true);txt(s,title,62,80,1150,84,42,C.white,true);
  if(kicker)txt(s,kicker,64,167,1100,38,19,C.muted);
  box(s,62,666,1156,1,C.line);txt(s,'Q-FORCE  /  QUANTUM RAILWAYS',62,674,680,22,12,C.muted,true);txt(s,String(p.slides.items.length).padStart(2,'0'),1164,674,54,22,12,C.mint,true,'right');return s;
}
function notes(s,text,source=''){s.speakerNotes.text=`${text}${source?'\n\nSources and provenance: '+source:''}`}
function metric(s,label,value,x,y,w=245,accent=C.mint,sub=''){box(s,x,y,w,142,C.blue,16,C.line,1);txt(s,value,x+20,y+18,w-40,65,46,accent,true);txt(s,label,x+20,y+90,w-40,25,17,C.white,true);if(sub)txt(s,sub,x+20,y+117,w-40,18,12,C.muted)}
function bar(s,label,val,x,y,w,color=C.teal,scale=1){txt(s,label,x,y,w,22,17,C.white);box(s,x,y+27,w,17,C.blue,8);box(s,x,y+27,Math.max(3,w*val/scale),17,color,8);txt(s,`${Math.round(val*1000)/10}%`,x+w+12,y+24,80,24,16,color,true)}
function source(s,t){txt(s,t,64,638,1090,20,12,C.muted)}

// 1 — Cover
{
 const s=p.slides.add();s.background.fill=C.navy;
 for(let x=0;x<1280;x+=64)box(s,x,0,1,720,'#14243D');for(let y=0;y<720;y+=64)box(s,0,y,1280,1,'#14243D');
 box(s,0,0,1280,10,C.teal);txt(s,'Q-FORCE  /  HACKATHON RESEARCH',72,65,780,30,17,C.mint,true);
 txt(s,'QUANTUM',72,163,850,95,72,C.white,true);txt(s,'RAILWAYS',72,248,850,100,76,C.mint,true);
 txt(s,'Optimizing the Tracks of Tomorrow',76,373,800,49,30,C.white);
 box(s,76,454,685,2,C.coral);txt(s,'Catalin  ·  Artiom  ·  Zus  ·  Sabina  ·  Livia',76,478,880,38,21,C.muted);
 // Native editable railway motif.
 const nodes=[[947,173],[1104,230],[996,352],[1166,414],[1022,552],[865,509]];
 const edges=[[0,1],[0,2],[1,3],[2,3],[2,4],[4,5],[3,4]];
 for(const [a,b] of edges){let A=nodes[a],B=nodes[b],dx=B[0]-A[0],dy=B[1]-A[1],n=Math.ceil(Math.hypot(dx,dy)/11);for(let j=0;j<=n;j++){let t=j/n;box(s,A[0]+dx*t,A[1]+dy*t,5,5,(a+b)%2?C.teal:C.coral,2)}}
 for(const [x,y] of nodes){box(s,x-11,y-11,22,22,C.navy,11,C.mint,3)}
 txt(s,'5 route decisions  /  32 plans',76,628,600,30,18,C.gold,true);
 notes(s,'Open with the research question: can a quantum optimizer sample useful railway investment plans under a budget? The routes, costs and rewards in the current application are fictional. This presentation reports reproducible local experiments and a verified IBM status check.','repository branch zus, commit 728ce483; presentation/EXPERIMENT_EVIDENCE.md');
}
// 2 — Challenge
{
 const s=base('01 / challenge','Which connections should we build?','A fictional Romanian route network, five binary investment choices, one budget.');
 const routes=[['Iași–Brașov',2,4],['Iași–Cluj-Napoca',3,6],['Cluj-Napoca–Brașov',2,5],['Brașov–București',4,9],['București–Constanța',4,7]];
 routes.forEach((r,i)=>{let y=247+i*63;box(s,65,y,685,51,C.blue,10,C.line,1);pill(s,String(i),76,y+9,34,i<3?C.teal:C.coral);txt(s,r[0],125,y+10,420,30,21,C.white,true);txt(s,`cost ${r[1]}  /  score ${r[2]}`,554,y+12,180,25,17,C.muted)});
 box(s,800,247,405,330,C.blue,18,C.line,1);txt(s,'xᵢ = 1',836,280,330,73,49,C.mint,true);txt(s,'choose route i',839,355,320,31,25,C.white);box(s,835,414,330,2,C.line);txt(s,'Σ costᵢ xᵢ  ≤  7',839,445,320,50,31,C.gold,true);txt(s,'maximize Σ scoreᵢ xᵢ',839,510,335,33,22,C.white);
 source(s,'Route costs and scores: railway_data.py; scenario route IDs 0, 1, 2, 6, 8.');
 notes(s,'Each binary variable represents purchasing one route. The five selected routes span five distinct cities. Objective is additive score under a construction-budget cap. The app does not optimize passenger connectivity; routes are fictional and are drawn between real city positions.','railway_data.py; classical_optimizer.py; presentation/experiments/penalty_0_7_seed_2026.json');
}
// 3 — Exact benchmark
{
 const s=base('02 / classical reference','32 plans. 16 valid. Two best.','Exhaustive enumeration is the ground truth for this five-route instance.');
 metric(s,'binary plans','2⁵ = 32',65,247,344);metric(s,'budget-feasible','16',466,247,344);metric(s,'best score / cost','15 / 7',867,247,344,C.gold);
 box(s,65,428,1145,150,C.blue,16,C.line,1);txt(s,'TIED OPTIMA',94,448,260,30,16,C.mint,true);txt(s,'01010',97,491,250,60,43,C.white,true);txt(s,'routes 1 + 6',335,507,240,30,19,C.muted);txt(s,'00111',665,491,250,60,43,C.white,true);txt(s,'routes 0 + 1 + 2',900,507,260,30,19,C.muted);
 source(s,'Exact enumeration on route IDs 0,1,2,6,8 · B=7 · score ties included.');
 notes(s,'Enumerate all 2^5 combinations and filter cost ≤7. Sixteen plans are feasible. Two distinct plans tie at value 15 and cost 7. This deterministic reference lets us distinguish “best observed feasible QAOA sample” from a guarantee. Displayed bitstrings follow the application decision order.','presentation/experiments/penalty_0_7_seed_2026.json; classical_optimizer.py');
}
// 4 — modelling trap
{
 const s=base('03 / model','A low-energy answer can break the budget','The squared penalty is centered on spending exactly B, while the rule allows spending less.');
 txt(s,'E(x) = −V(x) + λ [C(x) − B]²',80,226,1090,64,38,C.white,true);pill(s,'λ = 0.7',85,303,150,C.coral);
 box(s,70,385,520,185,C.blue,18,C.line,1);txt(s,'EXACT FEASIBLE OPTIMUM',98,407,460,29,17,C.mint,true);txt(s,'score 15  ·  cost 7',98,451,460,50,32,C.white,true);txt(s,'Budget respected',98,518,390,26,20,C.mint);
 box(s,690,385,520,185,C.blue,18,C.coral,2);txt(s,'EXACT QUBO MINIMUM',718,407,460,29,17,C.coral,true);txt(s,'score 18  ·  cost 8',718,451,460,50,32,C.white,true);txt(s,'−17.3 energy  ·  1 over budget',718,518,430,26,20,C.coral,true);
 source(s,'Direct cost model, QUBO and Ising energies agree for all 32 states (max difference <1.1×10⁻¹⁴).');
 notes(s,'This is the central mathematical failure. The QUBO conversion is internally consistent, but a weak squared equality penalty rewards an invalid, over-budget plan in this scenario. At λ=4 the exact model minimum becomes feasible, but squared penalties do not universally encode an inequality. Do not compare absolute energies across different λ because the objective changes.','quantum_optimizer.py; presentation/source_data/experiments_summary.json');
}
// 5 — QAOA mechanism
{
 const s=base('04 / quantum method','QAOA turns plan quality into interference','Five route decisions become five qubits; one layer has two trainable angles.');
 const stages=[['H','32-plan\nsuperposition'],['COST','RZ / RZZ\nphase γ'],['MIXER','RX rotations\nangle β'],['MEASURE','finite shots\nbitstrings']];
 stages.forEach((a,i)=>{let x=66+i*304;box(s,x,292,270,196,C.blue,18,C.line,1);box(s,x+20,315,230,62,i===3?C.coral:C.teal,12);txt(s,a[0],x+25,326,220,41,27,C.white,true,'center');txt(s,a[1],x+26,399,220,66,21,C.white,false,'center');if(i<3){txt(s,'→',x+271,350,48,55,38,C.gold,true)}});
 txt(s,'COBYLA adjusts γ and β to lower expected model energy; we then sample the trained circuit.',72,538,1130,55,22,C.muted);
 source(s,'p=1 local training: ideal statevector expectation; ideal Aer and synthetic-noise Aer sampling.');
 notes(s,'Explain QAOA physically: Hadamard gates create a superposition; the cost unitary applies objective-dependent phase; the mixer allows amplitudes to interfere; a classical optimizer picks angles. In this implementation, COBYLA trains on an ideal statevector expectation, then finite-shot measurement estimates output probabilities. Samples are decoded and feasible ones ranked by true score.','quantum_optimizer.py:105-113,179-220,268-321,357-440');
}
// 6 — product
{
 const s=base('05 / implementation','An end-to-end planning laboratory','The app ties scenario design, exact reference, QAOA, maps and reproducible reports.');
 const img=path.join(here,'screenshots/app_map.png');s.images.add({blob:new Uint8Array(await fs.readFile(img)),contentType:'image/png',alt:'Genuine Streamlit railway map screenshot',fit:'contain',position:P(70,224,455,398)});
 const steps=[['01','Select routes & budget'],['02','Build QUBO + exact reference'],['03','Train and sample QAOA'],['04','Compare maps, statistics, reports']];
 steps.forEach((a,i)=>{let y=242+i*88;box(s,583,y,615,68,C.blue,12,C.line,1);pill(s,a[0],600,y+17,55,i===3?C.coral:C.teal);txt(s,a[1],675,y+15,500,42,24,C.white,true)});
 source(s,'Screenshot: running local Streamlit app, captured 8 Nov 2026; fictional schematic edges.');
 notes(s,'This is an actual screenshot of the locally running Streamlit app. The UI supports route selection, incident toggles, simulation controls, results, history and PDF export. An HTML report exists through backend API. The map uses real city positions but fictional direct route edges. The screenshot was captured from the five-route, budget-seven scenario.','app.py; experiment.py; presentation/screenshots/app_map.png');
}
// 7 — methods
{
 const s=base('06 / experiment design','Change one axis; keep the comparison honest','Run-level JSON preserves configurations, seeds, counts, resources and optimizer status.');
 const rows=[['PRIMARY','Penalty λ','0.7 vs 4.0','3 paired seeds'],['PRECISION','Shots','256–4096','fixed trained circuit'],['SCALE','Route decisions','5 → 7 → 8','2⁵ → 2⁸ states'],['PLANNING','Budget','5 → 7 → 9','retrain per budget'],['EXECUTION','Backend','ideal vs local noise','same bound angles']];
 rows.forEach((r,i)=>{let y=224+i*77;box(s,68,y,1145,65,C.blue,12,C.line,1);txt(s,r[0],88,y+18,160,28,16,C.mint,true);txt(s,r[1],260,y+14,310,37,25,C.white,true);txt(s,r[2],590,y+18,255,30,20,C.gold);txt(s,r[3],858,y+19,315,26,17,C.muted)});
 source(s,'Local replay: p=1, COBYLA, 30 evaluation limit, 2048 shots unless shot study; 8-route compare limit.');
 notes(s,'The penalty study is the only three-seed matched comparison in the main deck. Its route set, true scoring, budget, depth, evaluation limit and shots are fixed. Shot sensitivity samples one fixed trained circuit without retraining. Budget and network-size studies retrain because the optimization problem changes. Ideal and synthetic-noise samples use the same trained angles within each run. All six penalty optimizers exhausted their evaluation budget.','presentation/run_experiments.py; presentation/source_data/experiments_summary.json');
}
// 8 — penalty result
{
 const s=base('07 / primary finding','A stronger penalty fixes the model, not sampling','Exact validity flips at λ=4; measured feasible rates move both ways across seeds.');
 const seeds=[2026,2027,2028];
 seeds.forEach((seed,i)=>{let y=269+i*104;txt(s,String(seed),80,y,100,30,22,C.white,true);let a=runs[`penalty_0_7_seed_${seed}`].samples.ideal.p_feasible,b=runs[`penalty_4_0_seed_${seed}`].samples.ideal.p_feasible;bar(s,'λ = 0.7',a,200,y-14,500,C.coral);bar(s,'λ = 4.0',b,200,y+29,500,C.mint)});
 box(s,825,248,370,290,C.blue,18,C.line,1);txt(s,'EXACT MODEL MINIMUM',852,274,315,30,17,C.muted,true);txt(s,'λ .7  →  invalid',852,337,325,40,28,C.coral,true);txt(s,'λ 4  →  valid',852,410,325,40,28,C.mint,true);txt(s,'All six optimizers hit the evaluation limit.',852,475,315,51,17,C.white);
 source(s,'Five routes, five cities, B=7, p=1, 2048 ideal shots, 30 evaluations, matched seeds.');
 notes(s,'Read paired rates by seed: λ=.7 gives 52.54%, 62.01%, 47.41%; λ=4 gives 51.07%, 45.46%, 65.43%. Changes are mixed, not a monotonic improvement. Probability of either tied true optimum likewise varies. Exact model minimum is over budget at .7 and feasible at 4. All six optimizers reported evaluation-limit exhaustion, so this is preliminary evidence, not a convergence claim. Cross-penalty absolute model energies are not comparable.','presentation/experiments/penalty_*.json; presentation/EXPERIMENT_EVIDENCE.md');
}
// 9 — shots
{
 const s=base('08 / precision','More shots narrow uncertainty','We remeasured the same trained circuit; its underlying state did not change.');
 const rows=shots.runs || shots.measurements || shots;
 const Ns=[256,1024,2048,4096];
 Ns.forEach((n,i)=>{let x=76+i*292;box(s,x,256,268,250,C.blue,16,C.line,1);txt(s,`${n}`,x+20,280,225,70,47,C.white,true);txt(s,'shots',x+20,348,200,28,18,C.muted);let band=[6.1,3.1,2.2,1.5][i];txt(s,`~±${band}%`,x+20,408,220,50,32,C.mint,true);txt(s,'95% sampling band',x+20,466,225,20,15,C.muted)});
 txt(s,'Three seeds per shot count  •  fixed γ, β and scenario  •  finite-shot P(feasible) estimates',79,545,1120,47,21,C.white);
 source(s,'Wilson intervals from presentation/source_data/shot_sensitivity.json; band shown near p≈0.5.');
 notes(s,'This is a fixed-state shot-count study, not four newly optimized circuits. Exact statevector P(feasible) is unchanged. Across three measurement seeds, observed estimates fluctuate. The displayed ~± values are approximate Wilson 95% half-widths for p near 0.5; exact run-specific intervals are preserved in source JSON. Shots, optimizer evaluations, and independent seeds are distinct resources.','presentation/source_data/shot_sensitivity.json');
}
// 10 — scale and budget
{
 const s=base('09 / scaling','Routes set qubits; cities do not','A route decision is one binary variable, so the state space grows as 2ⁿ routes.');
 const specs=[['5 routes','5 cities','32 states','baseline'],['7 routes','7 cities','128 states','local compare'],['8 routes','7 cities','256 states','current compare limit']];
 specs.forEach((a,i)=>{let x=65+i*390;box(s,x,238,360,226,C.blue,16,C.line,1);txt(s,a[0],x+22,264,315,47,34,C.white,true);txt(s,a[1],x+22,319,315,30,21,C.muted);txt(s,a[2],x+22,372,315,48,32,C.mint,true);txt(s,a[3],x+22,432,315,21,15,C.gold)});
 txt(s,'Budget 5 → 7 → 9',76,518,480,40,28,C.gold,true);txt(s,'Exact best score 11 → 15 → 20',497,518,720,40,28,C.white,true);
 source(s,'Size and budget replays: seed 2026, p=1, 2048 shots; each changed problem retrained.');
 notes(s,'Decision-space size depends on number of route variables. The seven- and eight-route scenarios both cover seven distinct cities, but require seven and eight qubits respectively. Their exact state counts are 128 and 256. The current ideal-plus-local-noise app comparison caps at eight active routes. Budget experiments hold the five-route set fixed but change B and retrain. Higher raw optimum under larger B reflects a different planning problem, not improved quantum performance.','presentation/experiments/size_*.json; presentation/experiments/budget_*.json');
}
// 11 — noise
{
 const s=base('10 / local noise','The same angles, two simulators','One baseline run shows similar finite-shot feasibility; no noise benefit follows.');
 let r=runs.penalty_0_7_seed_2026;
 metric(s,'ideal feasible',`${(100*r.samples.ideal.p_feasible).toFixed(1)}%`,76,250,340,C.mint,'2048 shots');metric(s,'synthetic noisy feasible',`${(100*r.samples.noisy.p_feasible).toFixed(1)}%`,470,250,340,C.coral,'2048 shots');metric(s,'exact best feasible','15',865,250,340,C.gold,'true score');
 box(s,76,437,1128,142,C.blue,16,C.line,1);txt(s,'Trained once → bound γ, β → sampled with Aer statevector and a local synthetic noise backend',105,460,1060,80,25,C.white,true);
 source(s,'Five routes, B=7, λ=.7, p=1, seed 2026; local GenericBackendV2 + Aer density matrix.');
 notes(s,'Within this run the ideal and synthetic-noisy measurements use the same trained QAOA angles. Ideal feasibility was 1076/2048, noisy 1086/2048. Difference is small and finite-shot uncertain. Best feasible true score was 15 for both. This noise model is local and synthetic; it is not an IBM QPU run. Noise does not improve the quantum algorithm based on one sample.','presentation/experiments/penalty_0_7_seed_2026.json');
}
// 12 — hardware path
{
 const s=base('11 / hardware path','From trained angles to physical measurements','Hardware changes mapping, depth and error profile; decoding must follow the final layout.');
 const a=[['Train','ideal expectation'],['Bind','γ / β'],['Transpile','device layout'],['IBM QPU','physical gates'],['Decode','feasible plans']];
 a.forEach((v,i)=>{let x=52+i*248;box(s,x,280,216,185,C.blue,15,C.line,1);txt(s,v[0],x+18,311,180,46,30,i===3?C.coral:C.mint,true,'center');txt(s,v[1],x+15,388,185,40,18,C.white,false,'center');if(i<4)txt(s,'→',x+213,344,46,55,34,C.gold,true)});
 txt(s,'Compare identical scenario, parameters, shots and decoded bit order wherever records permit.',73,532,1110,55,23,C.white);
 source(s,'Hardware workflow implemented separately in IBM runner; no verified counts available for this deck.');
 notes(s,'The hardware comparison requires the submitted circuit, parameter values, transpiled layout, backend, shot count and counts. Logical-to-physical mapping and bit order must be preserved when decoding. Classical enumeration is deterministic; ideal/noisy/QPU output distributions are measured. The team has a recorded hardware job identifier, but no verified completed counts.','ibm_notebook_runner.py; presentation/IBM_QPU_STATUS.md');
}
// 13 — IBM status
{
 const s=base('12 / IBM status',hardware?'Verified IBM QPU measurements':'IBM QPU measurements remain unverified',hardware?'Recovered counts passed recorded-circuit and scenario checks.':'The recorded job ID was not found in the configured IBM account at final check.');
 if(hardware){
  metric(s,'QPU feasible',`${(100*hardware.metrics.p_feasible).toFixed(1)}%`,75,251,340,C.mint,`${hardware.shots} shots`);metric(s,'optimal feasible',`${(100*hardware.metrics.p_optimal_feasible).toFixed(1)}%`,470,251,340,C.gold,'all tied optima');metric(s,'best feasible score',hardware.metrics.best_feasible_score,865,251,340,C.white,'true score');
  box(s,76,437,1128,133,C.blue,16,C.line,1);txt(s,`IBM ${hardware.backend} · job ${hardware.job_id}`,106,468,1055,62,24,C.white,true);
  source(s,'Verified result: presentation/source_data/ibm_verified_result.json. Compare with matching local run only.');
  notes(s,'These hardware counts were recovered from the recorded job and validated against preserved circuit metadata. Compare feasibility and true score with a matching 19-route local run, not the five-route examples on prior slides. The classical reference is deterministic. Inspect the verified JSON for layout, counts, transpiled depth, and metadata.','presentation/source_data/ibm_verified_result.json');
 } else {
  box(s,74,238,1127,327,C.blue,22,C.coral,2);pill(s,'NO VERIFIED COUNTS',110,269,258,C.coral);txt(s,'dbnpc00ou4as73b4u830',111,329,990,65,37,C.white,true);txt(s,'Recorded backend: ibm_marrakesh  •  4096 requested shots  •  p = 1',111,411,1010,36,23,C.muted);txt(s,'Status query: RuntimeJobNotFound for the locally configured account',111,485,1000,35,21,C.coral,true);
  source(s,'Recorded submission metadata only. No QPU success rate, score or distribution is claimed.');
  notes(s,'The archived ibm_job.json records a job ID, backend ibm_marrakesh, p=1 and 4096 shots. There is no counts file in that run folder. A read-only IBM Runtime query on 8 November 2026 returned RuntimeJobNotFound for the configured account. That may reflect account mismatch, access, or record status; it does not establish job failure or completion. No additional QPU job was submitted. The refresh command checks again without submitting a new job.','output/script_20261107_231254_822277/ibm_job.json; presentation/IBM_QPU_STATUS.md');
 }
}
// 14 — Romania roadmap
{
 const s=base('13 / future research','From a hackathon game to real Romania','A staged, source-grounded subnetwork study is the responsible next experiment.');
 const a=[['01','CFR + ERA data','validate stations, tracks'],['02','Real network graph','connectivity & constraints'],['03','Public investment case','reported costs, transparent benefit'],['04','Classical benchmark','small regional subproblem'],['05','Quantum comparison','resources, validity, limits']];
 a.forEach((v,i)=>{let x=44+i*248;box(s,x,247,222,267,C.blue,14,C.line,1);txt(s,v[0],x+18,265,184,50,37,C.mint,true);txt(s,v[1],x+17,342,188,62,22,C.white,true);txt(s,v[2],x+17,429,190,54,17,C.muted);if(i<4)txt(s,'→',x+214,347,38,54,32,C.gold,true)});
 txt(s,'CFR reports 10,615 km of lines and 896 operating points (2026 network statement annex).',72,548,1130,43,21,C.gold);
 source(s,'CFR Network Statement 2026, Annex 5; ERA RINF Romania dataset. Real project costs not inferred from distance.');
 notes(s,'This is future work, not a claim that the current app has real railway costs or network constraints. CFR Network Statement Annex 5 reports 10,615 km of lines and 896 operating points; confirm source definitions and period before analytic use. ERA RINF provides official infrastructure records but topology and licensing must be validated. Choose a manageable region, define a public-interest objective, use reported project costs, solve classically, then formulate a small quantum counterpart. Do not attempt naive nationwide QAOA.','https://cfr.ro/download-drr-2026-network-statement/ ; https://cfr.ro/files/ddr/EN%202026/Annex%205%20.pdf ; https://rinf.data.era.europa.eu/dataset-explorer ; presentation/REAL_ROMANIA_FEASIBILITY.md');
}
// 15 — conclusion
{
 const s=base('14 / conclusion','Meaningful solutions need more than low energy','Three lessons from one controlled railway optimization study.');
 const a=[['01','Exact classical reference','reveals what is truly optimal'],['02','Budget encoding','can reward an invalid model minimum'],['03','Training + sampling','shape the plans we actually see']];
 a.forEach((v,i)=>{let y=240+i*105;box(s,70,y,1130,85,C.blue,15,C.line,1);txt(s,v[0],95,y+18,82,52,35,C.mint,true);txt(s,v[1],191,y+18,430,54,27,C.white,true);txt(s,v[2],655,y+21,505,48,21,C.muted)});
 txt(s,'“Quantum optimization is about finding meaningful solutions.”',74,584,1128,51,28,C.gold,true);
 notes(s,'Close on honest scientific value: exact enumeration exposes the weak-penalty failure; stronger penalty corrects the exact five-route model minimum but does not consistently improve QAOA feasibility at three seeds; increasing shots improves estimate precision, while scale and physical noise add constraints. No quantum advantage or verified hardware result is claimed. Team Q-Force: Catalin, Artiom, Zus, Sabina, Livia.','presentation/EXPERIMENT_EVIDENCE.md; presentation/IBM_QPU_STATUS.md');
}
// 16 — appendix: QUBO / Ising
{
 const s=base('appendix a / equations','The implemented energy path','All 32 direct, QUBO and Ising energies matched numerically.');
 const lines=['E(x)=−Σ vᵢxᵢ + λ(Σ cᵢxᵢ−B)²','aᵢ=−vᵢ + λ(cᵢ²−2Bcᵢ)     bᵢⱼ=2λcᵢcⱼ','xᵢ=(1−Zᵢ)/2   →   H = const + Σ hᵢZᵢ + Σ JᵢⱼZᵢZⱼ'];
 lines.forEach((l,i)=>{box(s,78,246+i*104,1124,78,C.blue,13,C.line,1);txt(s,l,102,261+i*104,1070,50,i===1?25:29,i===2?C.mint:C.white,true)});
 source(s,'Direct/QUBO max |ΔE|=1.07×10⁻¹⁴; QUBO/Ising max |ΔE|=7.11×10⁻¹⁵.');
 notes(s,'These coefficients follow the implemented squared penalty. The direct and converted energies were checked over every five-bit state. Correct conversion does not prove the encoded minimum satisfies the original inequality.','quantum_optimizer.py; presentation/source_data/experiments_summary.json');
}
// 17 — appendix: training and depth
{
 const s=base('appendix b / resources','Training stopped at its evaluation limit','A single archived 19-route depth test is illustrative, not a general depth result.');
 metric(s,'p = 1 observed best','46',75,247,340,C.mint,'19 routes, B=20');metric(s,'p = 2 observed best','43',469,247,340,C.coral,'same archived seed');metric(s,'two-qubit gates','171 → 342',863,247,340,C.gold,'p=1 → p=2');
 box(s,76,439,1127,135,C.blue,15,C.line,1);txt(s,'One archived seed (2026)  •  30 evaluations each  •  neither optimizer converged',104,468,1050,67,23,C.white,true);
 source(s,'Tracked archive: validation/p_comparison_seed2026/comparison.json; configuration differs from five-route runs.');
 notes(s,'Do not merge this result with the five-route penalty study. It has nineteen route variables, budget 20, λ=.7, 4096 shots, and seed 2026. It is archived rather than newly rerun for this presentation. p=1 observed feasible score 46; p=2 observed 43. Compiled two-qubit gates increased from 171 to 342. Both optimizer runs exhausted their budget, so this does not show that shallower circuits generally outperform deeper circuits.','validation/p_comparison_seed2026/comparison.json');
}
// 18 — appendix: evidence map
{
 const s=base('appendix c / provenance','Every number has a source','Rebuild from frozen run JSON; refresh hardware only after verified measurements.');
 const a=[['LOCAL REPLAY','10 full run JSON files','presentation/experiments/'],['SHOT STUDY','12 fixed-state samplings','presentation/source_data/shot_sensitivity.json'],['IBM RECORD','job metadata, no counts','output/script_20261107_231254_822277/'],['REAL NETWORK','CFR + ERA sources','presentation/REAL_ROMANIA_FEASIBILITY.md']];
 a.forEach((v,i)=>{let y=226+i*96;box(s,70,y,1132,77,C.blue,13,C.line,1);txt(s,v[0],91,y+21,230,34,17,C.mint,true);txt(s,v[1],333,y+20,395,37,23,C.white,true);txt(s,v[2],744,y+24,430,27,17,C.muted)});
 source(s,'Rebuild: presentation/rebuild.ps1 · IBM read-only refresh: presentation/refresh_qpu_results.py --rebuild');
 notes(s,'Explain provenance categories clearly: executed local runs, archived tracked result, read-only IBM job record, and official external data source. The source files and rebuild scripts ship with this deck. No hardware measurement is represented by a simulated number.','presentation/README.md; presentation/EXPERIMENT_EVIDENCE.md');
}
// 19 — appendix: genuine UI captures
{
 const s=base('appendix d / live application','The app presents both quantum and exact plans','Genuine local Streamlit captures from a five-route, budget-seven run.');
 const files=[['Main interface','app_overview.png'],['Best feasible sampled','app_results.png'],['Exact classical','app_classical.png']];
 for(let i=0;i<files.length;i++){
  let x=73+i*397;box(s,x,224,350,384,C.blue,13,C.line,1);
  let data=new Uint8Array(await fs.readFile(path.join(here,'screenshots',files[i][1])));
  s.images.add({blob:data,contentType:'image/png',fit:'contain',alt:`Streamlit ${files[i][0]} screenshot`,position:P(x+13,238,324,321)});
  txt(s,files[i][0],x+17,568,318,29,18,C.white,true,'center');
 }
 source(s,'Captured from the locally running app 8 Nov 2026. UI run is separate from frozen experimental JSON.');
 notes(s,'These are genuine Streamlit UI screenshots captured during a live local run at five selected routes and budget seven. The sampled result panel reports the best feasible observed quantum plan, not the most frequent bitstring or an exact quantum guarantee. The classical panel is the exact enumeration reference. These UI captures are not used as the numerical source for the controlled penalty chart.','presentation/screenshots/app_overview.png; presentation/screenshots/app_results.png; presentation/screenshots/app_classical.png');
}

const build=path.join(here,'..','.presentation-build');await fs.mkdir(build,{recursive:true});
for(let i=0;i<p.slides.items.length;i++){let blob=await p.export({slide:p.slides.items[i],format:'png',scale:1});await fs.writeFile(path.join(build,`slide-${String(i+1).padStart(2,'0')}.png`),new Uint8Array(await blob.arrayBuffer()));}
const candidate=path.join(build,'candidate.pptx');await (await PresentationFile.exportPptx(p)).save(candidate);
const skill='C:/Users/artio/.codex/plugins/cache/openai-primary-runtime/presentations/26.1105.12137/skills/presentations';
const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const finalPath=path.join(here,'Q-Force_Quantum_Railways_Final.pptx');
const validationTarget=path.join(here,`.validated-deck-${randomUUID()}.pptx`);
let result;
try {
 result=await finalizePresentation({workspaceDir:path.join(here,'..'),candidatePath:candidate,finalPath:validationTarget,pythonExecutable:process.env.RUNTIME_PYTHON||'C:/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1105-1297-0_26.1105.1297.0_x64__3k8sg7r9htsxt/dependencies/python/python.exe',integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],explicitTotalSlideCount:19,requiredNativeTableOwnerSlides:[],requiredNativeChartOwnerSlides:[],fontPolicy:{basis:'design',families:['Arial']},verifyArtifactToolImport:true,receiptPath:path.join(build,'final.validation.json')});
 await fs.copyFile(validationTarget,finalPath);await fs.unlink(validationTarget);
 result={finalPath,finalizer:result};
} catch(error) {
 // Some managed Windows workspaces permit writing files but reject hard links.
 // The finalizer performs its checks before attempting this link.
 if(error?.code!=='EPERM' || !String(error.path||'').endsWith('.validated')) throw error;
 await fs.copyFile(candidate,finalPath);
 result={finalPath,validatedCopy:true};
}
console.log(JSON.stringify({slides:p.slides.items.length,pptx:result.finalPath||'Q-Force_Quantum_Railways_Final.pptx',result},null,2));
