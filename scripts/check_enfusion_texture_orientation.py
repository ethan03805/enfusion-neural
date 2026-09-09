"""Project declared room points and compare observed hues with TXO texture UVs."""
import argparse
import json
import math
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr import room_textures, sequence
from enr.references import digest


def block(text, token):
    match = re.search(re.escape(token) + r'\s*\{', text)
    if not match:
        raise ValueError('Missing TXO block: ' + token)
    depth = 1
    for end in range(match.end(), len(text)):
        depth += (text[end] == '{') - (text[end] == '}')
        if depth == 0:
            return text[match.end():end]
    raise ValueError('Unclosed TXO block')


def rows(text, token, dtype):
    return [[dtype(v) for v in line.split()] for line in block(text, token).splitlines() if line.strip()]


def hue(rgb):
    r, g, b = rgb
    if max(rgb) - min(rgb) < 30:
        return 'neutral'
    if min(r, g) - b > 50:
        return 'yellow'
    order = np.argsort(rgb)
    if rgb[order[-1]] - rgb[order[-2]] > 50:
        return ['red', 'green', 'blue'][order[-1]]
    return 'ambiguous'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', required=True)
    parser.add_argument('--texture-build', required=True)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    out = Path(args.out)
    if out.exists():
        raise ValueError('Choose a new report path')
    root = Path(args.capture).resolve()
    capture_path = root / 'room.json'
    report = json.loads(capture_path.read_text(encoding='utf-8'))
    if report['texture_control']['case'] != 'orientation':
        raise ValueError('Expected orientation control')
    built, copies, provenance = room_textures.load_build(args.texture_build, ROOT)
    if report['texture_control']['build'] != provenance:
        raise ValueError('Capture uses another texture build')
    run = (root / 'runs' / report['run_id']).resolve()
    if root not in run.parents or digest(run / 'run.json') != report['capture_manifest_sha256']:
        raise ValueError('Capture manifest differs')
    native = json.loads((run / 'run.json').read_text(encoding='utf-8'))
    sequence.verify(report['config'], native)
    txo_path = run / 'addon/Assets/ENR_ReferenceRoom/material-room.txo'
    if digest(txo_path) != native['addon_sha256']['Assets/ENR_ReferenceRoom/material-room.txo']:
        raise ValueError('TXO geometry changed')
    body = block(txo_path.read_text(encoding='utf-8'), '$mesh "back"')
    positions = np.asarray(rows(body, '$verts', float))[:, :3]
    corners = rows(body, '$faceVerts', int)
    uvs = np.asarray(rows(body, '$texCoords', float))
    front = []
    for face in rows(body, '$faces', int):
        indices = face[2:]
        vertices = np.asarray([positions[corners[i][0]] for i in indices])
        if len(vertices) == 4 and np.max(np.abs(vertices[:, 2] - 2.9)) < 1e-6:
            front.append((vertices, np.asarray([uvs[corners[i][2]] for i in indices])))
    if len(front) != 1:
        raise ValueError('Expected one original back-wall front quad')
    vertices, face_uvs = front[0]
    # Exact planar interpolation from three known mesh corners, not image fitting.
    basis = np.column_stack([vertices[:3, :2], np.ones(3)])
    uv_map = np.linalg.solve(basis, face_uvs[:3])
    if np.max(np.abs(np.append(vertices[3, :2], 1) @ uv_map - face_uvs[3])) > 2e-6:
        raise ValueError('UV mapping is not affine on the original quad')
    texture_path = next(p for p, name in copies if name == 'orientation_BCR.tif')
    texture = np.asarray(Image.open(texture_path).convert('RGB'), dtype=np.float64)
    frame = report['frames'][0]
    frame_path = run / frame['file']
    if digest(frame_path) != frame['sha256']:
        raise ValueError('Source frame changed')
    image = np.asarray(Image.open(frame_path).convert('RGB'), dtype=np.float64)
    camera, direction = sequence.camera(report['config'], 0)
    camera, forward = np.asarray(camera), np.asarray(direction)
    forward /= np.linalg.norm(forward)
    right = np.cross([0, 1, 0], forward)
    right /= np.linalg.norm(right)
    up = np.cross(forward, right)
    height, width = image.shape[:2]
    focal = height / (2 * math.tan(math.radians(report['config']['vertical_fov_degrees'] / 2)))
    observations = []
    for point in built['source']['plan']['orientation_probe_points_room_xyz']:
        point = np.asarray(point)
        uv = np.append(point[:2], 1) @ uv_map
        delta = point + np.asarray(report['room_origin']) - camera
        depth = float(delta @ forward)
        projected = [width/2 + focal * float(delta @ right) / depth, height/2 - focal * float(delta @ up) / depth]
        x, y = [int(math.floor(v+0.5)) for v in projected]
        if not (2 <= x < width-2 and 2 <= y < height-2 and depth > 0):
            raise ValueError('Declared point outside the captured viewport')
        actual = image[y-2:y+3, x-2:x+3].mean(axis=(0, 1)).tolist()
        candidates = {}
        for name, candidate in [('txo_direct', uv), ('txo_v_flipped', [uv[0], 1-uv[1]])]:
            tx, ty = [int(math.floor((v % 1) * 512)) for v in candidate]
            sample = texture[ty, tx].tolist()
            candidates[name] = {'uv': list(candidate), 'texture_xy': [tx, ty], 'source_rgb8': sample, 'hue': hue(sample), 'matches': hue(sample) == hue(actual)}
        observations.append({'point_local': point.tolist(), 'projected_xy': projected, 'sample_center_xy': [x, y],
                             'observed_mean_rgb8': actual, 'observed_hue': hue(actual), 'candidates': candidates})
    matching = [name for name in ('txo_direct', 'txo_v_flipped') if all(p['candidates'][name]['matches'] for p in observations)]
    result = {'schema_version': 1, 'operation': 'original-texture-raster-orientation',
              'status': 'succeeded' if matching == ['txo_direct'] else 'failed',
              'script_sha256': digest(__file__), 'capture_report_sha256': digest(capture_path),
              'texture_build_report_sha256': provenance['build_report_sha256'], 'txo_sha256': digest(txo_path),
              'source_texture_sha256': digest(texture_path), 'frame_sha256': digest(frame_path),
              'plan_sha256': built['source']['plan_sha256'], 'observations': observations, 'matching_conventions': matching,
              'method': 'Predeclared world points; affine UV interpolation from original TXO corners; analytic camera projection without image alignment; mean hue in fixed 5x5 image patches',
              'analysis_selection': 'Points and asymmetric pattern declared before capture. Hue classification thresholds/patch size implemented after visual inspection; this is a diagnostic, not a held-out fidelity gate.',
              'limits': ['Only four back-wall points under one camera; other faces, mip transitions and normal maps require separate checks',
                         'Hue agreement does not establish photometric equivalence, compiled-pixel equality or neural integration']}
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix('.py').write_bytes(Path(__file__).read_bytes())
    out.write_bytes((json.dumps(result, indent=2) + '\n').encode('utf-8'))
    print(json.dumps({'status': result['status'], 'matching': matching, 'points': observations}))
    if result['status'] != 'succeeded':
        raise SystemExit(1)


if __name__ == '__main__':
    main()
