import unittest
import numpy as np

from enr import lighting,lighting_gpu,diversity


class LightingGPUContract(unittest.TestCase):
    def setUp(self):
        self.model={'weights':lighting.initialize(20),'mean':np.zeros(20,np.float32),'scale':np.ones(20,np.float32)}
        self.limits={'maximum_absolute_residual_error':1e-5,'linear_rgb_absolute_tolerance':2e-5,'linear_rgb_relative_tolerance':2e-5}
        self.records=lighting_gpu.pack(*lighting_gpu.fixture(13,7,123))

    def test_pack_rejects_wrong_source_log_mask_and_nonfinite(self):
        x,rgb,alpha,valid=lighting_gpu.fixture(13,7,123)
        for index in (0,1,2,3):
            values=[v.copy().astype(np.float32) for v in (x,rgb,alpha,valid)]
            values[index].flat[-1]=np.nan
            with self.assertRaises(ValueError):lighting_gpu.pack(*values)
        wrong=x.copy();wrong[1,1,0]+=.01
        with self.assertRaises(ValueError):lighting_gpu.pack(wrong,rgb,alpha,valid)
        wrong_mask=valid.astype(np.float32);wrong_mask[1,1]=.5
        with self.assertRaises(ValueError):lighting_gpu.pack(x,rgb,alpha,wrong_mask)
        for shape in [(0,1),(16385,1),(16384,16384),(True,1)]:
            with self.assertRaises(ValueError):lighting_gpu.dimensions(*shape)

    def test_comparison_rejects_fallback_alpha_residual_and_nonfinite_corruption(self):
        expected=lighting_gpu.reference(self.records,self.model)
        self.assertTrue(lighting_gpu.compare(expected,expected,self.records,self.limits)['passed'])
        for channel,amount in [(0,.001),(3,.01),(6,.01)]:
            actual=expected.copy();actual[0,0,channel]+=amount
            self.assertFalse(lighting_gpu.compare(actual,expected,self.records,self.limits)['passed'])
        actual=expected.copy();actual[0,0,6]=0.0
        self.assertFalse(lighting_gpu.compare(actual,expected,self.records,self.limits)['passed'])
        actual=expected.copy();actual[0,0,3]=np.nan
        self.assertFalse(lighting_gpu.compare(actual,expected,self.records,self.limits)['passed'])

    def test_all_variants_keep_feature_order_and_original_fallback(self):
        x,rgb,alpha,valid=lighting_gpu.fixture(13,7,123)
        for variant in ('scene','relative','rgb'):
            columns=len(diversity.names(variant))
            model={'weights':lighting.initialize(columns),'mean':np.zeros(columns,np.float32),'scale':np.ones(columns,np.float32)}
            records=lighting_gpu.pack(diversity.select(x,variant),rgb,alpha,valid)
            output=lighting_gpu.reference(records,model)
            self.assertTrue(np.array_equal(output[...,3:6][~valid].view(np.uint32),rgb[~valid].view(np.uint32)))
            self.assertTrue(np.array_equal(output[...,6].view(np.uint32),alpha.view(np.uint32)))
            self.assertTrue(lighting_gpu.compare(output,output,records,self.limits)['passed'])

    def test_single_ulp_bound_escape_fails_even_inside_numeric_tolerance(self):
        expected=lighting_gpu.reference(self.records,self.model);expected[0,0,0]=.25
        actual=expected.copy();actual[0,0,0]=np.nextafter(np.float32(.25),np.float32(1))
        result=lighting_gpu.compare(actual,expected,self.records,self.limits)
        self.assertTrue(result['checks']['residual_error'])
        self.assertFalse(result['checks']['bounded_residual'])
        self.assertFalse(result['passed'])

    def test_finite_float64_feature_cannot_overflow_during_packing(self):
        x,rgb,alpha,valid=lighting_gpu.fixture(13,7,123)
        oversized=x.astype(np.float64);oversized[2,3,4]=1e100
        with self.assertRaisesRegex(ValueError,'finite FP32'):
            lighting_gpu.pack(oversized,rgb,alpha,valid)


if __name__=='__main__':unittest.main()
