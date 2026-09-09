"""Capture a verified real-world scout, optionally placing observed entity prefabs.

Source-only evidence. This does not create a reference target or process an
engine frame through a model. New worlds require a completed native inventory.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import image_bridge, sequence
from enr.references import digest, lab_modules, write_json


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', required=True)
    p.add_argument('--config', required=True)
    p.add_argument('--lab-source', required=True)
    p.add_argument('--world-inventory')
    p.add_argument('--entities', action='store_true')
    a = p.parse_args()
    out = Path(a.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Use a new empty scout directory')
    config, binding = image_bridge.load_probe_config(a.config, a.world_inventory)
    initialize, run_workbench, doctor = lab_modules(a.lab_source)
    from enfusion_lab import runner
    from enfusion_lab.config import LabError
    initialize(out)
    sequence.prepare(out, config)
    write_json(out/'capture-config.json', config)
    write_json(out/'doctor.json', doctor())
    if a.entities:
        entities = ROOT/'adapters/enfusion/probes/ENR_BridgeEntities.c'
        (out/'addon/Scripts/Game/ENR_BridgeEntities.c').write_bytes(entities.read_bytes())
        (out/'addon/Scripts/Game/ENR_BridgeConfig.c').write_text(
            '#ifdef WORKBENCH\nclass ENR_BridgeConfig { static bool Entities = true; }\n#endif\n')
        capture = out/'addon/Scripts/Game/ELab_GameCapture.c'
        text = capture.read_text()
        for needle, suffix in [('ENR_Sequence.Camera(world);', '\n  ENR_BridgeEntities.Init(world);'),
                               ('if (!ENR_Sequence.Tick(world, width, height)) return;', '\n  ENR_BridgeEntities.Record();')]:
            if text.count(needle) != 1:
                raise ValueError('Capture entry point changed')
            text = text.replace(needle, needle+suffix)
        capture.write_text(text)
    with sequence.private_settings(runner):
        validation = run_workbench(out, 'validate', timeout=180)
        if validation['status'] != 'succeeded':
            raise ValueError('Scout addon did not compile')
        position, direction = sequence.camera(config, 0)
        try:
            run = run_workbench(out, 'capture', world=config['world'], position=position,
                                direction=direction, settle=config['settle_seconds'], timeout=config['timeout_seconds'])
        except LabError as error:
            native = error.details.get('run')
            write_json(out/'scout.json', {'schema_version': 1, 'status': 'failed', 'error': str(error),
                       'capture_run': native['run_id'] if native else None, 'world_binding': binding})
            raise
    directory = Path(run['directory'])
    result = sequence.verify(config, run)
    result.update(config_sha256=digest(out/'capture-config.json'), world_binding=binding,
                  capture_manifest_sha256=digest(directory/'run.json'), console_sha256=digest(directory/'console.log'),
                  validation_run=validation['run_id'],
                  validation_manifest_sha256=digest(Path(validation['directory'])/'run.json'),
                  entities_requested=a.entities, visual_review='pending',
                  coverage_scope='Source-only real Arma capture; no aligned reference, model output or renderer integration proof.')
    result['entity_records'] = [s.split('ENR_PROP ', 1)[1] for s in (directory/'console.log').read_text(errors='replace').splitlines() if 'ENR_PROP ' in s]
    write_json(out/'scout.json', result)
    print(json.dumps({'status': result['status'], 'capture_run': run['run_id'],
                      'frames': len(result['frames']), 'image': run['image'], 'entity_records': result['entity_records']}, indent=2))


if __name__ == '__main__':
    main()
