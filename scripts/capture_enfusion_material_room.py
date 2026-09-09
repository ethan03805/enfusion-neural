"""Capture original imported geometry with the reference camera in an isolated world.

This scout does not establish matching materials, lighting, color or a model bridge.
"""
import argparse
import json
import math
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import sequence
from enr import room_textures
from enr.references import digest, lab_modules, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True)
    parser.add_argument('--loaded-import', required=True)
    parser.add_argument('--lab-source', required=True)
    parser.add_argument('--color-control', choices=('white', 'reference-colors'), help='Change only original material Color constants under the declared control plan')
    parser.add_argument('--texture-build', help='Verified completed original texture build')
    parser.add_argument('--texture-case', choices=('orientation', 'packed', 'metal-matte', 'metal-dielectric'))
    parser.add_argument('--light-case', choices=('night-off', 'night-low', 'night-high'))
    parser.add_argument('--light-clip-control', action='store_true', help='Apply the separately declared LV10 intensity-clipping follow-up')
    parser.add_argument('--calibration-case', choices=('off', 'lv8', 'lv9', 'lv10', 'lv11', 'lv12'), help='Run a declared point-light calibration case with fixed clipping policy')
    args = parser.parse_args()
    if bool(args.texture_build) != bool(args.texture_case) or (args.texture_case and args.color_control):
        raise ValueError('Texture build and case are required together and exclude Color-only control')
    if args.light_case and args.texture_case != 'packed':
        raise ValueError('Light controls require the original packed texture case')
    if args.light_clip_control and args.light_case != 'night-low':
        raise ValueError('The clipping follow-up requires the original night-low case')
    if args.calibration_case and (args.texture_case != 'packed' or args.light_case or args.light_clip_control):
        raise ValueError('Calibration requires packed textures and excludes the original light-case flags')
    texture_build = texture_copies = texture_provenance = None
    if args.texture_build:
        texture_build, texture_copies, texture_provenance = room_textures.load_build(args.texture_build, ROOT)
    source_root = Path(args.loaded_import).resolve()
    report_path = source_root / 'import.json'
    report = json.loads(report_path.read_text(encoding='utf-8'))
    events = [json.loads(event) for event in report['native_records']]
    if (report['status'] != 'succeeded' or report['route'] != 'load-completed'
            or [e['count'] for e in events if e['event'] == 'materials'] != [7]):
        raise ValueError('Require the separate native load of all seven original material regions')
    source_run = (source_root / 'runs' / report['run_id']).resolve()
    if source_root not in source_run.parents or digest(source_run / 'run.json') != report['run_manifest_sha256']:
        raise ValueError('Source run manifest mismatch')
    source_manifest = json.loads((source_run / 'run.json').read_text(encoding='utf-8'))
    if source_manifest['process_exit_code'] != 0 or source_manifest['terminated_owned_process']:
        raise ValueError('Separate resource load did not finish naturally')
    if digest(source_run / 'console.log') != report['console_sha256']:
        raise ValueError('Native load log changed')
    models = [e['resource'] for e in events if e['event'] == 'mesh_loaded']
    if len(models) != 1 or not re.fullmatch(r'\{[0-9A-F]{16}\}Assets/ENR_ReferenceRoom/material-room\.xob', models[0]):
        raise ValueError('Expected one original room resource')
    assets = source_run / 'addon/Assets/ENR_ReferenceRoom'
    copied = []
    for item in report['retained_assets']:
        path = (assets / item['file']).resolve()
        if assets not in path.parents or digest(path) != item['sha256']:
            raise ValueError('Imported asset path or hash differs')
        copied.append((path, item['file']))
    out = Path(args.out).resolve()
    if out.exists() and any(out.iterdir()):
        raise ValueError('Choose a new empty capture directory')
    initialize, run_workbench, doctor = lab_modules(args.lab_source)
    from enfusion_lab import runner
    initialize(out)
    shutil.copyfile(__file__, out / 'capture_driver.py')
    write_json(out / 'doctor.json', doctor())
    config = sequence.load_config(ROOT / 'scenes/arland-motion-v1.json')
    room = json.loads((ROOT / 'scenes/material-room-v1.json').read_text(encoding='utf-8'))
    color_control = None
    texture_control = None
    light_control = None
    if args.light_case or args.calibration_case:
        light_plan_path = ROOT / ('scenes/point-light-calibration-v1.json' if args.calibration_case else 'scenes/material-room-light-control-v1.json')
        light_plan = json.loads(light_plan_path.read_text(encoding='utf-8'))
        case = args.calibration_case or args.light_case
        light_control = {'case': case, 'plan': light_plan,
                         'plan_sha256': digest(light_plan_path), 'requested': light_plan['cases'][case]}
        if args.calibration_case and light_plan['light']['intensity_clip_ev_bias'] != -10:
            raise ValueError('Native fixture supports the declared -10 clipping bias only')
        if args.light_clip_control:
            clip_path = ROOT / 'scenes/material-room-light-clip-control-v1.json'
            clip_plan = json.loads(clip_path.read_text(encoding='utf-8'))
            light_control['clipping_followup'] = {'plan': clip_plan, 'plan_sha256': digest(clip_path),
                                                   'base_plan_sha256': digest(light_plan_path)}
        config['hour'] = light_plan['hour']
    if args.color_control:
        plan_path = ROOT / 'scenes/material-room-color-control-v1.json'
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
        color_control = {'case': args.color_control, 'plan_sha256': digest(plan_path),
                         'source_scene_sha256': digest(ROOT / plan['source_scene']),
                         'plan': plan, 'materials': []}
    origin = [2048, 1000, 2048]
    position = room['camera']['position']
    target = room['camera']['target']
    delta = [b-a for a, b in zip(position, target)]
    pitch = math.degrees(math.atan2(delta[2], math.hypot(delta[0], delta[1])))
    yaw = math.degrees(math.atan2(delta[0], delta[1]))
    mapped = [origin[0] + position[0], origin[1] + position[2], origin[2] + position[1]]
    config.update(id='material-room-engine-geometry-v1', group='material-room-v1',
                  position_start=mapped, position_end=mapped, yaw_start_degrees=yaw, yaw_end_degrees=yaw,
                  pitch_start_degrees=pitch, pitch_end_degrees=pitch,
                  vertical_fov_degrees=room['camera']['vertical_fov_degrees'],
                  near_plane_m=0.01, far_plane_m=100, samples=1, hold_ticks_per_sample=120)
    write_json(out / 'capture-config.json', config)
    config = sequence.load_config(out / 'capture-config.json')
    sequence.prepare(out, config)
    for source, name in copied:
        destination = out / 'addon/Assets/ENR_ReferenceRoom' / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    if color_control:
        # Only the fresh capture addon is changed. Retained import snapshots and
        # the original scene remain immutable. Packed-map defaults are untouched.
        for name, values in sorted(room['materials'].items()):
            material_path = out / 'addon/Assets/ENR_ReferenceRoom/Data' / (name + '.emat')
            before = digest(material_path)
            if material_path.read_text(encoding='utf-8').strip() != 'MatPBRBasic {\n}':
                raise ValueError('Color control requires the original default material: ' + name)
            color = values['base_color_linear'] if args.color_control == 'reference-colors' else [1, 1, 1]
            rgba = color + [1]
            material_path.write_bytes(('MatPBRBasic {\n Color ' + ' '.join(format(v, '.9g') for v in rgba) + '\n}\n').encode('utf-8'))
            color_control['materials'].append({'name': name, 'before_sha256': before,
                                              'after_sha256': digest(material_path), 'rgba': rgba})
        write_json(out / 'color-control.json', color_control)
    if texture_build:
        for source, name in texture_copies:
            destination = out / 'addon/Assets/ENR_OriginalTextures' / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        recipes = room_textures.material_recipe(args.texture_case, room['materials'], texture_build['identities'])
        texture_control = {'case': args.texture_case, 'build': texture_provenance,
                           'plan': texture_build['source']['plan'], 'plan_sha256': texture_build['source']['plan_sha256'],
                           'materials': [], 'texture_assets': texture_build['retained_assets']}
        for recipe in recipes:
            material_path = out / 'addon/Assets/ENR_ReferenceRoom/Data' / (recipe['name'] + '.emat')
            if material_path.read_text(encoding='utf-8').strip() != 'MatPBRBasic {\n}':
                raise ValueError('Texture control requires original default materials')
            before = digest(material_path)
            material_path.write_bytes(recipe['material_text'].encode('utf-8'))
            texture_control['materials'].append(dict(recipe, before_sha256=before, after_sha256=digest(material_path)))
        write_json(out / 'texture-control.json', texture_control)
    material_control = color_control or texture_control
    if light_control:
        light_spec = light_control['plan']['light']
        light_position = [a+b for a, b in zip(origin, light_spec['local_position_enfusion_xyz'])]
        light_control['world_position'] = light_position
        write_json(out / 'light-control.json', light_control)
        shutil.copyfile(ROOT / 'adapters/enfusion/probes/ENR_RoomLight.c', out / 'addon/Scripts/Game/ENR_RoomLight.c')
        light_config = ('#ifdef WORKBENCH\nclass ENR_RoomLightConfig {\n static string Case = "' + light_control['case'] + '";\n'
                        ' static vector Position = "' + ' '.join(map(str, light_position)) + '";\n'
                        ' static float Radius = ' + str(light_spec['radius_m']) + ';\n'
                        ' static float Near = ' + str(light_spec['near_plane_m']) + ';\n'
                        ' static float LV = ' + str(light_control['requested']['native_LV']) + ';\n'
                        ' static bool Enabled = ' + str(light_control['requested']['enabled']).lower() + ';\n'
                        ' static bool UseClipControl = ' + str(bool(args.light_clip_control or args.calibration_case)).lower() + ';\n}\n#endif\n')
        (out / 'addon/Scripts/Game/ENR_RoomLightConfig.c').write_bytes(light_config.encode('utf-8'))
    plugin = ROOT / 'adapters/enfusion/probes/ENR_MaterialRoom.c'
    shutil.copyfile(plugin, out / 'addon/Scripts/Game/ENR_MaterialRoom.c')
    material_lookup = ' static ResourceName MaterialResource(string slot) {\n'
    if material_control:
        for item in material_control['materials']:
            name = item['name']
            meta = out / 'addon/Assets/ENR_ReferenceRoom/Data' / (name + '.emat.meta')
            match = re.search(r'Name "(\{[0-9A-F]{16}\}Assets/ENR_ReferenceRoom/Data/' + re.escape(name) + r'\.emat)"', meta.read_text(encoding='utf-8'))
            if not match:
                raise ValueError('Material metadata lacks verified identity: ' + name)
            material_lookup += '  if (slot == "' + name + '") return "' + match.group(1) + '";\n'
    material_lookup += '  return "";\n }\n'
    (out / 'addon/Scripts/Game/ENR_RoomConfig.c').write_text(
        '#ifdef WORKBENCH\nclass ENR_RoomConfig { static ResourceName Model = "' + models[0] +
        '"; static vector Origin = "' + ' '.join(map(str, origin)) + '"; static bool InspectMaterialColors = ' +
        str(bool(material_control)).lower() + '; static bool InspectTextureMaps = ' + str(bool(texture_control)).lower() +
        ';\n' + material_lookup + '}\n#endif\n', encoding='utf-8')
    capture = out / 'addon/Scripts/Game/ELab_GameCapture.c'
    text = capture.read_text(encoding='utf-8')
    needle = 'ENR_Sequence.Camera(world);'
    if text.count(needle) != 1:
        raise ValueError('Capture entry point changed')
    addition = '\n  ENR_MaterialRoom.Init(world);'
    if light_control:
        addition += '\n  ENR_RoomLight.Init();'
    capture.write_text(text.replace(needle, needle + addition), encoding='utf-8')
    with sequence.private_settings(runner):
        validation = run_workbench(out, 'validate', timeout=180)
        if validation['status'] != 'succeeded':
            raise ValueError('Room capture addon failed validation')
        position, direction = sequence.camera(config, 0)
        run = run_workbench(out, 'capture', world=config['world'], position=position,
                            direction=direction, settle=config['settle_seconds'], timeout=config['timeout_seconds'])
    directory = Path(run['directory'])
    result = sequence.verify(config, run)
    records = [line.split('ENR_ROOM ', 1)[1] for line in (directory / 'console.log').read_text(encoding='utf-8').splitlines() if 'ENR_ROOM ' in line]
    if len(records) != 1 or not records[0].startswith('spawned ') or not records[0].endswith('materials=7'):
        raise ValueError('Original room was not observed once with seven materials')
    result.update(source_import_report_sha256=digest(report_path),
                  driver_sha256=digest(out / 'capture_driver.py'),
                  validation_run=validation['run_id'], validation_manifest_sha256=digest(Path(validation['directory']) / 'run.json'),
                  capture_manifest_sha256=digest(directory / 'run.json'), console_sha256=digest(directory / 'console.log'),
                  capture_config_sha256=digest(out / 'capture-config.json'), room_records=records,
                  model_resource=models[0], room_origin=origin,
                  visual_review='pending', engine_geometry_verified=False,
                  aligned_appearance_pair_verified=False, renderer_integration_verified=False,
                  scope='Imported original geometry and reference-camera scout; default engine materials and environment, no matched appearance or neural processing')
    if color_control:
        color_records = [line.split('ENR_ROOM_COLOR ', 1)[1] for line in (directory / 'console.log').read_text(encoding='utf-8').splitlines() if 'ENR_ROOM_COLOR ' in line]
        result.update(color_control=color_control, color_control_sha256=digest(out / 'color-control.json'),
                      color_records=color_records,
                      scope='Original material Color constant response control; outdoor illumination and default packed-map parameters, no matched appearance or neural processing')
    if texture_control:
        log_text = (directory / 'console.log').read_text(encoding='utf-8')
        result.update(texture_control=texture_control, texture_control_sha256=digest(out / 'texture-control.json'),
                      color_records=[line.split('ENR_ROOM_COLOR ', 1)[1] for line in log_text.splitlines() if 'ENR_ROOM_COLOR ' in line],
                      texture_records=[line.split('ENR_ROOM_MAP ', 1)[1] for line in log_text.splitlines() if 'ENR_ROOM_MAP ' in line],
                      scope='Original packed-texture response control; material/light photometry and neural integration remain unverified')
    if light_control:
        light_log = (directory / 'console.log').read_text(encoding='utf-8')
        result.update(light_control=light_control, light_control_sha256=digest(out / 'light-control.json'),
                      light_records=[line.split('ENR_ROOM_LIGHT ', 1)[1] for line in light_log.splitlines() if 'ENR_ROOM_LIGHT ' in line],
                      scope='Original room scripted point-light response at night; environment light/reflections are not isolated, no calibrated reference or neural processing')
    write_json(out / 'room.json', result)
    print(json.dumps({'status': result['status'], 'run': run['run_id'], 'records': records, 'image': run['image']}, indent=2))


if __name__ == '__main__':
    main()
