import copy
import json
from pathlib import Path
import tempfile
import unittest
import sys
import numpy as np
from enr import lighting,diversity

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from summarize_lighting_diversity import summarize


class DiversityTests(unittest.TestCase):
    def setUp(self):
        self.plan=json.loads((ROOT/'scenes/lighting-diversity-v1.json').read_text())

    def test_scene_split_rejects_leakage_and_incomplete_budget(self):
        diversity.validate_plan(self.plan)
        for mutation in ('group','case','budget'):
            p=copy.deepcopy(self.plan)
            if mutation=='group':p['scenes'][-1]['group']=p['scenes'][0]['group']
            elif mutation=='case':p['cases'][0]['split']='test'
            else:p['cases'].pop()
            with self.assertRaises(ValueError):diversity.validate_plan(p)

    def test_fit_manifest_rejects_test_phase_or_additional_case(self):
        run={'status':'succeeded','phase':'fit','plan':self.plan,'cases':copy.deepcopy(self.plan['cases']),
             'scenes':{s['id']:{} for s in self.plan['scenes'] if s['split']!='test'}}
        diversity.validate_fit_run(run,self.plan)
        bad=copy.deepcopy(run);bad['phase']='test'
        with self.assertRaises(ValueError):diversity.validate_fit_run(bad,self.plan)
        bad=copy.deepcopy(run);bad['cases'].append({'split':'test'})
        with self.assertRaises(ValueError):diversity.validate_fit_run(bad,self.plan)

    def test_relative_features_ignore_global_translation(self):
        rng=np.random.default_rng(3);rgb=rng.random((3,4,3));position=rng.normal(size=rgb.shape)
        normal=np.zeros_like(rgb);normal[...,2]=1;material=rng.random((3,4,5))
        camera=np.array([0,-7,3]);light=np.array([0,1,4]);shift=np.array([8,-12,4])
        a=lighting.features(rgb,position,normal,material,camera,light)
        b=lighting.features(rgb,position+shift,normal,material,camera+shift,light+shift)
        np.testing.assert_allclose(diversity.select(a,'relative'),diversity.select(b,'relative'),atol=5e-7)
        self.assertFalse(np.allclose(diversity.select(a,'scene'),diversity.select(b,'scene')))
        np.testing.assert_array_equal(diversity.select(a,'rgb'),diversity.select(b,'rgb'))

    def test_relative_model_roundtrip_preserves_feature_identity(self):
        model={'weights':lighting.initialize(17),'mean':np.zeros(17,np.float32),'scale':np.ones(17,np.float32)}
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/'relative.json'
            lighting.save(path,model,{},feature_names=lighting.RELATIVE_FEATURES)
            restored,record=lighting.load(path)
            x=np.random.default_rng(4).normal(size=(9,17)).astype(np.float32)
            np.testing.assert_array_equal(lighting.predict(x,model),lighting.predict(x,restored))
            self.assertEqual(record['features'],lighting.RELATIVE_FEATURES)
            record['features'][3]='position_x/4';path.write_text(json.dumps(record))
            with self.assertRaises(ValueError):lighting.load(path)

    def test_selection_requires_all_variants_and_finite_validation(self):
        models={'scene':{'validation_mse':.2},'relative':{'validation_mse':.1},'rgb':{'validation_mse':.3}}
        self.assertEqual(diversity.choose_candidate(models),'relative')
        with self.assertRaises(ValueError):diversity.choose_candidate({'rgb':models['rgb']})
        models['scene']['validation_mse']=float('nan')
        with self.assertRaises(ValueError):diversity.choose_candidate(models)

    def test_fidelity_gate_rejects_contrast_even_when_mean_error_improves(self):
        losses={'source':.1,'affine-scene':.08,'affine-rgb':.09,'scene':.06}
        case={'id':'example','metrics':{n:{r:{'log1p_rmse':v} for r in ('all','object_edges','thin_posts')} for n,v in losses.items()},
              'outputs':{n:{'rgb_mae_8bit':v} for n,v in losses.items()},
              'temporal':{'coverage':{'valid_fraction':.9},'error_change':{n:{'rmse':v} for n,v in losses.items()},
                          'paired_error_change':{n:{'rmse':v} for n,v in losses.items()}},
              'paired_reference_metrics':{n:{'log1p_rmse':v} for n,v in losses.items()},
              'reference_seed_difference':{'log1p_rmse':.005},'marking_contrast':{**{n:.01 for n in losses},'reference':0}}
        result=summarize([case],'scene',self.plan['gates']);self.assertTrue(result['passed'])
        case['marking_contrast']['scene']=.025
        result=summarize([case],'scene',self.plan['gates'])
        self.assertTrue(result['gates']['spatial_improvement']);self.assertFalse(result['passed'])
        self.assertIn('marking_contrast',result['candidate_frame_failures'][0]['regions'])
        case['marking_contrast']['scene']=.01;case['paired_reference_metrics']['scene']['log1p_rmse']=.09
        result=summarize([case],'scene',self.plan['gates'])
        self.assertFalse(result['gates']['spatial_gain_resolved']);self.assertFalse(result['passed'])


if __name__=='__main__':unittest.main()
