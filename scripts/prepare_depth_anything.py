"""Download the pinned author Depth Anything V2 Small checkpoint into ignored runs/."""
import json
from pathlib import Path
import subprocess
import sys
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest,write_json

SOURCE_REV='a561b849ebae10a6f5ef49e26c83cbbcd36c71bf'
MODEL_REV='03876f8651c73a60fe4c2c48294e09fcb6838fcf'
SHA='715fade13be8f229f8a70cc02066f656f2423a59effd0579197bbf57860e1378'
SIZE=99218434


def main():
    source=ROOT/'runs/pretrained/depth-anything-v2-source-v1'
    if not source.exists():
        subprocess.run(['git','clone','--depth','1','--filter=blob:none','--sparse','https://github.com/DepthAnything/Depth-Anything-V2.git',str(source)],check=True)
        subprocess.run(['git','-C',str(source),'sparse-checkout','set','depth_anything_v2'],check=True)
    current=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    if current!=SOURCE_REV: raise ValueError('Source revision differs; use the recorded commit in a separate checkout')
    out=ROOT/'runs/pretrained/depth-anything-v2-small-v1';out.mkdir(exist_ok=True)
    checkpoint=out/'depth_anything_v2_vits.pth'
    url=f'https://huggingface.co/depth-anything/Depth-Anything-V2-Small/resolve/{MODEL_REV}/depth_anything_v2_vits.pth'
    if not checkpoint.exists():
        with urlopen(Request(url,headers={'User-Agent':'Enfusion-Neural research reference downloader'}),timeout=60) as response, checkpoint.open('xb') as stream:
            count=0
            while True:
                block=response.read(1024*1024)
                if not block:break
                count+=len(block)
                if count>SIZE:raise ValueError('Checkpoint larger than author LFS metadata')
                stream.write(block)
    if checkpoint.stat().st_size!=SIZE or digest(checkpoint)!=SHA:raise ValueError('Checkpoint differs from pinned author LFS hash')
    source_files=sorted((source/'depth_anything_v2').rglob('*.py'))+[source/'LICENSE',source/'README.md',source/'requirements.txt']
    report={'source_repository':'https://github.com/DepthAnything/Depth-Anything-V2','source_revision':SOURCE_REV,
        'model_repository':'https://huggingface.co/depth-anything/Depth-Anything-V2-Small','model_revision':MODEL_REV,
        'checkpoint_url':url,'checkpoint_sha256':SHA,'checkpoint_bytes':SIZE,'license':'Apache-2.0 (Small model and author source)',
        'source_hashes':{p.relative_to(ROOT).as_posix():digest(p) for p in source_files},
        'driver_sha256':digest(Path(__file__)),'scope':'Download and provenance only; no inference or appearance result'}
    write_json(out/'source.json',report)
    print(json.dumps({k:report[k] for k in ['source_revision','model_revision','checkpoint_bytes','checkpoint_sha256']}))


if __name__=='__main__':main()
