"""Bind completed calibration evidence to full-size reference/display inspections."""
import argparse
import json
from pathlib import Path
import sys
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from enr.references import digest


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--analysis',required=True);p.add_argument('--reference',required=True)
    p.add_argument('--review',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();analysis=Path(a.analysis);reference=Path(a.reference);out=Path(a.out)
    if out.exists():raise ValueError('Choose a new portable evidence file')
    result=read(analysis/'analysis.json');review=read(a.review)
    if (result['evidence_verification']!='succeeded' or result['operation']!='point-light-calibration'
            or result['plan_sha256']!=digest(ROOT/'scenes/point-light-calibration-v1.json')
            or result['analyzer_sha256']!=digest(ROOT/'scripts/analyze_point_light_calibration.py')
            or result['photometry_sha256']!=digest(ROOT/'enr/photometry.py')
            or result['fit_lock_sha256']!=digest(ROOT/'evidence/point-light-calibration-lock-v1.json')
            or result['review_sha256']!=digest(ROOT/'evidence/point-light-calibration-native-review-v1.json')
            or result['reference_report_sha256']!=digest(reference/'run.json')):
        raise ValueError('Completed analysis provenance differs')
    roles=result['plan']['reference']['roles'];expected={(stage,role) for stage in ['rendered','mapped'] for role in roles}
    if len(review['frames'])!=8 or {(r['stage'],r['role']) for r in review['frames']}!=expected:
        raise ValueError('Review must include all raw and mapped reference images')
    for inspected in review['frames']:
        role=inspected['role'];stage=inspected['stage']
        path=(reference if stage=='rendered' else analysis)/(role+'.png')
        source=next(r for r in result['reference']['renders'] if r['role']==role) if stage=='rendered' else next(r for r in result['display_outputs'] if r['role']==role)
        expected_hash=source['png_sha256'] if stage=='rendered' else source['sha256']
        with Image.open(path) as image:
            dimensions=list(image.size);image.verify()
        if (digest(path)!=expected_hash or inspected['sha256']!=expected_hash or not inspected['full_size_inspected']
                or inspected['dimensions']!=dimensions or dimensions!=result['plan']['dimensions']):
            raise ValueError('Reference image changed or lacks full-size inspection')
    result.update(analysis_sha256=digest(analysis/'analysis.json'),summarizer_sha256=digest(__file__),
                  reference_visual_review=review,reference_visual_review_sha256=digest(a.review))
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_bytes((json.dumps(result,indent=2,allow_nan=False)+'\n').encode('utf-8'))
    print(json.dumps({'verified':result['verified'],'gates':result['gates'],'images_reviewed':8}))


if __name__=='__main__':main()
