"""Freeze one source-conditioned appearance proposal before using the image tool."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def main():
    out = ROOT / 'runs/synthetic-target-v1'
    out.mkdir(parents=True, exist_ok=False)
    source = ROOT / 'docs/media/sustained-reduced-020.png'
    if Image.open(source).size != (2560, 1440):
        raise ValueError('Unexpected input dimensions')
    manifest = json.loads((ROOT / 'docs/media/manifest.json').read_text())
    record = next(x for x in manifest['images'] if x['file'] == source.name)
    if digest(source) != record['sha256']:
        raise ValueError('Source differs from published capture')
    prompt = """Use case: style-transfer, strictly source-constrained lighting/material correction.
Asset type: one offline synthetic art-direction proposal for a gameplay rendering study; not a new scene or a live frame.
Input image 1 is the EDIT TARGET: a 2560 x 1440 Arma Reforger gameplay capture. Return exactly one image with the same 2560 x 1440 canvas, camera, framing, perspective, and pixel-coordinate scene layout.
Primary request: make the EXISTING plaster, weathered roof, asphalt, vegetation and metal read more naturally photographic through coherent broad illumination and material response. Improve diffuse/indirect-light balance and surface shading without replacing or inventing surface details. Preserve the existing clear daytime sky, sun direction, cast-shadow boundaries, exposure visibility and material colors/identity. A simple global brightness or saturation grade is not the requested improvement.
Hard invariants: every building outline, roof edge/tile/seam, facade opening, door/window corner, pole, antenna, branch/leaf/foliage gap, barrier bar/gap and road marking stays at its source coordinate. Keep the two painted wall logos and all text exactly as pictured, including partial/illegible characters; do not reconstruct them. Keep HUD, FPS/version text and TAB Quick slots overlay pixel-identical. Retain all source fine texture and wear patterns without new cracks, grain, bricks, leaves or legible writing. Preserve the shaded areas' visible detail; no crushing blacks, glowing edges, added depth of field or motion blur. No object additions/removals, crop, warp, new weather, new materials, relabeling, new shadows or change to cover/opening visibility.
Allowed edit: source-aligned low-frequency lighting and material-response correction inside existing surfaces only. Keep high-frequency structure and scene identity. If an area cannot be improved under these constraints, leave that area unchanged. No caption, watermark or decorative border."""
    now = datetime.now(timezone.utc)
    plan = {
        'schema_version': 1, 'started_at': now.isoformat(),
        'deadline': (now + timedelta(minutes=20)).isoformat(), 'maximum_minutes': 20,
        'source': record, 'source_dimensions': [2560, 1440],
        'tool': 'built-in image_gen.imagegen', 'calls_allowed': 1,
        'prompt': prompt, 'label': 'Synthetic art direction, not photographic ground truth',
        'landmark_coordinate_convention': 'Manually selected source-pixel review rectangles [x0,y0,x1,y1], half-open. They are inspection regions, not measured feature correspondences.',
        'landmarks': [
            {'name': 'roof silhouette, seams and antenna', 'region': [1200,48,2560,710]},
            {'name': 'near facade door and window corners', 'region': [1288,560,1815,806]},
            {'name': 'thin central pole', 'region': [1507,0,1556,752]},
            {'name': 'middle barrier bars and gaps', 'region': [1264,733,1560,905]},
            {'name': 'foreground barrier and opening', 'region': [2185,735,2560,991]},
            {'name': 'right painted wall logo and text', 'region': [2061,223,2440,672]},
            {'name': 'left painted wall logo and text', 'region': [399,453,582,673]},
            {'name': 'road cast-shadow boundary', 'region': [193,780,1029,960]},
            {'name': 'left foliage, trunks and thin roadside cover', 'region': [0,0,783,965]},
            {'name': 'top HUD text', 'region': [2265,0,2560,36]},
            {'name': 'bottom HUD text', 'region': [0,1355,260,1440]},
        ],
        'rejection_gates': [
            'Moved boundaries or changed openings/cover/foliage gaps',
            'Invented fine texture, new or modified text or logos',
            'Different weather, material identity or lost shaded visibility',
            'Only a brightness/color grade without useful material/lighting gain',
        ],
        'review': 'Inspect the complete source and unchanged raw proposal at original dimensions, then every fixed landmark. Numeric image differences are diagnostic, not realism or correspondence measurements.',
        'limits': 'No prompt search, second candidate, cleanup edit, local generative integration, model training or frame-performance claim. A rejected target cannot be used for training. A passing still only permits a separate feasibility test of compact deterministic source-coordinate correction.',
        'driver_sha256': digest(Path(__file__)),
    }
    shutil.copyfile(source, out / 'source.png')
    shutil.copyfile(__file__, out / 'prepare-driver.py')
    (out / 'prompt.txt').write_text(prompt, encoding='utf-8')
    plan['prompt_sha256'] = digest(out / 'prompt.txt')
    write_json(ROOT / 'scenes/playable-synthetic-target-v1.json', plan)
    shutil.copyfile(ROOT / 'scenes/playable-synthetic-target-v1.json', out / 'plan.json')
    print(json.dumps({'started_at': plan['started_at'], 'deadline': plan['deadline'],
                      'source_sha256': digest(source), 'plan_sha256': digest(out / 'plan.json'),
                      'prompt': prompt}))


if __name__ == '__main__':
    main()
