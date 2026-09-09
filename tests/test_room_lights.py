import copy
import unittest

from enr.room_lights import check_readback


class LightReadbackTests(unittest.TestCase):
    def setUp(self):
        self.control={'case':'night-low','requested':{'native_LV':10,'enabled':True},
                      'plan':{'light':{'radius_m':15,'near_plane_m':.05,'cast_shadow':True}},
                      'world_position':[2048,1003.8,2048.2]}
        self.records=['created case=night-low requested_lv=10 requested_rgb=1,1,1 requested_attenuation=2 requested_flare=-1',
                      'readback enabled=1 shadow=1 radius=15 near=0.05 position=<2048,1003.8,2048.2>']

    def test_native_readback_does_not_certify_requested_intensity(self):
        result=check_readback(self.control,self.records)
        self.assertTrue(result['all_readbacks_match'])
        self.assertFalse(result['intensity_color_attenuation_and_clip_readback_verified'])
        moved=[self.records[0],self.records[1].replace('1003.8','1003.9')]
        self.assertFalse(check_readback(self.control,moved)['all_readbacks_match'])

    def test_negative_disabled_radius_is_not_silently_normalized(self):
        control=copy.deepcopy(self.control)
        control['requested']['enabled']=False
        records=[self.records[0],self.records[1].replace('enabled=1','enabled=0').replace('radius=15','radius=-15')]
        result=check_readback(control,records)
        self.assertEqual(result['radius_raw'],-15)
        self.assertTrue(result['radius_magnitude_matches'])
        self.assertFalse(result['all_readbacks_match'])

    def test_incomplete_wrong_and_nonfinite_records_rejected(self):
        for records in [self.records[:1], self.records+self.records[:1],
                        [self.records[0].replace('requested_lv=10','requested_lv=12'),self.records[1]],
                        [self.records[0],self.records[1].replace('radius=15','radius=1e999')]]:
            with self.subTest(records=records),self.assertRaises(ValueError):
                check_readback(self.control,records)

    def test_declared_clip_policy_requires_the_exact_native_request(self):
        control=copy.deepcopy(self.control)
        control['plan']['light']['intensity_clip_ev_bias']=-10
        self.assertTrue(check_readback(control,self.records+['clip requested_ev=-10'])['all_readbacks_match'])
        for suffix in [[], ['clip requested_ev=-9'], ['clip requested_ev=-10', 'clip requested_ev=-10']]:
            with self.subTest(suffix=suffix),self.assertRaises(ValueError):
                check_readback(control,self.records+suffix)


if __name__=='__main__':
    unittest.main()
