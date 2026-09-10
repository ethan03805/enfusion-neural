import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('playable_trace', Path(__file__).resolve().parents[1]/'scripts/playable_trace.py')
trace = importlib.util.module_from_spec(spec); spec.loader.exec_module(trace)


class PresentEvidenceTests(unittest.TestCase):
    def test_capture_internal_events_are_not_output_frames(self):
        self.assertFalse(trace.application_present({'Runtime':'Other','SwapChainAddress':'0x0000000000000000'}))
        self.assertFalse(trace.application_present({'Runtime':'DXGI','SwapChainAddress':'0x0'}))
        self.assertTrue(trace.application_present({'Runtime':'DXGI','SwapChainAddress':'0x123'}))

    def test_loss_is_visible_in_both_presentmon_log_encodings(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory)/'trace.log'
            for encoding in ['utf-16','utf-8-sig']:
                file.write_text('warning: 200 ETW events were lost.',encoding=encoding)
                self.assertIn('ETW events were lost',trace.read_trace_log(file))


if __name__=='__main__': unittest.main()
