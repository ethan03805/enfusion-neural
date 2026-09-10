"""Preserve and publish one rejected, unchanged synthetic appearance proposal."""
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from enr.references import digest, write_json


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    out = ROOT / 'runs/synthetic-target-v1'
    plan_path = ROOT / 'scenes/playable-synthetic-target-v1.json'
    evidence = ROOT / 'evidence/synthetic-target-v1.json'
    if evidence.exists():
        raise FileExistsError(evidence)
    plan, generation = read(plan_path), read(out / 'generation.json')
    raw, source = out / 'proposal-raw.png', out / 'source.png'
    expected = [(out / 'plan.json', digest(plan_path)),
                (source, plan['source']['sha256']),
                (out / 'prompt.txt', plan['prompt_sha256']),
                (out / 'prepare-driver.py', plan['driver_sha256']),
                (raw, generation['sha256'])]
    for path, sha in expected:
        if digest(path) != sha:
            raise ValueError('Changed artifact: ' + path.name)
    if generation['calls'] != plan['calls_allowed'] or Image.open(raw).size != (1672, 941):
        raise ValueError('Unexpected proposal or call count')
    observations = [
        'Roof outline and antenna remain recognizable. Roof tiles/seams acquire much denser, darker high-contrast texture; the original fine surface pattern is not retained.',
        'Broad door/window arrangement remains recognizable. Facade shading becomes stronger and more sharply divided beneath the eaves. Exact corners and shadow boundaries are not certified.',
        'The central pole remains in approximately the same normalized position. Fine surface shading/texture changes; pixel-coordinate preservation is not established.',
        'The middle barrier and its placement remain recognizable. Small rail/bar details are redrawn; fine cover and gap equivalence is not certified.',
        'The foreground barrier and adjacent opening retain their broad arrangement. Shading and fine metal texture differ; no semantic visibility acceptance.',
        'The right painted logo remains recognizable, but the mermaid and faded small lettering are redrawn rather than preserved. It is not an exact text/texture target.',
        'The left painted logo retains the partial word and fruit motif at a coarse level; fine lettering and surrounding plaster texture are regenerated.',
        'Road and cast-shadow layout remain broadly recognizable, with stronger shadow contrast and new fine asphalt grain/crack markings. Exact source shadow boundaries are not accepted.',
        'The two foreground trunks and broad foliage masses remain recognizable. Leaves, bark and fine vegetation gaps are reconstructed; preserved concealment is not established.',
        'Top HUD is recreated at the lower returned resolution, not pixel-identical to the 2560x1440 source.',
        'Bottom TAB/Quick slots HUD is recreated at the lower returned resolution, not pixel-identical to the source.',
    ]
    if len(observations) != len(plan['landmarks']):
        raise ValueError('Incomplete fixed landmark review')
    closed = datetime.now(timezone.utc)
    elapsed = (closed - datetime.fromisoformat(plan['started_at'])).total_seconds() / 60
    review = {
        'decision': 'reject', 'scope': 'One complete 2560x1440 source and one complete unchanged 1672x941 proposal inspected at their original dimensions; every fixed source landmark region considered. Qualitative review only; no measured feature correspondence, temporal sequence or target-visibility experiment.',
        'landmarks': [dict(landmark, observation=observation) for landmark, observation in zip(plan['landmarks'], observations)],
        'appearance': 'Stronger and more varied plaster, roof and road shading appears more photographic at a glance. This is a subjective art-direction observation, not measured physical realism. The improvement is coupled to regenerated fine detail and cannot be accepted under the source-identity contract.',
        'dimensions': {'requested': [2560,1440], 'returned': [1672,941], 'matches': False,
                       'limit': 'The original files have different dimensions. No resampling, registration, warping or cleanup is applied to make them appear aligned.'},
        'failed_gates': ['Invented/reconstructed fine texture and lettering', 'Source pixel-coordinate/HUD identity not preserved'],
        'unverified_gates': ['Exact opening, barrier and foliage-gap equivalence', 'Exact cast-shadow boundary preservation', 'Shaded gameplay-target visibility'],
        'training_allowed': False, 'live_integration_allowed': False,
        'next_candidate_generated': False, 'retouched': False,
    }
    write_json(out / 'decision.json', review)
    filename = 'synthetic-target-rejected.png'
    destination = ROOT / 'docs/media' / filename
    if destination.exists():
        raise FileExistsError(destination)
    entry = {
        'file': filename, 'sha256': digest(raw), 'bytes': raw.stat().st_size,
        'dimensions': list(Image.open(raw).size), 'source_record': evidence.relative_to(ROOT).as_posix(),
        'source_artifact': raw.relative_to(ROOT).as_posix(), 'source_sha256': digest(raw),
        'transformation': 'Unchanged built-in image-tool PNG. Source-conditioned synthetic proposal from the documented 2560x1440 gameplay frame; tool returned 1672x941. No resize, cleanup, registration or additional generation. Not photographic ground truth, not live gameplay output.',
        'rights': 'Synthetic edit of Arma Reforger imagery © Bohemia Interactive; game imagery is outside the MIT code license. No training-data authorization or new game-asset license is inferred.',
    }
    report = {
        'schema_version': 1, 'date': '2026-09-10', 'outcome': 'rejected_synthetic_target',
        'evaluation_closed_at': closed.isoformat(), 'minutes_since_plan_start': elapsed,
        'within_declared_time_bound': elapsed <= plan['maximum_minutes'],
        'plan': plan, 'generation': generation, 'review': review,
        'working_package_changed': False, 'training_performed': False,
        'photorealistic_gain_accepted': False, 'local_model_performance_measured': False,
        'source_hashes': {p.relative_to(ROOT).as_posix(): digest(p) for p in
                          (plan_path, out/'generation.json', out/'decision.json', Path(__file__))},
        'published_media': [entry],
    }
    manifest_path = ROOT / 'docs/media/manifest.json'
    manifest = read(manifest_path)
    if any(row['file'] == filename for row in manifest['images']):
        raise ValueError('Duplicate media entry')
    manifest['images'].append(entry)
    shutil.copyfile(raw, destination)
    write_json(evidence, report)
    write_json(manifest_path, manifest)
    print(json.dumps({'decision': review['decision'], 'elapsed_minutes': elapsed,
                      'within_bound': report['within_declared_time_bound'], 'raw_sha256': digest(raw)}))


if __name__ == '__main__':
    main()
