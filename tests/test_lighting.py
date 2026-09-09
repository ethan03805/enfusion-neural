import unittest
import tempfile
import json
import hashlib
from pathlib import Path
import numpy as np
from enr import lighting


class LightingTests(unittest.TestCase):
    def test_gradients(self):
        rng = np.random.default_rng(2)
        x = rng.normal(size=(9,5)).astype(np.float64)
        y = rng.normal(0,.05,size=(9,3))
        weights = {k:v.astype(np.float64) for k,v in lighting.initialize(5,7).items()}
        weights["w3"] *= 50
        _, gradients = lighting.loss_and_grad(x,y,weights)
        for key,value in weights.items():
            for index in rng.choice(value.size,min(5,value.size),replace=False):
                old = value.flat[index]; epsilon = 1e-6
                value.flat[index] = old+epsilon
                high = lighting.loss_and_grad(x,y,weights)[0]
                value.flat[index] = old-epsilon
                low = lighting.loss_and_grad(x,y,weights)[0]
                value.flat[index] = old
                self.assertAlmostEqual((high-low)/(2*epsilon),gradients[key].flat[index],delta=1e-7)

    def test_feature_contract(self):
        rgb = np.ones((3,7,3),np.float32)
        x = lighting.features(rgb,np.zeros_like(rgb),np.zeros_like(rgb),np.zeros((3,7,5)),[0,0,2],[4,0,0])
        self.assertEqual(x.shape,(3,7,20))
        np.testing.assert_allclose(x[...,:3],np.log(2),rtol=1e-6)
        np.testing.assert_equal(x[...,14:17],np.broadcast_to([0,0,1],(3,7,3)))
        np.testing.assert_equal(x[...,17:],np.broadcast_to([1,0,0],(3,7,3)))
        with self.assertRaises(ValueError):
            lighting.features(-rgb,np.zeros_like(rgb),np.zeros_like(rgb),np.zeros((3,7,5)),[0,0,2],[4,0,0])

    def test_inference_partition_and_bound(self):
        x = np.random.default_rng(3).normal(size=(113,20)).astype(np.float32)
        model = {"weights":lighting.initialize(20),"mean":np.zeros(20,np.float32),"scale":np.ones(20,np.float32)}
        a = lighting.predict(x,model,chunk=11); b = lighting.predict(x,model,chunk=200)
        np.testing.assert_allclose(a,b,atol=1e-8,rtol=1e-5)
        self.assertLessEqual(float(np.abs(a).max()),lighting.LIMIT)
        with self.assertRaises(ValueError): lighting.predict(x*np.nan,model)

    def test_saved_model_and_contract(self):
        model = {"weights":lighting.initialize(20),"mean":np.zeros(20,np.float32),"scale":np.ones(20,np.float32)}
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/"model.json"
            lighting.save(path,model,{"scope":"test"})
            restored,record = lighting.load(path)
            x = np.random.default_rng(4).normal(size=(11,20)).astype(np.float32)
            np.testing.assert_array_equal(lighting.predict(x,model),lighting.predict(x,restored))
            record["features"][0] = "reference_r"
            path.write_text(json.dumps(record))
            with self.assertRaises(ValueError): lighting.load(path)

    def test_committed_models_match_report(self):
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root/"evidence/lighting-study-v1.json").read_text())
        for kind,name in (("scene","lighting-v1.json"),("rgb","lighting-rgb-v1.json")):
            path = root/"models"/name
            model,record = lighting.load(path)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),report["model_files"][kind])
            self.assertEqual(sum(w.size for w in model["weights"].values()),report["models"][kind]["parameters"])
            self.assertTrue(set(record["training"]["train_cases"]).isdisjoint(record["training"]["validation_cases"]))


if __name__ == "__main__": unittest.main()
