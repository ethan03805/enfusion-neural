import json
import hashlib
import tempfile
import unittest
from pathlib import Path
import numpy as np
from enr import data, model


class ModelTests(unittest.TestCase):
    def test_committed_model_matches_evidence(self):
        root=Path(__file__).parents[1]
        digest=hashlib.sha256((root/'models/bootstrap-v0.json').read_bytes()).hexdigest()
        for name in ['gpu-1440p','gpu-arland','evaluation-v0']:
            report=json.loads((root/'evidence'/f'{name}.json').read_text())
            self.assertEqual(digest,report['model_sha256'])

    def test_zero_residual_is_identity_at_edges_and_odd_sizes(self):
        rng=np.random.default_rng(30)
        for h,w in [(1,1),(1,7),(9,1),(17,31),(129,5)]:
            rgb=rng.random((h,w,3),dtype=np.float32)
            np.testing.assert_array_equal(model.infer(rgb,model.initialize()),rgb)

    def test_tiled_inference_matches_full_convolution(self):
        rng=np.random.default_rng(45)
        rgb=rng.random((131,19,3),dtype=np.float32)
        weights=model.initialize()
        weights['w2'][:]=rng.normal(0,.02,(8,3))
        expected=model.forward(model.patches(rgb),weights)[0].reshape(rgb.shape)
        np.testing.assert_allclose(model.infer(rgb,weights,rows=7),expected,atol=1e-7)

    def test_gradients_match_finite_differences(self):
        rng=np.random.default_rng(11)
        weights={k:v.astype(np.float64) for k,v in model.initialize().items()}
        weights['b1'][:]=.5
        weights['w2'][:]=rng.uniform(-.01,.01,(8,3))
        x=rng.uniform(.2,.8,(13,27)); y=rng.uniform(.2,.8,(13,3))
        _,gradient=model.loss_and_grad(x,y,weights)
        eps=1e-5
        for key in weights:
            for index in [0,weights[key].size-1]:
                old=weights[key].flat[index]
                weights[key].flat[index]=old+eps
                plus=model.loss_and_grad(x,y,weights)[0]
                weights[key].flat[index]=old-eps
                minus=model.loss_and_grad(x,y,weights)[0]
                weights[key].flat[index]=old
                self.assertAlmostEqual((plus-minus)/(2*eps),gradient[key].flat[index],places=7)

    def test_bound_and_nonfinite_input(self):
        rgb=np.full((3,4,3),.5,np.float32)
        weights=model.initialize(); weights['b2'][:]=[1,-1,0]
        np.testing.assert_allclose(model.infer(rgb,weights)[0,0],[.625,.375,.5])
        rgb[0,0,0]=np.nan
        with self.assertRaises(ValueError): model.infer(rgb,weights)

    def test_model_roundtrip_and_contract_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.json'
            model.save(path,model.initialize(),{'seed':7})
            weights,_=model.load(path)
            np.testing.assert_array_equal(weights['w1'],model.initialize()['w1'])
            value=json.loads(path.read_text()); value['weights']['w1'][0][0]=float('nan')
            path.write_text(json.dumps(value))
            with self.assertRaises(ValueError): model.load(path)

    def test_learned_weights_improve_validation_fixture(self):
        weights,_=model.load(Path(__file__).parents[1]/'models/bootstrap-v0.json')
        x,y=data.training_set([100],1024)
        self.assertLess(np.mean((model.forward(x,weights)[0]-y)**2),np.mean((x[:,12:15]-y)**2))


if __name__=='__main__': unittest.main()
