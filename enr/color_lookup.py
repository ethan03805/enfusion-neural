"""Verify the original 16-cube lookup import; not a general EDDS decoder."""
import json
from pathlib import Path
import re
import struct

import numpy as np
from PIL import Image
from .references import digest


def lz4_block(data, expected):
    # Original implementation of https://github.com/lz4/lz4/blob/dev/doc/lz4_Block_format.md
    if not 0 <= expected <= 16384 or len(data) > 20000: raise ValueError('Block exceeds fixture bounds')
    out=bytearray(); index=0
    def length(value):
        nonlocal index
        if value == 15:
            while True:
                if index >= len(data): raise ValueError('Truncated LZ4 length')
                extra=data[index]; index+=1; value+=extra
                if value > expected: raise ValueError('LZ4 length exceeds output')
                if extra != 255: break
        return value
    while index < len(data):
        token=data[index]; index+=1; literals=length(token >> 4)
        if index+literals > len(data) or len(out)+literals > expected: raise ValueError('Invalid literals')
        out.extend(data[index:index+literals]); index+=literals
        if index == len(data): break
        if index+2 > len(data): raise ValueError('Missing match offset')
        offset=int.from_bytes(data[index:index+2],'little'); index+=2
        if offset == 0 or offset > len(out): raise ValueError('Invalid match offset')
        count=length(token & 15)+4
        if len(out)+count > expected: raise ValueError('Match exceeds output')
        for _ in range(count): out.append(out[-offset])
    if len(out) != expected: raise ValueError('Decoded size differs')
    return bytes(out)


def decode_volume(data):
    if len(data)<136 or data[:4]!=b'DDS ' or data[36:40]!=b'ENF1': raise ValueError('Expected original DDS/ENF1')
    word=lambda offset: struct.unpack_from('<I',data,offset)[0]
    if (word(4),word(12),word(16),word(20),word(24),word(28)) != (124,16,16,64,16,1):
        raise ValueError('Unexpected lookup dimensions, pitch or mip count')
    if tuple(word(o) for o in [76,80,84,88,92,96,100,104,112]) != (32,65,0,32,0xff0000,0xff00,0xff,0xff000000,0x200000):
        raise ValueError('Expected BGRA8 volume masks')
    tag=data[128:132]; size=word(132)
    if size != len(data)-136: raise ValueError('Container payload size differs')
    if tag == b'COPY': pixels=data[136:]
    elif tag == b'LZ4 ':
        if len(data)<144 or word(136)!=16384 or word(140)!=(0x80000000 | (len(data)-144)):
            raise ValueError('Unsupported LZ4 fixture wrapper')
        pixels=lz4_block(data[144:],16384)
    else: raise ValueError('Unsupported original lookup payload')
    if len(pixels)!=16384: raise ValueError('Volume payload size differs')
    return np.frombuffer(pixels,dtype=np.uint8).reshape(16,16,16,4)[...,[2,1,0,3]].copy(),tag.decode().strip()


def verify_pixels(data, source):
    volume,encoding=decode_volume(data)
    source=np.asarray(source)
    if source.shape!=(16,256,4) or source.dtype!=np.uint8: raise ValueError('Invalid original lattice source')
    expected=source.reshape(16,16,16,4).transpose(1,0,2,3)
    if not np.array_equal(volume,expected): raise ValueError('Compiled volume differs from original RGBA lattice')
    return {'dimensions':[16,16,16],'source_dimensions':[256,16],'mips':1,'format':'BGRA8',
            'encoding':encoding,'exact_rgba_lattice_match':True,
            'scope':'Original fixture bytes and axis layout only; engine lookup sampling and color stage unverified'}


