"""Exercise real hardware correctness. CI can explicitly skip absent hardware."""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--allow-no-gpu',action='store_true')
    args=parser.parse_args()
    for w,h in [(1,1),(1,17),(31,1),(127,65),(1920,1080),(3840,2160)]:
        with tempfile.TemporaryDirectory() as name:
            directory=Path(name)
            rgba=np.random.default_rng(w+h).integers(0,256,(h,w,4),dtype=np.uint8)
            Image.fromarray(rgba).save(directory/'input.png')
            command=[sys.executable,'-m','enr.cli','benchmark','--model','models/bootstrap-v0.json',
                     '--image',str(directory/'input.png'),'--out',str(directory/'run')]
            result=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
            if result.returncode:
                if args.allow_no_gpu and 'No hardware D3D12 FL12_0 adapter' in result.stderr:
                    print('SKIPPED: no hardware D3D12 adapter; no GPU correctness claim')
                    return
                print(result.stdout); print(result.stderr,file=sys.stderr)
                raise SystemExit(result.returncode)
            report=json.loads((directory/'run/run.json').read_text())
            if not report['cpu_reference_pass'] or not report['alpha_exact']:
                raise SystemExit('GPU parity failure')
            print(f"PASS {w}x{h}: max RGB error {report['rgb_max_error_8bit']}; random alpha exact",flush=True)


if __name__=='__main__': main()
