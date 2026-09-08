import copy
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from enr.references import analyze, digest, image_metrics, load_pack, scene_config, write_json

ROOT = Path(__file__).resolve().parents[1]


class ReferenceTests(unittest.TestCase):
    def test_identity_has_zero_error(self):
        image = np.random.default_rng(11).integers(0, 256, (64, 80, 4), dtype=np.uint8)
        result = image_metrics(image, image)
        self.assertEqual(result['rgb_mae_8bit'], 0)
        self.assertIsNone(result['psnr_db'])
        self.assertTrue(result['alpha_exact'])
        self.assertEqual(result['alignment']['estimated_translation_px'], [0, 0])

    def test_known_translation_is_recovered(self):
        image = np.random.default_rng(4).integers(0, 256, (96, 100, 4), dtype=np.uint8)
        shifted = np.roll(image, (1, -2), axis=(0, 1))
        result = image_metrics(image, shifted)
        self.assertEqual(result['alignment']['estimated_translation_px'], [-2, 1])
        self.assertGreater(result['rgb_mae_8bit'], 0)
        self.assertGreater(result['alignment']['improvement_fraction'], .99)

    def test_brightness_drift_is_not_hidden_by_alignment(self):
        rgb = np.random.default_rng(6).integers(20, 180, (64, 80, 4), dtype=np.uint8)
        second = rgb.copy(); second[:, :, :3] += 10
        result = image_metrics(rgb, second)
        self.assertEqual(result['rgb_mae_8bit'], 10)
        self.assertEqual(result['mean_rgb_drift_8bit'], [10, 10, 10])
        self.assertEqual(result['alignment']['estimated_translation_px'], [0, 0])

    def test_shape_mismatch_and_flat_image(self):
        a = np.zeros((32, 32, 4), dtype=np.uint8)
        self.assertFalse(image_metrics(a, a)['alignment']['available'])
        with self.assertRaises(ValueError): image_metrics(a, a[:16])

    def test_pack_checks_split_leakage_and_injection(self):
        original = load_pack(ROOT/'scenes/arland-reference-v1.json')
        for mutate in [lambda p: p['scenes'][0].update(split='train'),
                       lambda p: p['scenes'][0].update(direction=[0, 0, 0]),
                       lambda p: p['defaults'].update(weather_state='Clear"; code'),
                       lambda p: p['scenes'][0].update(id='../escape')]:
            pack = copy.deepcopy(original); mutate(pack)
            with tempfile.TemporaryDirectory() as temp:
                path = Path(temp)/'pack.json'; path.write_text(json.dumps(pack))
                with self.assertRaises(ValueError): load_pack(path)

    def test_config_contains_requested_scene_time(self):
        pack = load_pack(ROOT/'scenes/arland-reference-v1.json')
        self.assertIn('Hour = 18.5;', scene_config(pack, pack['scenes'][2]))

    def fake_batch(self, root):
        path = ROOT/'scenes/arland-reference-v1.json'
        pack = load_pack(path)
        batch = {'pack_sha256': digest(path), 'status': 'succeeded', 'runs': []}
        for scene in pack['scenes']:
            for repeat in range(3):
                name = scene['id'] + '-' + str(repeat)
                directory = root/name; directory.mkdir()
                image = np.random.default_rng(42).integers(0, 256, (24, 32, 4), dtype=np.uint8)
                Image.fromarray(image).save(directory/'frame.png')
                camera = {'event': 'camera', 'position': scene['position'], 'direction': scene['direction'], 'elapsed_simulation_seconds': 8}
                run = {'run_id': name, 'status': 'succeeded', 'command': 'capture', 'world': pack['world'],
                       'events': [camera], 'image': {'sha256': digest(directory/'frame.png'), 'width': 32, 'height': 24},
                       'addon_sha256': {'adapter': 'unchanged'}}
                write_json(directory/'run.json', run)
                event = {'event': 'environment', 'date': pack['defaults']['date'], 'hour': scene['hour'],
                         'wind_speed_mps': 0, 'wind_direction_degrees': 0, 'weather_state': 'Clear'}
                (directory/'console.log').write_text('ENR '+json.dumps(event))
                batch['runs'].append({'scene_id': scene['id'], 'directory': name})
        write_json(root/'batch.json', batch)
        return path

    def test_analyzer_verifies_batch_and_detects_image_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); pack = self.fake_batch(root)
            report = analyze(pack, root/'batch.json', root/'report.json')
            self.assertEqual(len(report['scenes']), 3)
            self.assertTrue(all(s['controls_verified'] for s in report['scenes']))
            frame = root/'forest-east-noon-0/frame.png'
            frame.write_bytes(frame.read_bytes()+b'changed')
            with self.assertRaisesRegex(ValueError, 'Image changed'):
                analyze(pack, root/'batch.json', root/'second.json')

    def test_analyzer_rejects_wrong_environment_and_duplicate_runs(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); pack = self.fake_batch(root)
            console = root/'forest-east-noon-0/console.log'
            original = console.read_text()
            console.write_text(original.replace('"hour": 13', '"hour": 12'))
            with self.assertRaisesRegex(ValueError, 'Environment mismatch'):
                analyze(pack, root/'batch.json', root/'report.json')
            console.write_text(original)
            batch = json.loads((root/'batch.json').read_text())
            batch['runs'][1] = batch['runs'][0]
            write_json(root/'batch.json', batch)
            with self.assertRaisesRegex(ValueError, 'Duplicate'):
                analyze(pack, root/'batch.json', root/'report.json')


if __name__ == '__main__': unittest.main()