def load_build(root, repository):
    root=Path(root).resolve(); repository=Path(repository); path=root/'build.json'
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    report=read(path)
    if report['status']!='succeeded' or report['operation']!='color-lookup-build': raise ValueError('Incomplete lookup build')
    plan_path=repository/'scenes/color-lookup-control-v1.json'
    if report['plan_sha256']!=digest(plan_path) or report['plan']!=read(plan_path): raise ValueError('Lookup plan changed')
    if report['plan']['volume_edge']!=16 or report['plan']['texture_import']!={'Conversion':'None','ColorSpace':'ToLinear','GenerateMips':0,'VolumeTexture':1}:
        raise ValueError('Unsupported fixture import contract')
    for key, hash_key, command in [('run_id','manifest_sha256','color-lookup-build'),('validation_run','validation_manifest_sha256','validate')]:
        if not re.fullmatch(r'[0-9]{8}T[0-9]{6}-[a-f0-9]{10}',report[key]): raise ValueError('Invalid build run name')
        manifest=root/'runs'/report[key]/'run.json'; native=read(manifest)
        if digest(manifest)!=report[hash_key] or native['status']!='succeeded' or native['command']!=command: raise ValueError('Build provenance differs')
        if command=='validate' and native['process_exit_code']!=0: raise ValueError('Invalid compile validation')
        if command=='color-lookup-build' and (not native['alive_after_build_observation'] or native['stable_output_observation_seconds']<10): raise ValueError('Build stopped prematurely')
    folder=root/'runs'/report['run_id']; assets=folder/'addon/Assets/ENR_ColorLookup'
    for name,key in [('console.log','console_sha256'),('driver.py','driver_sha256'),('addon/Scripts/WorkbenchGame/ENR_TextureBuildPlugin.c','plugin_sha256')]:
        if digest(folder/name)!=report[key]: raise ValueError('Build snapshot changed')
    log=(folder/'console.log').read_text(encoding='utf-8')
    if log.count('Build successful')<3 or log.count('ENR_TEXTURE queued=3')!=1: raise ValueError('Build observations missing')
    copies=[];names=set()
    for item in report['retained_assets']:
        file=(assets/item['file']).resolve()
        if not file.is_relative_to(assets) or file in names or digest(file)!=item['sha256']: raise ValueError('Build asset changed or escaped')
        names.add(file); copies.append((file,item['file']))
    if len(copies)!=9 or [v['case'] for v in report['identities']]!=report['plan']['textures']: raise ValueError('Missing/duplicate lookup controls')
    checks=[]
    for item in report['identities']:
        if item['name']!=item['case']+'_lut' or item['source']!=item['name']+'.tif': raise ValueError('Unexpected lookup name')
        if not re.fullmatch(r'\{[0-9A-F]{16}\}Assets/ENR_ColorLookup/'+item['name']+r'\.edds',item['resource']): raise ValueError('Invalid resource name')
        source=assets/item['source']; metadata=(assets/(item['name']+'.edds.meta')).read_text()
        if digest(source)!=item['source_sha256'] or 'Name "'+item['resource']+'"' not in metadata: raise ValueError('Source or metadata differs')
        check=verify_pixels((assets/(item['name']+'.edds')).read_bytes(),np.asarray(Image.open(source)))
        checks.append({'case':item['case'],**check})
    return report,copies,{'build_report_sha256':digest(path),'run_id':report['run_id'],'manifest_sha256':report['manifest_sha256'],'volume_checks':checks}


def check_requests(records,table,case,priority,suffix,log):
    expected=['none'] if case=='off' else ['apply','remove'] if case=='removed' else ['apply']
    requests=[v.split('=',1)[1] for v in records if v.startswith('requested=')]
    errors=[line.strip() for line in log.splitlines() if 'Cannot set ColorGradingEffect' in line]
    actual=[v for v in records if v.startswith('material_class=')]
    target='material_class=ColorGradingEffect table_read=1 table='+table+suffix+' enabled_read=1 enabled=1'
    starts=[v for v in records if v.startswith('case=')]
    checks={'request_order':requests==expected,'native_readback':actual==([] if case=='off' else [target]),
            'single_initialization':len(starts)==1 and re.fullmatch(r'case='+re.escape(case)+r' camera=\d+ priority='+str(priority),starts[0]) is not None,
            'no_explicit_engine_rejection':not errors,'no_script_failure':not any(v.startswith('failed=') for v in records)}
    return {'checks':checks,'passed':all(checks.values()),'raw_readback':actual,'engine_rejections':errors,
            'scope':'Requested call and container readback; visible response and correct color mapping require pixel evidence'}
