"""Freeze the source-headroom correction before changing the live compositor."""
from datetime import datetime, timedelta
import itertools
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def main():
    out = ROOT/'runs/dce-channel-guard-v1'
    out.mkdir(parents=True, exist_ok=True)
    if (out/'plan.json').exists():
        raise FileExistsError('A frozen plan already exists')
    old = ROOT/'runs/dce-temporal-native-v2'
    parent = json.loads((old/'report.json').read_text())
    if parent['status'] != 'completed' or len(parent['frames']) != 600:
        raise ValueError('Original replay is incomplete')
    text = (ROOT/'native/companion.cpp').read_text()
    shader = re.search(r'const char \*shader = R"\((.*?)\)";', text, re.S).group(1)
    if shader != (old/'companion.hlsl').read_text():
        raise ValueError('Original compositor changed')
    shutil.copyfile(old/'companion.hlsl',out/'original.hlsl')
    shutil.copyfile(ROOT/'native/companion.cpp',out/'original-companion.cpp')
    shutil.copyfile(ROOT/'build/Release/enr_dce_replay.exe',out/'enr_dce_replay.exe')
    shutil.copyfile(__file__,out/'prepare-driver.py')
    values = [0,1,2,16,64,127,192,240,250,253,254,255]
    palette = np.array(list(itertools.product(values, repeat=3)),dtype=np.uint8)
    yy,xx = np.mgrid[:1440,:2560]
    source = palette[((xx//32)+(yy//20)*80)%len(palette)]
    Image.fromarray(source).save(out/'fixture-source.png')
    started = datetime.fromisoformat('2026-09-10T13:05:15+00:00')
    paths = ['native/companion.cpp','native/curve_network.h','native/dce_replay.cpp',
             'scripts/evaluate_dce_temporal.py','runs/dce-temporal-native-v2/report.json',
             'runs/dce-temporal-native-v2/source-timestamps.json','runs/dce-temporal-native-v2/curves.npy',
             'runs/dce-temporal-native-v2/residuals.npy','runs/dce-temporal-native-v2/clipping-diagnostic.json',
             'runs/pretrained/zero-dce-plusplus/weights.bin','runs/pretrained/zero-dce-plusplus/Epoch99.pth',
             'runs/pretrained/zero-dce-plusplus/model.py','runs/foliage-walk-reduced-v1/gameplay.mp4',
             'runs/companion-input-final-v1/source.bmp','runs/companion-input-final-v1/output.bmp',
             'runs/companion-input-final-v1/curve.f32']
    plan = {
        'schema_version':1,'started_at':started.isoformat(),'maximum_minutes':30,
        'preparation_failures':'Two preparation attempts stop before writing a plan: Python 3.9 Path.write_text does not accept newline; explicit LF then differs from the saved CRLF shader bytes. Retain both drivers. Compare extracted shader text, then copy the original HLSL bytes unchanged. Retain the original 13:05:15 start. No live shader change or evaluation precedes this correction.',
        'deadline':(started+timedelta(minutes=30)).isoformat(),
        'source_hashes':{p:digest(ROOT/p) for p in paths},
        'retained_originals':{p.name:digest(p) for p in [out/'original.hlsl',out/'original-companion.cpp',out/'enr_dce_replay.exe',out/'fixture-source.png']},
        'parent_plan':json.loads((ROOT/'scenes/playable-dce-temporal-native-v2.json').read_text()),
        'correction':'Limit positive common RGB gain using the maximum source channel and a 254/255 output ceiling. A source already at 254 or 255 has no positive headroom. Keep the existing negative bound, strength .35, source positions, feathering and nonfinite fallback. No model or history change.',
        'formula':'After the existing deltaGain cap and before protect: deltaGain = min(deltaGain, max(0, (254/255 - maxc) / max(maxc, .001))). The half-code margin before RGB8 rounding prevents a new 255 endpoint; negative common gain remains at least .9475 at strength .35, so source code 1 cannot round to 0.',
        'fixture':{'dimensions':[2560,1440],'values':values,'colors':len(palette),'layout':'32x20 pixel tiles in raster order, palette repeated; includes protected HUD/crosshair positions and all 1728 combinations of twelve boundary/intensity codes.',
            'curves':{'bright':[-1,-1,-1],'dark':[1,1,1],'identity':[0,0,0],'invalid_range':[1.01,0,0],'invalid_nan':['nan',0,0],'invalid_inf':['inf',0,0]},
            'injection':'Replace only the curve sample expression in a diagnostic shader with the declared constant. Same native compositor/compile path; model still runs but its output is ignored only in these fixtures. Keep original and guarded fixture outputs.'},
        'gates':{'newly_endpoint_clipped_channels':0,'rgb8_source_change_max':15,'protected_region_rgb8_error_max':0,
            'cpu_curve_max_error':.0001,'fixture_cpu_rgb8_max_error':1,
            'temporal':json.loads((ROOT/'scenes/playable-dce-temporal-native-v2.json').read_text())['gates']},
        'controls':'Original native snapshot and all 600 original output/curve hashes must reproduce exactly. Independent CPU curve reference remains required. Invalid/zero fixture curves must return exact source. Bright original fixture must demonstrate new clipping; guarded fixture must remove it. Record CPU full-composition differences without relabeling the prior failed mean tolerance.',
        'segment':'Every original frame and timestamp from [18,28) seconds, reserve [25,28); original source-only flow/masks and limits. Preserve all per-frame raw-output hashes, scalar checks and residual fields, four native-size source/original/guarded keys, and original failures.',
        'review':'Inspect all six complete fixture output pairs, source atlas, all four complete native gameplay source/original/guarded keys, plus ten chronological contact samples. No full real-time perceptual review claim.',
        'scope':'Offline correction and validation only, game stopped. No live performance or appearance-gain claim. Retain failed candidates. A pass requires a separate bounded live validation before replacing the download.'
    }
    write_json(ROOT/'scenes/playable-dce-channel-guard-v1.json',plan)
    write_json(out/'plan.json',plan)
    print(json.dumps({'started_at':plan['started_at'],'deadline':plan['deadline'],'plan_sha256':digest(out/'plan.json')}))


if __name__=='__main__':
    main()
