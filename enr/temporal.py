"""Static-geometry correspondence for a recorded pinhole camera.

Blender world coordinates, camera local -Z forward/+Y up, top-down pixel arrays.
This is a diagnostic reprojection, not an engine motion-vector implementation.
"""
import numpy as np


def validate_sequence(sequence,definition,plan):
    if any(sequence.get(k)!=value for k,value in definition.items()):raise ValueError("Sequence definition changed")
    frames=sequence.get("frames",[])
    if len(frames)!=plan["frames"]:raise ValueError("Incomplete frame sequence")
    for index,frame in enumerate(frames):
        t=index/(len(frames)-1);u=t*t*(3-2*t)
        if frame["index"]!=index or abs(frame["time_seconds"]-index/plan["playback_fps"])>1e-9:
            raise ValueError("Frame order or time changed")
        for name in ("camera","light"):
            expected=(1-u)*np.asarray(plan[name+"_start"])+u*np.asarray(plan[name+"_end"])
            actual=np.asarray(frame[name])
            if actual.shape!=(3,) or not np.allclose(actual,expected,atol=1e-6,rtol=0):raise ValueError("Path differs from plan")
        matrix=np.asarray(frame["camera_matrix"])
        if matrix.shape!=(4,4) or not np.isfinite(matrix).all() or not np.allclose(matrix[3],[0,0,0,1],atol=1e-6):
            raise ValueError("Invalid camera transform")
        if not np.allclose(matrix[:3,3],frame["camera"],atol=1e-6,rtol=0) or not np.allclose(matrix[:3,:3].T@matrix[:3,:3],np.eye(3),atol=1e-5):
            raise ValueError("Camera matrix disagrees with pose")
        direction=np.asarray(plan["camera_target"],np.float64)-frame["camera"]
        if np.linalg.norm(direction)<1e-8:raise ValueError("Camera target coincides with its origin")
        direction/=np.linalg.norm(direction)
        if not np.allclose(-matrix[:3,2],direction,atol=1e-5):raise ValueError("Camera target changed")


def project(position,camera_matrix,vertical_fov_degrees):
    position=np.asarray(position,np.float64);matrix=np.asarray(camera_matrix,np.float64)
    if position.ndim!=3 or position.shape[-1]!=3 or matrix.shape!=(4,4) or not np.isfinite(position).all() or not np.isfinite(matrix).all():
        raise ValueError("Expected finite HWC positions and a 4x4 camera transform")
    if not 0 < vertical_fov_degrees < 180:raise ValueError("Invalid vertical FOV")
    h,w=position.shape[:2]
    homogeneous=np.concatenate([position,np.ones((h,w,1))],axis=-1)
    view=homogeneous@np.linalg.inv(matrix).T
    depth=-view[...,2];safe=np.where(np.abs(depth)>1e-12,depth,1e-12)
    focal=h/(2*np.tan(np.deg2rad(vertical_fov_degrees)/2))
    xy=np.stack([view[...,0]*focal/safe+w/2-.5,h/2-.5-view[...,1]*focal/safe],axis=-1)
    return xy,depth


def interior(ids):
    ids=np.asarray(ids);mask=ids>0
    padded=np.pad(ids,1,mode="edge")
    for y in range(3):
        for x in range(3):mask &= padded[y:y+ids.shape[0],x:x+ids.shape[1]]==ids
    return mask


def sample(values,xy):
    values=np.asarray(values);h,w=values.shape[:2]
    if xy.shape!=(h,w,2) or not np.isfinite(xy).all():raise ValueError("Invalid sampling coordinates")
    x=np.clip(xy[...,0],0,w-1);y=np.clip(xy[...,1],0,h-1)
    x0=np.floor(x).astype(np.int32);y0=np.floor(y).astype(np.int32)
    x1=np.minimum(x0+1,w-1);y1=np.minimum(y0+1,h-1)
    wx=x-x0;wy=y-y0
    if values.ndim==3:wx=wx[...,None];wy=wy[...,None]
    return (values[y0,x0]*(1-wx)+values[y0,x1]*wx)*(1-wy)+(values[y1,x0]*(1-wx)+values[y1,x1]*wx)*wy


def correspondence(current,previous,previous_camera,fov,tolerance=.04,normal_dot=.98):
    xy,depth=project(current["position"],previous_camera,fov)
    h,w=current["ids"].shape
    mask=interior(current["ids"]) & (depth>0) & (xy[...,0]>=0) & (xy[...,1]>=0) & (xy[...,0]<w-1) & (xy[...,1]<h-1)
    x=np.clip(np.floor(xy[...,0]),0,w-2).astype(np.int32);y=np.clip(np.floor(xy[...,1]),0,h-2).astype(np.int32)
    for dy,dx in ((0,0),(0,1),(1,0),(1,1)):
        mask &= previous["ids"][y+dy,x+dx]==current["ids"]
    error=np.linalg.norm(sample(previous["position"],xy)-current["position"],axis=-1)
    mask &= error<tolerance
    normal=sample(previous["normal"],xy)
    normal/=np.maximum(np.linalg.norm(normal,axis=-1,keepdims=True),1e-8)
    current_normal=current["normal"]/np.maximum(np.linalg.norm(current["normal"],axis=-1,keepdims=True),1e-8)
    mask &= np.sum(normal*current_normal,axis=-1)>normal_dot
    return xy,mask,{"valid_pixels":int(mask.sum()),"total_pixels":h*w,"valid_fraction":float(mask.mean()),
        "mean_world_correspondence_error_m":float(error[mask].mean()) if mask.any() else None}


def error_change(current_error,previous_error,xy,mask):
    if not np.any(mask):raise ValueError("No valid temporal correspondences")
    difference=(current_error-sample(previous_error,xy))[mask]
    return {"mae":float(np.abs(difference).mean()),"rmse":float(np.sqrt(np.mean(difference.astype(np.float64)**2)))}
