"""Publish portable verified outcomes from retained screenshot/UI attempts."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.image_bridge import inspect, pixels, operation, difference
from enr.references import digest, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', action='append', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    attempts = []
    for folder in args.root:
        root = Path(folder)
        result = inspect(root, ROOT/'models/bootstrap-v0.json')
        native = json.loads((root/'runs'/result['capture_run']/'run.json').read_text())
        if native['status'] not in ('succeeded', 'failed'):
            raise ValueError('An attempt must be terminal before publication')
        result['process'] = {key: native[key] for key in
                             ('process_exit_code', 'terminated_owned_process', 'wall_seconds')}
        profile=root/'runs'/result['capture_run']/'profile/profile'
        if result['mode'] in ('identity','invert') and (profile/'bridge-output.png').exists():
            worker=json.loads((profile/'bridge-worker.json').read_text())
            for field,name in [('input_sha256','bridge-input.png'),('output_sha256','bridge-output.png')]:
                if worker[field]!=digest(profile/name):raise ValueError('Worker image changed')
            if worker['mode']!=result['mode'] or worker['status']!='succeeded':raise ValueError('Worker control differs')
            dims=result['config']['dimensions']
            source=pixels(profile/'bridge-input.png',dims,allow_opaque_rgb=result['source_interface']=='file')
            output=pixels(profile/'bridge-output.png',dims)
            result['independent_cpu_operation_check']=difference(output,operation(source,result['mode']))
            result['worker_report']=worker
            final=profile.parent.parent/'frame.png'
            if final.exists():
                captured=pixels(final,dims,allow_opaque_rgb=True)
                compared=difference(captured,output)
                result['final_capture_vs_worker']={'sha256':digest(final),'rgb_exact':compared['rgb_changed_pixel_fraction']==0,
                    'rgb_mae_8bit':compared['rgb_mae_8bit'],'rgb_max_error_8bit':compared['rgba_max_error_8bit'],
                    'scope':'Ordinary final scene export after the failed widget readback. This is not a texture readback or proof of the display/presentation stage.'}
        attempts.append(result)
    report = {'schema_version': 1, 'scope': 'Screenshot/UI probes only. Each attempt retains its actual outcome; no scene-renderer bridge is established.',
              'reporter_sha256': digest(__file__), 'verifier_sha256': digest(ROOT/'enr/image_bridge.py'),
              'attempts': attempts,
              'sources': ['https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceSystem.html',
                          'https://community.bistudio.com/wikidata/external-data/arma-reforger/EnfusionScriptAPIPublic/interfaceImageWidget.html']}
    write_json(args.out, report)
    print(json.dumps([{'run': a['capture_run'], 'mode': a['mode'], 'status': a['capture_status'],
                       'verification': a['verification']} for a in attempts], indent=2))


if __name__ == '__main__':
    main()
