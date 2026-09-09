"""Native material readback must not certify a wrong, omitted or failed map."""
import unittest

from enr.room_textures import verify_map_records


class TextureReadbackTests(unittest.TestCase):
    def setUp(self):
        self.bcr = '{1234567890ABCDEF}Assets/ENR_OriginalTextures/metal_BCR.edds'
        self.nmo = '{FEDCBA0987654321}Assets/ENR_OriginalTextures/metal_NMO.edds'
        self.materials = [{'name': 'metal', 'bcr': self.bcr, 'nmo': self.nmo},
                          {'name': 'default', 'bcr': None, 'nmo': None}]
        self.records = ['slot=metal bcr_read=1 bcr=' + self.bcr + ' 0 nmo_read=1 nmo=' + self.nmo + ' 0',
                        'slot=default bcr_read=1 bcr= nmo_read=1 nmo=']

    def test_preserves_resource_suffix_and_empty_default(self):
        result = verify_map_records(self.records, self.materials)
        self.assertEqual(result['metal']['bcr']['native_raw'], self.bcr + ' 0')
        self.assertEqual(result['metal']['bcr']['native_suffix'], ' 0')
        self.assertIsNone(result['default']['bcr']['resource'])

    def test_rejects_wrong_map_failed_read_and_unknown_suffix(self):
        for line in [self.records[0].replace(self.bcr, self.nmo),
                     self.records[0].replace('bcr_read=1', 'bcr_read=0'),
                     self.records[0].replace(self.bcr + ' 0', self.bcr + ' 1'),
                     self.records[0].replace(self.bcr + ' 0', self.bcr)]:
            with self.subTest(line=line), self.assertRaises(ValueError):
                verify_map_records([line, self.records[1]], self.materials)

    def test_rejects_omitted_duplicate_and_unexpected_materials(self):
        for records in [self.records[:1], self.records + self.records[:1],
                        [self.records[0], self.records[1].replace('default', 'other')]]:
            with self.subTest(records=records), self.assertRaises(ValueError):
                verify_map_records(records, self.materials)


if __name__ == '__main__':
    unittest.main()
