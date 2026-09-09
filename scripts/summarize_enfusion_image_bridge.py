"""Verify one completed probe; keep UI image return distinct from renderer access."""
import argparse
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from enr.image_bridge import inspect
from enr.references import write_json


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    p.add_argument('--model',help='Exact bootstrap model used by a v0 file-return control')
    a=p.parse_args();result=inspect(a.root,a.model);write_json(a.out,result)
    print(result['verification']);print('Probe errors:',result['errors'])


if __name__=='__main__':main()
