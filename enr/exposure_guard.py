"""Independent NumPy reference for the source-preserving DCE composition.

This is an offline numerical reference, not part of the live GPU frame path.
The historical CPU full-composition rounding discrepancy remains documented.
"""
import numpy as np


def smoothstep(low, high, value):
    t = np.clip((value-low)/(high-low), 0, 1)
    return t*t*(3-2*t)


def compose_constant_curve(rgb, curve, strength=.35):
    """Reference for fixed-curve saturation/fallback fixtures, RGB8 in/out."""
    source = np.asarray(rgb, dtype=np.float32)/np.float32(255)
    r = np.asarray(curve, dtype=np.float32)
    if not np.isfinite(r).all() or np.any(np.abs(r)>1):
        return np.asarray(rgb).copy()
    mapped = source.copy()
    for _ in range(8):
        mapped += r*(mapped*mapped-mapped)
    coefficients = np.array([.2126,.7152,.0722],np.float32)
    luminance = np.sum(source*coefficients,axis=2)
    target = np.sum(mapped*coefficients,axis=2)
    gain = np.clip(target/np.maximum(luminance,.001),.85,1.4)
    maximum = source.max(axis=2)
    # Limit the scale by both absolute RGB change and available source headroom.
    change = np.clip((gain-1)*strength,-.06/np.maximum(maximum,.001),.06/np.maximum(maximum,.001))
    headroom = np.maximum(np.float32(254/255)-maximum,0)/np.maximum(maximum,.001)
    change = np.minimum(change,headroom)
    h,w = source.shape[:2]
    u = (np.arange(w,dtype=np.float32)+.5)/w
    v = (np.arange(h,dtype=np.float32)+.5)/h
    protection = smoothstep(.03,.1,luminance)*(1-smoothstep(.7,.9,luminance))
    protection *= (smoothstep(.045,.1,v)*(1-smoothstep(.84,.91,v)))[:,None]
    center = np.maximum(np.abs(u[None,:]-.5)/.018,np.abs(v[:,None]-.5)/.025)
    protection *= smoothstep(1,2,center)
    result = source*(1+change*protection)[:,:,None]
    if not np.isfinite(result).all():
        raise ValueError('Nonfinite composed fixture')
    return np.rint(np.clip(result,0,1)*255).astype(np.uint8)
