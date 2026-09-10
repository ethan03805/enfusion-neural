"""Collect verified application measurements without changing their raw scope."""
import hashlib
import json
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    names=['bench-town-'+p+'-v4' for p in ['standard','scale','shadows','effects','combined','combined-neural']]
    names+=['bench-town-standard-neural-v1','bench-town-combined-neural-display-v1']
    names+=['video-town-'+p+'-v1' for p in ['standard','combined','neural']]
    names+=['video-foliage-'+p+'-v1' for p in ['standard','combined','neural']]+['video-evening-neural-v1']
    reports=[]
    for name in names:
        file=ROOT/'runs'/name/'analysis.json'
        if not file.exists(): continue
        report=json.loads(file.read_text())
        if not report['configuration_verified']: raise ValueError('Unverified preset: '+name)
        report['analysis_sha256']=sha(file)
        reports.append(report)
        if report['scene']=='foliage':
            report['scene_limit']='The walking input reaches a solid fence and cannot complete the intended distance. Much of the measured period is stationary against cover. Reduced-only path differs by up to 1.87 metres around a tree. Retained collision/visibility sample, not an accepted matched moving-foliage benchmark.'
    def positions(report):
        trace=report['path']; t=[r['simulation_s'] for r in trace]
        return np.stack([np.interp(np.arange(31,60),t,[r['camera'][k] for r in trace]) for k in range(3)],axis=1)
    for r in reports:
        baseline=next((b for b in reports if b['scene']==r['scene'] and b['preset']=='standard' and b['mode']=='off' and b['recording']==r['recording']),None)
        if baseline:
            drift=np.linalg.norm(positions(r)-positions(baseline),axis=1)
            r['path_repeat']={'reference':baseline['run'],'scope':'Camera distance at interpolated simulation seconds 31..59, including head movement; no image registration or retiming','median_metres':float(np.median(drift)),'max_metres':float(max(drift))}
    record={'schema_version':1,'date':'2026-09-10','hardware':'AMD Radeon RX 7800 XT, 16 GiB, local Windows PC','output_dimensions':[2560,1440],
            'method':'One fixed 30-second local controlled-player path per configuration, 20 seconds forward through engine CharacterForward action then 10 seconds heading sweep. Requested settings verified by runtime numeric readback. No texture, geometry or vegetation reductions. CPU traces count only DXGI non-null application swapchains, excluding WGC internal events. Recording passes are separate.',
            'statistical_limit':'Single pass per configuration; no confidence interval or broad-scene generalization. Present-call cadence is not necessarily displayed frame cadence.',
            'processing':{'precision':'FP32','curve_dimensions':[320,180],'model_sha256':sha(ROOT/'runs/pretrained/zero-dce-plusplus/weights.bin'),'measured_town_binary_sha256':sha(ROOT/'runs/companion-measured-build-v1/enr_companion.exe'),'later_binary_sha256':sha(ROOT/'build/Release/enr_companion.exe'),'binary_change':'C++20 and statically linked C++ runtime; added run metadata/help. Neural shader unchanged; rebuilt numerical parity max error 7.4505806e-08.'},
            'latency_limit':'Moving-path PresentMon display traces remain unavailable after one display-only retry. Earlier 895-frame capture-to-display sample is retained separately in playable-live-v1.json; it is not full physical input latency.',
            'runs':reports}
    (ROOT/'evidence/playable-comparison-v1.json').write_text(json.dumps(record,indent=2))
    old=ROOT/'evidence/playable-town-baseline-v1.json'
    data=json.loads(old.read_text()); data.update(configuration_verified=False,configuration_scope='Historical engine-default sample. Requested standard profile was ignored because it was placed one directory too high. Do not use as the corrected standard baseline.')
    old.write_text(json.dumps(data,indent=2))
    for r in reports:
        print(r['run'], 'game',round(r['game'].get('mean_fps',0),2),'companion',round(r['companion'].get('mean_fps',0),2),'path_max_m',round(r.get('path_repeat',{}).get('max_metres',0),3))


if __name__=='__main__': main()
