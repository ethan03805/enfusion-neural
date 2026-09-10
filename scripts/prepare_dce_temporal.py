"""Freeze a bounded paired-frame diagnostic of the existing live DCE pass."""
from datetime import datetime, timedelta, timezone
import json
import re
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def main():
    if '--native-replay' in sys.argv:
        return amend_native()
    out = ROOT / 'runs/dce-temporal-v1'
    out.mkdir(parents=True, exist_ok=False)
    depth = json.loads((ROOT / 'scenes/playable-depth-motion-v1.json').read_text())
    if digest(ROOT / depth['source']) != depth['source_sha256']:
        raise ValueError('Changed source video')
    paths = [depth['source'], 'runs/depth-motion-v1/source-timestamps.json',
             'runs/pretrained/zero-dce-plusplus/Epoch99.pth',
             'runs/pretrained/zero-dce-plusplus/model.py',
             'runs/pretrained/zero-dce-plusplus/weights.bin',
             'runs/companion-input-final-v1/source.bmp',
             'runs/companion-input-final-v1/output.bmp',
             'runs/companion-input-final-v1/curve.f32',
             'runs/companion-input-final-v1/run.json',
             'native/companion.cpp', 'native/curve_network.h']
    now = datetime.now(timezone.utc)
    plan = {
        'schema_version': 1, 'started_at': now.isoformat(), 'maximum_minutes': 30,
        'deadline': (now + timedelta(minutes=30)).isoformat(),
        'source': depth['source'], 'segment_seconds': [18,28], 'reserved_start_seconds': 25,
        'source_dimensions': [2560,1440], 'curve_dimensions': [320,180],
        'source_hashes': {p:digest(ROOT/p) for p in paths},
        'model': 'Pinned unchanged author Zero-DCE++ Epoch99, FP32 CPU, scale_factor=1 on bilinear 320x180 RGB input. Native exported tensors remain unchanged.',
        'strength': .35, 'mode': 3,
        'parity_snapshot': 'runs/companion-input-final-v1',
        'parity_gates': {'curve_max_absolute_error': .0001, 'composed_rgb8_max_error': 1, 'composed_rgb8_mean_error': .02},
        'parity_policy': 'Check all 172800 native curve values and all 11059200 output RGB8 channels against the retained same-frame source/curve/output snapshot. Stop the diagnostic if either reproduction gate fails. No retuning or new snapshot.',
        'compositor': 'Reproduce native mode 3 including eight curve iterations, luminance gain .85..1.4, strength .35, source-RGB change cap .06, dark/highlight smoothstep and feathered vertical/crosshair masks. Quantize to RGB8 before temporal analysis.',
        'correspondence': {'size': [448,252], 'flow': 'Farneback, both directions',
            'parameters': [.5,3,15,3,5,1.2,0], 'maximum_closure_px': 1, 'maximum_source_gray_error_codes': 12,
            'minimum_sobel_magnitude': 5, 'core': 'x 5..95%, y 10..84%; exclude central x +/-3.6%, y +/-5%. Reject outside backward coordinates, closure and photometric failure. Flow is source-only; enhancement is never used to fit correspondence.'},
        'metric': 'Area-reduce the quantized enhancement-minus-source Rec.709 luminance residual to 448x252. Backward-warp the previous residual using source flow; absolute change in RGB8 luminance codes, on the valid mask. Report per-frame coverage, median and p95; aggregate separately on selection and final-three-second reserved split. Not a certified flicker or target-visibility score.',
        'gates': {'median_coverage_min': .60, 'p95_of_frame_median_codes_max': 1, 'p95_of_frame_p95_codes_max': 4},
        'controls': 'Identity output must have zero residual change. Clip source RGB8 plus alternating +/-8 codes before the identical residual diagnostic; this deliberate brightness alternation must fail both change gates on both splits. Same source flow/mask for every control.',
        'retention': 'Retain all source PTS and hashes, native curve predictions, coarse residual fields, every timestamped comparison PNG, all per-frame results and controls. Four original-size source/enhanced key pairs at 0,3,7,last frame. No frame subsampling for metrics or comparison.',
        'timing_scope': 'Offline CPU diagnostic with game stopped. Decode, CPU inference/composition, flow, PNG/video encoding do not establish live application performance.',
        'video': 'Each native source/enhanced image is area-reduced to 896x504, side by side with 32px labels. Original relative source PTS, no generated motion or speed change, H264 CRF20 YUV420p. Verify every encoded PTS.',
        'review': 'Inspect all chronological one-second comparison samples and all four native key pairs. Retain review limits; this sampled review cannot establish full real-time perceptual stability.',
        'limits': 'One source segment, no new gameplay, model tuning, temporal smoothing, alternate strength, training or appearance claim. Source flow may reject difficult cover/openings and cannot certify visibility. A pass only characterizes added exposure variation in covered regions.',
    }
    path = ROOT / 'scenes/playable-dce-temporal-v1.json'
    write_json(path, plan)
    shutil.copyfile(path, out/'plan.json')
    shutil.copyfile(__file__, out/'prepare-driver.py')
    print(json.dumps({'started_at':plan['started_at'], 'deadline':plan['deadline'], 'plan_sha256':digest(path)}))


