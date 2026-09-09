"""Small scene-conditioned lighting residual, independent of the v0 RGB graph.

Inputs are source radiance and source/scene buffers. Targets never enter feature
construction. This CPU reference is a within-scene experiment, not a live backend.
"""
import json
from pathlib import Path
import numpy as np

FEATURES = ["log_r", "log_g", "log_b", "position_x/4", "position_y/4", "position_z/4",
            "normal_x", "normal_y", "normal_z", "albedo_r", "albedo_g", "albedo_b",
            "roughness", "metallic", "view_x", "view_y", "view_z",
            "light_offset_x/4", "light_offset_y/4", "light_offset_z/4"]
LIMIT = 0.25


def features(rgb, position, normal, material, camera, light):
    arrays = [np.asarray(value, np.float32) for value in (rgb, position, normal, material)]
    rgb, position, normal, material = arrays
    shape = rgb.shape[:-1]
    if rgb.shape[-1:] != (3,) or position.shape != rgb.shape or normal.shape != rgb.shape or material.shape != (*shape, 5):
        raise ValueError("Inconsistent source feature dimensions")
    camera, light = np.asarray(camera,np.float32), np.asarray(light,np.float32)
    if camera.shape != (3,) or light.shape != (3,) or any(not np.isfinite(a).all() for a in arrays+[camera,light]):
        raise ValueError("Nonfinite features or invalid scene vectors")
    if np.any(rgb < 0): raise ValueError("Expected nonnegative scene-linear source")
    view = camera-position
    view /= np.maximum(np.linalg.norm(view,axis=-1,keepdims=True),1e-6)
    return np.concatenate([np.log1p(rgb), position/4, normal, material, view, (light-position)/4],axis=-1)


def initialize(inputs, width=32, seed=7):
    if inputs < 1 or width < 1: raise ValueError("Invalid network dimensions")
    rng = np.random.default_rng(seed)
    return {"w1":(rng.standard_normal((inputs,width))*np.sqrt(2/inputs)).astype(np.float32),
            "b1":np.zeros(width,np.float32),
            "w2":(rng.standard_normal((width,width))*np.sqrt(2/width)).astype(np.float32),
            "b2":np.zeros(width,np.float32),
            "w3":(rng.standard_normal((width,3))*.001).astype(np.float32),
            "b3":np.zeros(3,np.float32)}


def forward(x, weights):
    z1 = x@weights["w1"]+weights["b1"]; h1 = np.maximum(z1,0)
    z2 = h1@weights["w2"]+weights["b2"]; h2 = np.maximum(z2,0)
    tanh = np.tanh(h2@weights["w3"]+weights["b3"])
    return LIMIT*tanh, (z1,h1,z2,h2,tanh)


def loss_and_grad(x, target, weights):
    prediction,(z1,h1,z2,h2,tanh) = forward(x,weights)
    error = prediction-target
    d3 = (2/error.size)*error*LIMIT*(1-tanh*tanh)
    d2 = (d3@weights["w3"].T)*(z2>0)
    d1 = (d2@weights["w2"].T)*(z1>0)
    return float(np.mean(error*error)), {"w1":x.T@d1,"b1":d1.sum(0),
        "w2":h1.T@d2,"b2":d2.sum(0),"w3":h2.T@d3,"b3":d3.sum(0)}


def fit(x,y,vx,vy,config,progress=None):
    if len(x)==0 or len(vx)==0 or x.ndim != 2 or vx.shape[1] != x.shape[1]:
        raise ValueError("Empty or incompatible training/validation features")
    if y.shape != (len(x),3) or vy.shape != (len(vx),3) or any(not np.isfinite(a).all() for a in (x,y,vx,vy)):
        raise ValueError("Invalid training targets")
    mean = x.mean(0); scale = np.maximum(x.std(0),.05)
    x = (x-mean)/scale; vx = (vx-mean)/scale
    weights = initialize(x.shape[1],config["hidden_width"],config["seed"])
    rng = np.random.default_rng(config["seed"])
    m = {k:np.zeros_like(v) for k,v in weights.items()}; v = {k:np.zeros_like(w) for k,w in weights.items()}
    best_loss = float("inf"); best = None; history = []
    for step in range(1,config["steps"]+1):
        ids = rng.integers(0,len(x),config["batch_size"])
        loss,grad = loss_and_grad(x[ids],y[ids],weights)
        for k in weights:
            m[k] = .9*m[k]+.1*grad[k]; v[k] = .999*v[k]+.001*grad[k]**2
            weights[k] -= config["learning_rate"]*(m[k]/(1-.9**step))/(np.sqrt(v[k]/(1-.999**step))+1e-8)
        if step == 1 or step%config["check_every"]==0 or step == config["steps"]:
            val = float(np.mean((forward(vx,weights)[0]-vy)**2))
            history.append({"step":step,"batch_mse":loss,"validation_mse":val})
            if val < best_loss:
                best_loss = val; best = {k:a.copy() for k,a in weights.items()}; best_step = step
            if progress: progress(history[-1])
    return {"weights":best,"mean":mean,"scale":scale,"selected_step":best_step,"history":history}


def predict(x, model, chunk=65536):
    if chunk < 1 or x.ndim != 2 or not np.isfinite(x).all(): raise ValueError("Invalid inference input")
    output = np.empty((len(x),3),np.float32)
    for start in range(0,len(x),chunk):
        stop = min(start+chunk,len(x))
        output[start:stop] = forward((x[start:stop]-model["mean"])/model["scale"],model["weights"])[0]
    return output


def save(path, model, metadata):
    columns = len(model["mean"])
    record = {"schema_version":1,"architecture":"lighting-mlp-32x32",
              "features":FEATURES[:columns],"residual_limit_log1p":LIMIT,
              "color_space":"scene-linear Rec.709; log1p residual",
              "mean":model["mean"].tolist(),"scale":model["scale"].tolist(),
              "weights":{k:v.tolist() for k,v in model["weights"].items()},"training":metadata}
    path = Path(path)
    if path.exists(): raise ValueError("Model output exists")
    path.write_text(json.dumps(record,indent=2,allow_nan=False)+"\n")


def load(path):
    record = json.loads(Path(path).read_text())
    if (record.get("schema_version") != 1 or record.get("architecture") != "lighting-mlp-32x32"
            or record.get("residual_limit_log1p") != LIMIT
            or record.get("color_space") != "scene-linear Rec.709; log1p residual"):
        raise ValueError("Unsupported lighting model contract")
    names = record.get("features")
    if names not in (FEATURES,FEATURES[:3]): raise ValueError("Unsupported feature order")
    columns = len(names)
    weights = {k:np.asarray(v,np.float32) for k,v in record["weights"].items()}
    shapes = {"w1":(columns,32),"b1":(32,),"w2":(32,32),"b2":(32,),"w3":(32,3),"b3":(3,)}
    if weights.keys() != shapes.keys() or any(weights[k].shape != shape or not np.isfinite(weights[k]).all() for k,shape in shapes.items()):
        raise ValueError("Invalid lighting weights")
    mean,scale = (np.asarray(record[k],np.float32) for k in ("mean","scale"))
    if mean.shape != (columns,) or scale.shape != (columns,) or not np.isfinite(mean).all() or not np.isfinite(scale).all() or (scale <= 0).any():
        raise ValueError("Invalid feature normalization")
    return {"weights":weights,"mean":mean,"scale":scale},record
