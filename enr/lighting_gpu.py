"""FP32 lighting shader and offline record contract; the CPU model stays independent."""
import json
from pathlib import Path

import numpy as np

from . import lighting


def dimensions(width, height):
    if (type(width) is not int or type(height) is not int or min(width, height) < 1
            or max(width, height) > 16384 or width*height > 65535*256):
        raise ValueError('Unsupported lighting dimensions')


def pack(x, rgb, alpha, valid):
    x, rgb, alpha, valid = (np.asarray(v) for v in (x, rgb, alpha, valid))
    if x.ndim != 3 or x.shape[-1] not in (3, 17, 20):
        raise ValueError('Expected an image of ordered model features')
    h, w, columns = x.shape
    dimensions(w, h)
    if rgb.shape != (h,w,3) or alpha.shape != (h,w) or valid.shape != (h,w):
        raise ValueError('Source, alpha or valid-mask shape differs')
    if any(not np.isfinite(v).all() for v in (x,rgb,alpha,valid)) or (rgb < 0).any():
        raise ValueError('Nonfinite or negative lighting source')
    if not np.isin(valid,[0,1]).all() or (alpha < 0).any() or (alpha > 1).any():
        raise ValueError('Invalid alpha or valid mask')
    x, rgb = x.astype(np.float32), rgb.astype(np.float32)
    # The log source is part of the serialized feature contract, not an optional substitute.
    if not np.array_equal(x[...,:3],np.log1p(rgb)):
        raise ValueError('Source log features differ from the original scene-linear RGB')
    if (x[...,:3] > 80).any():
        raise ValueError('Source exceeds the finite FP32 reconstruction range')
    return np.ascontiguousarray(np.concatenate([x,rgb,alpha[...,None],valid[...,None]],-1),dtype='<f4')


def reference(records, model):
    columns=len(model['mean'])
    x=records[...,:columns].reshape(-1,columns)
    residual=lighting.predict(x,model).reshape(*records.shape[:2],3)
    rgb=np.maximum(np.expm1(records[...,:3]+residual),0)
    invalid=records[...,columns+4]==0
    rgb[invalid]=records[...,columns:columns+3][invalid]
    return np.concatenate([residual,rgb,records[...,columns+3:columns+4]],-1).astype(np.float32)


def compare(actual, expected, records, limits):
    if actual.shape != expected.shape or actual.shape != (*records.shape[:2],7):
        raise ValueError('Native output size differs')
    columns=records.shape[-1]-5
    finite=bool(np.isfinite(actual).all() and np.isfinite(expected).all())
    if not finite:
        return {'passed':False,'all_outputs_finite':False}
    residual=np.abs(actual[...,:3].astype(np.float64)-expected[...,:3])
    delta=np.abs(actual[...,3:6].astype(np.float64)-expected[...,3:6])
    tolerance=limits['linear_rgb_absolute_tolerance']+limits['linear_rgb_relative_tolerance']*np.abs(expected[...,3:6])
    invalid=records[...,columns+4]==0
    alpha_exact=bool(np.array_equal(actual[...,6].view(np.uint32),records[...,columns+3].view(np.uint32)))
    fallback_exact=bool(np.array_equal(actual[...,3:6][invalid].view(np.uint32),records[...,columns:columns+3][invalid].view(np.uint32)))
    checks={'all_outputs_finite':finite,'residual_error':bool(residual.max()<=limits['maximum_absolute_residual_error']),
            'linear_rgb_error':bool(np.all(delta<=tolerance)),'alpha_bits_exact':alpha_exact,
            'invalid_source_rgb_bits_exact':fallback_exact,'bounded_residual':bool(np.abs(actual[...,:3]).max()<=lighting.LIMIT),
            'nonnegative_rgb':bool((actual[...,3:6]>=0).all())}
    return {'passed':all(checks.values()),'checks':checks,'maximum_absolute_residual_error':float(residual.max()),
            'maximum_absolute_linear_rgb_error':float(delta.max()),'mean_absolute_linear_rgb_error':float(delta.mean()),
            'maximum_linear_error_fraction_of_tolerance':float((delta/tolerance).max()),
            'invalid_pixels':int(invalid.sum()),'compared_pixels':int(invalid.size)}


