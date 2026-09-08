"""A 251-parameter residual CNN; NumPy training and reference inference.

NHWC float32 display-referred RGB. A 3x3 RGB patch is flattened in
(dy, dx, channel) order, followed by Conv(27,8), ReLU, Conv(8,3).
The bounded residual is added to the centre pixel. Alpha is untouched.
"""
import json
from pathlib import Path
import numpy as np

SHAPES = {"w1": (27, 8), "b1": (8,), "w2": (8, 3), "b2": (3,)}
LIMIT = 0.125


def initialize(seed=7):
    rng = np.random.default_rng(seed)
    return {"w1": (rng.standard_normal((27, 8)) * 0.15).astype(np.float32),
            "b1": np.zeros(8, np.float32), "w2": np.zeros((8, 3), np.float32),
            "b2": np.zeros(3, np.float32)}


def patches(rgb):
    if rgb.ndim != 3 or rgb.shape[2] != 3 or not np.isfinite(rgb).all():
        raise ValueError("Expected finite HWC RGB")
    h, w, _ = rgb.shape
    padded = np.pad(rgb, ((1, 1), (1, 1), (0, 0)), mode="edge")
    return np.stack([padded[y:y+h, x:x+w] for y in range(3) for x in range(3)], axis=2).reshape(-1, 27)


def forward(x, weights):
    z = x @ weights["w1"] + weights["b1"]
    hidden = np.maximum(z, 0)
    raw = hidden @ weights["w2"] + weights["b2"]
    bounded = np.clip(raw, -LIMIT, LIMIT)
    output = np.clip(x[:, 12:15] + bounded, 0, 1)
    return output, (z, hidden, raw, x[:, 12:15] + bounded)


def loss_and_grad(x, target, weights):
    output, (z, hidden, raw, preclip) = forward(x, weights)
    error = output - target
    delta = (2.0 / error.size) * error
    delta *= (preclip > 0) & (preclip < 1) & (raw > -LIMIT) & (raw < LIMIT)
    dh = (delta @ weights["w2"].T) * (z > 0)
    return float(np.mean(error**2)), {
        "w2": hidden.T @ delta, "b2": delta.sum(axis=0),
        "w1": x.T @ dh, "b1": dh.sum(axis=0)}


def infer(rgb, weights, rows=64):
    """Bounded-memory reference; each row tile keeps its own one-pixel halo."""
    if rows < 1:
        raise ValueError("rows must be positive")
    rgb = np.asarray(rgb, np.float32)
    if rgb.ndim != 3 or rgb.shape[2] != 3 or min(rgb.shape[:2]) < 1:
        raise ValueError("Expected nonempty HWC RGB")
    if not np.isfinite(rgb).all() or rgb.min() < 0 or rgb.max() > 1:
        raise ValueError("RGB must be finite in [0,1]")
    result = np.empty_like(rgb)
    h, w, _ = rgb.shape
    for start in range(0, h, rows):
        end = min(start + rows, h)
        lo, hi = max(0, start-1), min(h, end+1)
        block = patches(rgb[lo:hi]).reshape(hi-lo, w, 27)[start-lo:end-lo]
        result[start:end] = forward(block.reshape(-1, 27), weights)[0].reshape(end-start, w, 3)
    return result


def save(path, weights, metadata):
    data = {"schema_version": 1, "architecture": "residual-cnn-27x8x3",
            "color_space": "display-referred-rgb", "residual_limit": LIMIT,
            "weights": {k: v.tolist() for k, v in weights.items()}, "training": metadata}
    Path(path).write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (data.get("schema_version") != 1 or data.get("architecture") != "residual-cnn-27x8x3"
            or data.get("residual_limit") != LIMIT or data.get("color_space") != "display-referred-rgb"):
        raise ValueError("Unsupported model contract")
    weights = {k: np.asarray(data["weights"][k], dtype=np.float32) for k in SHAPES}
    for k, shape in SHAPES.items():
        if weights[k].shape != shape or not np.isfinite(weights[k]).all():
            raise ValueError("Invalid weights: " + k)
    return weights, data


def hlsl(weights):
    """Only validated numerical weights enter generated shader source."""
    arrays = []
    for name in SHAPES:
        values = np.asarray(weights[name], np.float32).flatten()
        if not np.isfinite(values).all() or weights[name].shape != SHAPES[name]:
            raise ValueError("Invalid shader weights")
        arrays.append("static const float %s[%d] = {%s};" %
                      (name, len(values), ",".join(format(float(v), ".9e") + "f" for v in values)))
    return "\n".join(arrays) + r'''
cbuffer Params : register(b0) { uint count; uint width; uint height; }
ByteAddressBuffer src : register(t0);
RWByteAddressBuffer dst : register(u0);
float3 rgb(uint pixel) {
    return float3(pixel & 255, (pixel >> 8) & 255, (pixel >> 16) & 255) / 255.0;
}
[numthreads(256,1,1)] void main(uint3 tid : SV_DispatchThreadID) {
    uint id = tid.x;
    if (id >= count) return;
    int x = int(id % width), y = int(id / width);
    float patch[27];
    [unroll] for (int dy=0; dy<3; ++dy) {
        [unroll] for (int dx=0; dx<3; ++dx) {
            uint at = uint(clamp(y+dy-1,0,int(height)-1))*width + uint(clamp(x+dx-1,0,int(width)-1));
            float3 c = rgb(src.Load(at*4));
            int offset = (dy*3+dx)*3;
            patch[offset]=c.r; patch[offset+1]=c.g; patch[offset+2]=c.b;
        }
    }
    float hidden[8];
    [unroll] for (int j=0; j<8; ++j) {
        float sum = b1[j];
        [unroll] for (int i=0; i<27; ++i) sum += patch[i]*w1[i*8+j];
        hidden[j] = max(0.0,sum);
    }
    uint original = src.Load(id*4);
    float3 base = rgb(original);
    uint output = original & 0xff000000;
    [unroll] for (int c=0; c<3; ++c) {
        float sum = b2[c];
        [unroll] for (int j=0; j<8; ++j) sum += hidden[j]*w2[j*3+c];
        uint channel = uint(floor(saturate(base[c]+clamp(sum,-0.125,0.125))*255.0+0.5));
        output |= channel << (8*c);
    }
    dst.Store(id*4,output);
}
'''
