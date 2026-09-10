"""Guard the isolated settings boundary and modules with nested instances."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('playable_launcher', ROOT/'scripts/launch_playable.py')
launcher = importlib.util.module_from_spec(spec); spec.loader.exec_module(launcher)


class PlayableSettingsTests(unittest.TestCase):
    def test_nested_instance_changes_only_requested_field(self):
        text = 'EngineUserSettings {\n DisplayUserSettings DisplayUserSettings "{guid}" {\n  PPQuality PPEffectsSettings "{other}" {\n   SSDO 1\n   SSR 2\n  }\n }\n VideoUserSettings VideoUserSettings {\n  SSR 7\n }\n}\n'
        result = launcher.set_field(text,'PPEffectsSettings','SSR',0)
        self.assertIn('SSDO 1',result)
        self.assertIn('SSR 0',result)
        self.assertIn('SSR 7',result)

    def test_missing_module_fails(self):
        with self.assertRaises(ValueError): launcher.set_field('EngineUserSettings {}','Absent','Field',1)

    def test_malformed_braces_fail(self):
        with self.assertRaises(ValueError): launcher.set_field('VideoUserSettings VideoUserSettings {\n','VideoUserSettings','Vsync',0)

    def test_profile_is_nested_and_source_unchanged(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root/'original/app_fixture/settings/ReforgerEngineSettings.conf'
            source.parent.mkdir(parents=True)
            text = 'EngineUserSettings {\n VideoUserSettings VideoUserSettings {\n  ResolutionScale 1\n }\n PipelineUserSettings PipelineUserSettings {\n  ShadowQuality High\n }\n DisplayUserSettings DisplayUserSettings {\n  PPQuality PPEffectsSettings {\n   SSDO 1\n   SSR 1\n  }\n }\n}\n'
            source.write_text(text)
            out = root/'session'
            launcher.prepare(out,'town','combined',False,source)
            file = out/'profile/profile/.save/app_fixture/settings/ReforgerEngineSettings.conf'
            self.assertTrue(file.exists())
            self.assertIn('ResolutionScale 0.75',file.read_text())
            self.assertIn('SSDO 0',file.read_text())
            self.assertEqual(text,source.read_text())
            with self.assertRaises(FileExistsError): launcher.prepare(out,'town','standard',False,source)


if __name__ == '__main__': unittest.main()