def fixture(width, height, seed):
    dimensions(width,height)
    rng=np.random.default_rng(seed)
    # Broad, reproducible numerical inputs; no game assets or reference targets.
    rgb=np.expm1(rng.uniform(0,4,(height,width,3))).astype(np.float32)
    rgb.reshape(-1,3)[:min(4,width*height)]=np.array([[0,0,0],[1e-8,1e-4,.1],[1,2,4],[100,1000,10000]],np.float32)[:min(4,width*height)]
    position=rng.uniform(-8,8,(height,width,3)).astype(np.float32)
    normal=rng.normal(size=(height,width,3)).astype(np.float32)
    normal/=np.maximum(np.linalg.norm(normal,axis=-1,keepdims=True),1e-6)
    material=rng.uniform(0,1,(height,width,5)).astype(np.float32)
    x=lighting.features(rgb,position,normal,material,[1,2,3],[-2,4,1])
    alpha=rng.uniform(0,1,(height,width)).astype(np.float32)
    alpha.flat[0]=np.float32(-0.0)
    valid=np.ones((height,width),bool);valid.reshape(-1)[::7]=False
    return x,rgb,alpha,valid


def hlsl(model):
    columns=len(model['mean'])
    if columns not in (3,17,20):raise ValueError('Unsupported lighting feature count')
    def scalar(value):
        value=float(np.float32(value))
        if not np.isfinite(value):raise ValueError('Nonfinite shader constant')
        s=format(value,'.9g')
        return s if '.' in s or 'e' in s else s+'.0'
    def array(name,values):
        flat=np.asarray(values).reshape(-1)
        return 'static const float '+name+'['+str(len(flat))+'] = {'+','.join(scalar(v) for v in flat)+'};'
    lines=['cbuffer Shape : register(b0) { uint count; uint width; uint height; };',
           'StructuredBuffer<float> source : register(t0);',
           'RWStructuredBuffer<float> target : register(u0);',
           array('mean',model['mean']),array('scale',model['scale'])]
    for name,values in model['weights'].items():lines.append(array(name,values))
    lines += ['[numthreads(256,1,1)] void main(uint3 tid : SV_DispatchThreadID) {',
              'uint id=tid.x; if(id>=count) return;',f'uint base=id*{columns+5}; uint dst=id*7;',
              f'float x[{columns}]; float first[32]; float second[32];',
              f'[unroll] for(uint i=0;i<{columns};i++) x[i]=(source[base+i]-mean[i])/scale[i];',
              '[unroll] for(uint j=0;j<32;j++) { precise float sum=b1[j];',
              f'[unroll] for(uint i=0;i<{columns};i++) sum += x[i]*w1[i*32+j];',
              'first[j]=max(sum,0.0); }',
              '[unroll] for(uint j=0;j<32;j++) { precise float sum=b2[j];',
              '[unroll] for(uint i=0;i<32;i++) sum += first[i]*w2[i*32+j];',
              'second[j]=max(sum,0.0); }',
              '[unroll] for(uint j=0;j<3;j++) { precise float sum=b3[j];',
              '[unroll] for(uint i=0;i<32;i++) sum += second[i]*w3[i*3+j];',
              'float residual=0.25*tanh(sum); target[dst+j]=residual;',
              'float value=max(source[base+j]+residual,0.0);',
              # exp(x)-1 cancels near zero; the short series is accurate over this tiny interval.
              'float rgb=value<0.001 ? value*(1.0+value*(0.5+value*(0.166666667+value*0.041666667))) : exp(value)-1.0;',
              f'target[dst+3+j]=source[base+{columns+4}]==0.0 ? source[base+{columns}+j] : rgb;',
              '}',f'target[dst+6]=source[base+{columns+3}];','}']
    return '\n'.join(lines)+'\n'
