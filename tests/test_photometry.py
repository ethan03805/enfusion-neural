import copy
import unittest
import numpy as np
from enr.photometry import fit_response, gain_for_mean, patch, response_gain, srgb_code


class PhotometryTests(unittest.TestCase):
    def test_transfer_and_invalid_radiance(self):
        np.testing.assert_allclose(srgb_code(np.array([0,.0031308,1,2])),[0,.040449936*255,255,255],atol=1e-9)
        for value in [-.01,float('nan'),float('inf')]:
            with self.assertRaises(ValueError):srgb_code([value])
        with self.assertRaises(ValueError):gain_for_mean(np.zeros((2,2,3)),np.zeros((2,2,3)))
        with self.assertRaises(ValueError):patch(np.zeros((3,4,3)),[0,0,5,2])

    def test_fit_cannot_read_validation_images_or_independent_patches(self):
        reference=np.full((2,2,3),.04)
        plan={'fit_cases':['a','c','e'],'validation_cases':['b','d'],
              'cases':{n:{'enabled':True,'native_LV':lv} for n,lv in zip('abcde',range(8,13))},
              'patches':{'fit':{'xyxy':[0,0,1,1],'split':'fit'},'check':{'xyxy':[1,1,2,2],'split':'validation'}}}
        images={n:srgb_code(reference,2**(.5*p['native_LV']-4)) for n,p in plan['cases'].items()}
        fit=fit_response(reference,images,plan)
        self.assertAlmostEqual(fit['slope'],.5,places=10)
        self.assertAlmostEqual(fit['intercept'],-4,places=10)
        self.assertAlmostEqual(response_gain(fit,9),2**.5,places=10)
        for n in plan['fit_cases']:images[n][1,1]=255
        del images['b'];del images['d']
        self.assertEqual(fit,fit_response(reference,images,plan))
        invalid=copy.deepcopy(plan);invalid['validation_cases'][0]='a'
        with self.assertRaises(ValueError):fit_response(reference,images,invalid)


if __name__=='__main__':unittest.main()
