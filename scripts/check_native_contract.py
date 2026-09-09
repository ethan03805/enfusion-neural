"""Reject malformed native record/size arguments before creating a GPU device."""
import argparse
from pathlib import Path
import subprocess
import tempfile


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--exe',default='build/Release/enr_gpu.exe');a=p.parse_args()
    exe=Path(a.exe).resolve()
    with tempfile.TemporaryDirectory(prefix='enr-record-contract-') as temporary:
        root=Path(temporary);source=root/'input.bin';source.write_bytes(b'\x00'*4)
        base=[str(source),str(root/'output.bin'),str(root/'gpu.json'),'1','1',str(root/'unused.hlsl'),'0','1']
        cases=[(['1','1','0','1','lighting20'],'Input size differs'),
               (['1','1','0','1','lighting17'],'Input size differs'),
               (['1','1','0','1','lighting3'],'Input size differs'),
               (['1','1','0','1','unknown'],'Unsupported record mode'),
               (['0','1','0','1',None],'Invalid dimensions'),
               (['16385','1','0','1',None],'Invalid dimensions'),
               (['16384','16384','0','1',None],'Invalid dimensions'),
               (['-1','1','0','1',None],'Expected unsigned decimal'),
               (['1x','1','0','1',None],'Expected unsigned decimal'),
               (['1','1','101','1',None],'Invalid warmup'),
               (['1','1','0','0',None],'Invalid warmup'),
               (['2','1','0','1',None],'Input size differs')]
        for (w,h,warmup,samples,mode),expected in cases:
            args=base.copy();args[3:5]=[w,h];args[6:8]=[warmup,samples]
            if mode:args.append(mode)
            result=subprocess.run([str(exe),*args],capture_output=True,text=True,timeout=10)
            if result.returncode==0 or expected not in result.stderr or (root/'output.bin').exists() or (root/'gpu.json').exists():
                raise ValueError('Native rejection differs: '+str(args)+' '+result.stderr)
    print('Passed 12 native malformed-record checks before GPU setup.')


if __name__=='__main__':main()
