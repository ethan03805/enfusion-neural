"""An explicit candidate display mapping, fitted only on declared calibration data."""
import numpy as np


def srgb_code(linear, gain=1):
    values=np.asarray(linear,dtype=np.float64)
    if not np.isfinite(values).all() or np.any(values<0) or not np.isfinite(gain) or gain<=0:
        raise ValueError('Expected nonnegative finite radiance and positive scalar gain')
    values=np.clip(values*gain,0,1)
    return 255*np.where(values<=.0031308,12.92*values,1.055*values**(1/2.4)-.055)


def patch(image, rectangle):
    image=np.asarray(image)
    x0,y0,x1,y1=rectangle
    if (image.ndim!=3 or image.shape[2]!=3 or any(type(v)!=int for v in rectangle)
            or not 0<=x0<x1<=image.shape[1] or not 0<=y0<y1<=image.shape[0]):
        raise ValueError('Invalid RGB patch bounds or image shape')
    return image[y0:y1,x0:x1]


def gain_for_mean(reference, target):
    reference=np.asarray(reference,dtype=np.float64);target=np.asarray(target,dtype=np.float64)
    if (reference.shape!=target.shape or reference.size==0 or not np.isfinite(target).all()
            or np.any(target<0) or np.any(target>255)):
        raise ValueError('Incompatible calibration images')
    desired=float(target.mean())
    low,high=-20.,20.
    if not srgb_code(reference,2**low).mean()<desired<srgb_code(reference,2**high).mean():
        raise ValueError('Calibration mean is dark, saturated or outside declared gain bounds')
    for _ in range(64):
        middle=(low+high)/2
        if srgb_code(reference,2**middle).mean()<desired:low=middle
        else:high=middle
    return 2**((low+high)/2)


def fit_response(reference, images, plan):
    names=plan['fit_cases'];validation=plan['validation_cases']
    if (len(names)!=3 or len(set(names))!=3 or len(validation)!=2 or len(set(validation))!=2
            or set(names)&set(validation) or set(names+validation)-set(plan['cases'])):
        raise ValueError('Calibration cases must have distinct fit/validation partitions')
    rectangles=[p['xyxy'] for p in plan['patches'].values() if p['split']=='fit']
    if len(rectangles)!=1:raise ValueError('Expected one declared fit patch')
    source=patch(reference,rectangles[0]);fits=[]
    for name in names:
        if not plan['cases'][name]['enabled']:raise ValueError('Cannot fit a disabled light')
        target=patch(images[name],rectangles[0]);gain=gain_for_mean(source,target)
        fits.append({'case':name,'native_LV':plan['cases'][name]['native_LV'],'scalar_gain':gain,
            'source_mean_linear':float(source.mean()),'engine_mean_rgb8':float(target.mean()),
            'clipped_fraction':float(np.mean((target<=1)|(target>=254))),
            'single_gain_patch_mae_rgb8':float(np.abs(srgb_code(source,gain)-target).mean())})
    lv=np.asarray([f['native_LV'] for f in fits],dtype=np.float64)
    if len(set(lv))!=3 or not np.isfinite(lv).all():raise ValueError('Distinct finite fit intensities required')
    coefficients=np.linalg.lstsq(np.stack([lv,np.ones_like(lv)],axis=1),np.log2([f['scalar_gain'] for f in fits]),rcond=None)[0]
    return {'slope':float(coefficients[0]),'intercept':float(coefficients[1]),'fits':fits,
            'scope':'Candidate sRGB display/gain curve; does not prove native engine transfer or physical light units'}


def response_gain(fit, native_lv):
    gain=2**(fit['slope']*native_lv+fit['intercept'])
    if not np.isfinite(gain) or gain<=0:raise ValueError('Invalid response gain')
    return gain
