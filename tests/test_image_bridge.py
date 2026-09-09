"""CPU file protocol controls; these tests do not certify Workbench presentation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from enr import model

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bridge_probe',ROOT/'scripts/probe_enfusion_image_bridge.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)


class ImageBridgeControls(unittest.TestCase):
    def test_file_controls_preserve_alpha_and_cpu_model_at_odd_dimensions(self):
        source=np.random.default_rng(23).integers(0,256,(7,11,4),dtype=np.uint8)
        weights,_=model.load(ROOT/'models/bootstrap-v0.json')
        for mode in ('identity','invert','v0'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as name:
                folder=Path(name);Image.fromarray(source).save(folder/'bridge-input.png')
                report=bridge.process_image(folder,mode)
                actual=np.array(Image.open(folder/'bridge-output.png'))
                expected=source.copy()
                if mode=='invert':expected[...,:3]=255-source[...,:3]
                if mode=='v0':expected[...,:3]=np.floor(model.infer(source[...,:3].astype(np.float32)/255,weights,rows=3)*255+.5).astype(np.uint8)
                np.testing.assert_array_equal(actual,expected)
                self.assertTrue(report['alpha_exact'])
                self.assertEqual(report['dimensions'],[11,7])
                self.assertEqual(json.loads((folder/'bridge-worker.json').read_text())['output_sha256'],bridge.digest(folder/'bridge-output.png'))
                self.assertTrue((folder/'bridge-worker.done').is_file())

    def test_rejects_implicit_color_conversion(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name);Image.new('RGB',(11,7)).save(folder/'bridge-input.png')
            with self.assertRaises(ValueError):bridge.process_image(folder,'identity')
            self.assertFalse((folder/'bridge-worker.done').exists())
