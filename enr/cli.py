import argparse
import hashlib
import json
import platform
import subprocess
import time
from pathlib import Path
import numpy as np
from PIL import Image
from . import __version__, data, model


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+"\n", encoding="utf-8")


def quantize(rgb):
    return np.floor(np.clip(rgb,0,1)*255 + .5).astype(np.uint8)


def train(args):
    output = Path(args.out)
    if output.exists():
        raise ValueError("Output exists; choose a new model path")
    x,y = data.training_set(range(12))
    vx,vy = data.training_set(range(100,104))
    weights = model.initialize(args.seed)
    rng = np.random.default_rng(args.seed)
    m = {k: np.zeros_like(v) for k,v in weights.items()}
    v = {k: np.zeros_like(value) for k,value in weights.items()}
    baseline = float(np.mean((vx[:,12:15]-vy)**2))
    history = []
    started = time.perf_counter()
    for step in range(1, args.steps+1):
        ids = rng.integers(0,len(x),1024)
        loss, grads = model.loss_and_grad(x[ids],y[ids],weights)
        for k in weights:
            m[k] = .9*m[k] + .1*grads[k]
            v[k] = .999*v[k] + .001*grads[k]**2
            weights[k] -= .002*(m[k]/(1-.9**step))/(np.sqrt(v[k]/(1-.999**step))+1e-8)
        if step == 1 or step % 100 == 0 or step == args.steps:
            val = float(np.mean((model.forward(vx,weights)[0]-vy)**2))
            history.append({"step":step,"batch_mse":loss,"validation_mse":val})
            print(json.dumps(history[-1]), flush=True)
    metadata = {"seed":args.seed,"steps":args.steps,"optimizer":"Adam", "learning_rate":.002,
        "training_device":"CPU / NumPy", "train_scene_seeds":list(range(12)),
        "validation_scene_seeds":list(range(100,104)), "test_scene_seeds":[200,201,202,203],
        "degradation":"bicubic 0.5x then bicubic upsample; display RGB8",
        "baseline_validation_mse":baseline,"history":history,
        "seconds":time.perf_counter()-started, "numpy":np.__version__,
        "license":"MIT; original procedural fixtures", "production_ready":False}
    output.parent.mkdir(parents=True, exist_ok=True)
    model.save(output,weights,metadata)
    print(json.dumps({"model":str(output),"sha256":sha(output),"baseline_validation_mse":baseline}))


def evaluate(args):
    output = Path(args.out)
    output.mkdir(parents=True, exist_ok=False)
    weights, metadata = model.load(args.model)
    results=[]
    for seed in [200,201,202,203]:
        clean=data.fixture(seed,256)
        baseline=data.degrade(clean)
        reference=np.asarray(clean,np.float32)/255
        prediction=model.infer(np.asarray(baseline,np.float32)/255,weights)
        def metrics(value):
            mse=float(np.mean((value-reference)**2))
            return {"mse":mse,"psnr_db":float(-10*np.log10(max(mse,1e-15)))}
        results.append({"scene_seed":seed, "bicubic":metrics(np.asarray(baseline,np.float32)/255),
                        "neural":metrics(prediction)})
        clean.save(output/f"{seed}-reference.png")
        baseline.save(output/f"{seed}-bicubic.png")
        Image.fromarray(quantize(prediction)).save(output/f"{seed}-neural.png")
    write_json(output/"evaluation.json", {"schema_version":1,"model_sha256":sha(args.model),
               "scope":"held-out procedural fixtures; not Enfusion quality or an FSR comparison",
               "results":results})
    print(json.dumps(results,indent=2))


