import struct
import unittest
import numpy as np
from enr.color_lookup import lz4_block,verify_pixels


class LookupImportTests(unittest.TestCase):
    def test_lz4_overlap_and_corrupt_lengths_offsets(self):
        self.assertEqual(lz4_block(b'\x1bA\x01\x00\x50hello',21), b'A'*16+b'hello')
        for block,size in [(b'\xf0',15),(b'\x10A\x00\x00',5),(b'\x10A\x02\x00',5),(b'\x1bA\x01\x00\x50hello',20)]:
            with self.assertRaises(ValueError): lz4_block(block,size)

    def test_volume_axis_and_channel_corruption_are_rejected(self):
        header=bytearray(128);header[:4]=b'DDS ';header[36:40]=b'ENF1'
        for offset,value in {4:124,12:16,16:16,20:64,24:16,28:1,76:32,80:65,84:0,88:32,92:0xff0000,96:0xff00,100:0xff,104:0xff000000,112:0x200000}.items():struct.pack_into('<I',header,offset,value)
        z,y,x=np.indices((16,16,16)); volume=np.stack([x*17,y*17,z*17,np.full_like(x,255)],axis=-1).astype(np.uint8)
        source=volume.transpose(1,0,2,3).reshape(16,256,4)
        data=bytes(header)+b'COPY'+struct.pack('<I',16384)+volume[...,[2,1,0,3]].tobytes()
        self.assertTrue(verify_pixels(data,source)['exact_rgba_lattice_match'])
        broken=bytearray(data);broken[150]^=1
        for candidate in [bytes(broken),data[:-1],data[:24]+struct.pack('<I',1)+data[28:]]:
            with self.assertRaises(ValueError):verify_pixels(candidate,source)
        with self.assertRaises(ValueError):verify_pixels(data,volume.reshape(16,256,4))


if __name__=='__main__':unittest.main()
