"""Regression for Blender's separate Combined/Depth/Normal/Object Index EXR parts."""
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scripts.check_material_room import read_exr


class MaterialRoomPasses(unittest.TestCase):
    def parts(self):
        groups = [("Combined","RGBA"),("Depth","Z"),("Normal","XYZ"),("Object Index","X")]
        return [SimpleNamespace(channels={"ViewLayer."+name+"."+component:
                SimpleNamespace(pixels=np.ones((4,6),np.float32)) for component in components})
                for name,components in groups]

    def read(self,parts):
        def open_file(path,separate_channels):
            self.assertTrue(separate_channels)
            return nullcontext(SimpleNamespace(parts=parts))
        with patch.dict("sys.modules",{"OpenEXR":SimpleNamespace(File=open_file)}):
            return read_exr(Path("fixture.exr"))

    def test_reads_all_four_parts(self):
        result=self.read(self.parts())
        self.assertEqual(len(result),9)
        self.assertIn("ViewLayer.Object Index.X",result)

    def test_rejects_missing_duplicate_nonfinite_or_misaligned_passes(self):
        with self.assertRaisesRegex(ValueError,"Missing"):self.read(self.parts()[:1])
        parts=self.parts()
        with self.assertRaisesRegex(ValueError,"Duplicate"):self.read(parts+[parts[0]])
        parts=self.parts();parts[1].channels["ViewLayer.Depth.Z"].pixels[0,0]=np.nan
        with self.assertRaisesRegex(ValueError,"Nonfinite"):self.read(parts)
        parts=self.parts();parts[1].channels["ViewLayer.Depth.Z"].pixels=np.ones((3,6),np.float32)
        with self.assertRaisesRegex(ValueError,"dimensions"):self.read(parts)


if __name__ == "__main__":unittest.main()
