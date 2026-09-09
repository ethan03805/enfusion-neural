import unittest

from scripts.import_enfusion_material_room import require_material_sections


class RoomImportControl(unittest.TestCase):
    def test_empty_loaded_resource_is_not_a_room(self):
        # The v5 native process exited 0 and loaded a MeshObject with zero materials.
        log = '\n'.join([
            'ENR_IMPORT {"event":"mesh_loaded","resource":"room.xob"}',
            'ENR_IMPORT {"event":"materials","count":0}',
            'ENR_IMPORT {"event":"completed"}',
        ])
        with self.assertRaisesRegex(ValueError, 'no observed material sections'):
            require_material_sections(log)

    def test_missing_or_duplicate_observations_are_rejected(self):
        observed = 'ENR_IMPORT {"event":"materials","count":7}'
        require_material_sections(observed)
        for log in ('ENR_IMPORT {"event":"completed"}', observed + '\n' + observed):
            with self.assertRaises(ValueError):
                require_material_sections(log)


if __name__ == '__main__':
    unittest.main()
