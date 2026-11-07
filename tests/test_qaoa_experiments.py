import json
from pathlib import Path
import tempfile
import unittest

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from examples.demo_qaoa import DEMO_ROUTES
from qaoa_experiments import draw_qaoa_layers, run_depth_comparison, comparison_rows, plot_depth_comparison
from quantum_optimizer import construct_qubo


class DepthComparisonTests(unittest.TestCase):
    def test_drawings_match_real_circuit_resources(self):
        q=construct_qubo(DEMO_ROUTES,7,.7)
        for depth in (1,2):
            fig=draw_qaoa_layers(q,depth)
            self.assertEqual(fig.qaoa_resources,dict(p=depth,qubits=5,parameters=2*depth,
                                                    rz=5*depth,rzz=10*depth,rx=5*depth))
            self.assertEqual(len(fig.axes[0].lines),5)
            plt.close(fig)

    def test_paired_training_and_saved_outputs(self):
        workspace=Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory(dir=workspace) as directory:
            self.assertEqual(Path(directory).resolve().parent,workspace.resolve())
            results=run_depth_comparison(DEMO_ROUTES[:2],3,.7,maxiter=6,shots=32,
                                          output_dir=directory,progress=None)
            self.assertEqual(set(results),{1,2})
            rows=comparison_rows(results)
            self.assertEqual(len(rows),2)
            for depth,result in results.items():
                self.assertEqual(result['statistici']['qaoa_depth'],depth)
                self.assertEqual(len(result['unghiuri_optime']),2*depth)
                self.assertEqual(sum(result['counts'].values()),32)
                self.assertLessEqual(result['cost_total'],3)
                self.assertTrue((Path(directory)/f'circuit_p{depth}.png').is_file())
                saved=json.loads((Path(directory)/f'p{depth}.json').read_text(encoding='utf-8'))
                self.assertEqual(saved,result)
            self.assertEqual(results[1]['referinta_clasica'],results[2]['referinta_clasica'])
            self.assertTrue((Path(directory)/'comparatie.png').is_file())
            fig=plot_depth_comparison(results); self.assertEqual(len(fig.axes),4); plt.close(fig)

    def test_depth_validation(self):
        for depths in ((),(0,),(True,),(1,1),(1.5,)):
            with self.assertRaises(ValueError):
                run_depth_comparison(DEMO_ROUTES,7,depths=depths,progress=None)

    def test_notebook_uses_comparison_and_exposes_both_depths(self):
        p=Path(__file__).resolve().parents[1]/'Quantum_Railways_Labb.ipynb'
        notebook=json.loads(p.read_text(encoding='utf-8'))
        sources=[''.join(c['source']) for c in notebook['cells'] if c['cell_type']=='code']
        for source in sources: compile(source,'notebook','exec')
        self.assertTrue(any('qaoa_results=run_depth_comparison' in s and 'depths=(1,2)' in s for s in sources))
        self.assertTrue(any('draw_qaoa_layers(qubo,p=depth)' in s for s in sources))
        self.assertTrue(any('p2_result=qaoa_results[2]' in s for s in sources))


if __name__=='__main__': unittest.main()