def benchmark(args):
    started=time.perf_counter()
    weights,_=model.load(args.model)
    if args.image:
        with Image.open(args.image) as im:
            if im.mode not in {"RGB", "RGBA", "L", "LA", "P"}:
                raise ValueError("Only display-referred 8-bit images are supported; convert HDR explicitly")
            rgba=np.asarray(im.convert("RGBA")).copy()
        source_hash=sha(args.image)
        source_kind="external image (no quality ground truth)"
    else:
        im=data.fixture(200,256).resize((args.width,args.height),Image.Resampling.BICUBIC)
        rgba=np.asarray(im.convert("RGBA")).copy()
        source_hash=hashlib.sha256(rgba.tobytes()).hexdigest()
        source_kind="procedural fixture resized for dispatch measurement"
    h,w=rgba.shape[:2]
    if min(w,h) < 1 or max(w,h) > 16384 or w*h > 65535*256:
        raise ValueError("Unsupported dimensions")
    out=Path(args.out)
    out.mkdir(parents=True,exist_ok=False)
    Image.fromarray(rgba).save(out/"input.png")
    rgba.tofile(out/"input.rgba")
    shader=out/"model.hlsl"
    shader.write_text(model.hlsl(weights),encoding="utf-8")
    pipeline_start=time.perf_counter()
    subprocess.run([str(Path(args.exe).resolve()),str((out/"input.rgba").resolve()),
        str((out/"output.rgba").resolve()),str((out/"gpu.json").resolve()),str(w),str(h),str(shader.resolve()),
        str(args.warmup),str(args.samples)],check=True,timeout=120)
    actual=np.fromfile(out/"output.rgba",dtype=np.uint8).reshape(h,w,4)
    gpu=json.loads((out/"gpu.json").read_text())
    Image.fromarray(actual).save(out/"output.png")
    pipeline_ms=1000*(time.perf_counter()-pipeline_start)
    reference_start=time.perf_counter()
    expected=quantize(model.infer(rgba[:,:,:3].astype(np.float32)/255,weights))
    delta=np.abs(actual[:,:,:3].astype(np.int16)-expected.astype(np.int16))
    alpha_equal=bool(np.array_equal(actual[:,:,3],rgba[:,:,3]))
    report={"schema_version":1,"software_version":__version__,"python":platform.python_version(),
        "model_sha256":sha(args.model),"shader_sha256":sha(shader), "input_sha256":source_hash,
        "source_kind":source_kind,"dimensions":[w,h],"backend":"native D3D12 / FP32 HLSL",
        "rgb_max_error_8bit":int(delta.max()),"rgb_mean_error_8bit":float(delta.mean()),
        "alpha_exact":alpha_equal,"cpu_reference_pass":bool(delta.max()<=1 and alpha_equal),
        "neural_changed_rgb_values":int(np.count_nonzero(actual[:,:,:3]!=rgba[:,:,:3])),
        "file_pipeline_all_dispatches_ms":pipeline_ms,"total_dispatches":args.warmup+args.samples,
        "cpu_reference_ms":1000*(time.perf_counter()-reference_start),
        "total_ms":1000*(time.perf_counter()-started),"gpu":gpu,
        "limitations":["offline", "not game frame time", "no capture-to-present timing",
                       "no live memory budget measurement", "no FSR comparison"]}
    write_json(out/"run.json",report)
    print(json.dumps({k:v for k,v in report.items() if k!="gpu"},indent=2))
    if not report["cpu_reference_pass"]:
        raise RuntimeError("GPU result failed CPU reference validation")


def main():
    parser=argparse.ArgumentParser(description="Offline neural reconstruction experiments")
    commands=parser.add_subparsers(dest="command",required=True)
    p=commands.add_parser("train"); p.add_argument("--out",required=True)
    p.add_argument("--steps",type=int,default=1200); p.add_argument("--seed",type=int,default=7)
    p.set_defaults(run=train)
    p=commands.add_parser("evaluate"); p.add_argument("--model",required=True); p.add_argument("--out",required=True)
    p.set_defaults(run=evaluate)
    p=commands.add_parser("benchmark"); p.add_argument("--model",required=True); p.add_argument("--out",required=True)
    p.add_argument("--exe",default="build/Release/enr_gpu.exe"); p.add_argument("--image")
    p.add_argument("--width",type=int,default=2560); p.add_argument("--height",type=int,default=1440)
    p.add_argument("--warmup",type=int,default=10); p.add_argument("--samples",type=int,default=100)
    p.set_defaults(run=benchmark)
    args=parser.parse_args()
    if getattr(args,"steps",1)<1:
        parser.error("steps must be positive")
    if not 0 <= getattr(args,"warmup",0) <= 100 or not 1 <= getattr(args,"samples",1) <= 1000:
        parser.error("warmup must be 0–100; samples must be 1–1000")
    try:
        args.run(args)
    except (ValueError, OSError, RuntimeError, subprocess.SubprocessError) as error:
        parser.exit(1,str(error)+"\n")


if __name__=="__main__":
    main()
