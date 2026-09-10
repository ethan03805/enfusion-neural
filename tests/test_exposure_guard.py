import unittest
import numpy as np

from enr.exposure_guard import compose_constant_curve


class ExposureGuardProperties(unittest.TestCase):
    def source(self):
        # Both gain directions encounter near-endpoint channels in non-dark colors.
        palette=np.array([[0,127,200],[1,127,200],[2,127,200],[64,127,192],
                          [253,64,16],[254,64,16],[255,64,16],[127,254,253]],np.uint8)
        return np.tile(palette,(80,12,1))

    def test_extreme_valid_curves_preserve_endpoint_headroom_and_change_bound(self):
        source=self.source()
        for curve in [(-1,-1,-1),(1,1,1)]:
            output=compose_constant_curve(source,curve)
            new_endpoint=((output==0)|(output==255))&((source>0)&(source<255))
            self.assertFalse(new_endpoint.any())
            self.assertLessEqual(np.abs(output.astype(np.int16)-source).max(),15)
            self.assertFalse(np.array_equal(output,source))
            np.testing.assert_array_equal(output[:3],source[:3])
            np.testing.assert_array_equal(output[-7:],source[-7:])

    def test_zero_and_invalid_curves_return_exact_source(self):
        source=self.source()
        for curve in [(0,0,0),(np.nan,0,0),(0,np.inf,0),(0,0,-np.inf),(1.001,0,0)]:
            np.testing.assert_array_equal(compose_constant_curve(source,curve),source)

    def test_valid_odd_dimensions_keep_shape_and_finite_rgb8_output(self):
        for h,w in [(1,1),(3,7),(31,64),(79,93)]:
            source=np.random.default_rng(123).integers(0,256,(h,w,3),dtype=np.uint8)
            output=compose_constant_curve(source,(-1,-1,-1))
            self.assertEqual(output.shape,source.shape)
            self.assertEqual(output.dtype,np.uint8)
            self.assertTrue(np.isfinite(output).all())
            self.assertFalse((((output==0)|(output==255))&((source>0)&(source<255))).any())


if __name__=='__main__':
    unittest.main()