def amend_native():
    old = ROOT/'scenes/playable-dce-temporal-v1.json'
    plan = json.loads(old.read_text())
    failure = json.loads((ROOT/'runs/dce-temporal-v1/report.json').read_text())
    if failure['status']!='failed' or failure['frames'] or failure['parity']['passes']:
        raise ValueError('Unexpected original diagnostic state')
    out = ROOT/'runs/dce-temporal-native-v2'
    out.mkdir(parents=True,exist_ok=False)
    shader = re.search(r'const char \*shader = R"\((.*?)\)";', (ROOT/'native/companion.cpp').read_text(), re.S).group(1)
    (out/'companion.hlsl').write_text(shader,encoding='utf-8')
    plan['amendment'] = {
        'recorded_at':datetime.now(timezone.utc).isoformat(),
        'parent_plan_sha256':digest(old), 'failed_cpu_report_sha256':digest(ROOT/'runs/dce-temporal-v1/report.json'),
        'reason':'The full CPU reproduction fails the frozen mean RGB8 gate despite a one-code maximum and matching curves. Stop that route. One offscreen native replay through the exact existing companion shaders will be checked against the same retained snapshot, without relaxing thresholds or resetting the original deadline.',
        'maximum_native_routes':1,
        'unchanged':'Source clip, timestamps, model, strength, parity/temporal thresholds, split and original deadline',
    }
    plan['reproduction'] = 'Exact native CurveNetwork and extracted companion HLSL on RX7800XT D3D11, BGRA8 input/target, mode3 strength.35, original compile flags. Offline UpdateSubresource/full readback and pipes; no game/capture/Present or live FPS claim. CPU curve reference remains independent; original failed CPU composition remains retained.'
    for p in ['native/dce_replay.cpp','build/Release/enr_dce_replay.exe','runs/dce-temporal-native-v2/companion.hlsl']:
        plan['source_hashes'][p]=digest(ROOT/p)
    plan['parity_policy']='Compare native replay with the same retained native source/curve/output snapshot using unchanged curve and RGB8 thresholds; additionally retain independent CPU curve and composition errors. Stop on native replay mismatch. No new snapshot or precision/strength change.'
    plan['timing_scope']='Offline native GPU replay including CPU upload/readback, pipes and curve-dump file. Not pure GPU time, live capture/display or application performance.'
    plan['video']=plan['video'].replace('source/enhanced','source/native-replayed')
    path = ROOT/'scenes/playable-dce-temporal-native-v2.json'
    write_json(path,plan); shutil.copyfile(path,out/'plan.json'); shutil.copyfile(__file__,out/'prepare-driver.py')
    print(json.dumps({'amended_at':plan['amendment']['recorded_at'],'original_deadline':plan['deadline'],'plan_sha256':digest(path)}))


if __name__ == '__main__':
    main()
