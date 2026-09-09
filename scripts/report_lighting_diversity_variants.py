"""Apply the unchanged test checks to each locked variant without reselection."""
import argparse
import json
from pathlib import Path

from lighting_diversity_data import sha, write
from summarize_lighting_diversity import summarize


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report', required=True)
    p.add_argument('--out', required=True)
    args = p.parse_args()
    report = json.loads(Path(args.report).read_text())
    if report['status'] != 'succeeded' or report['evaluation_scope'] != 'test':
        raise ValueError('A completed untouched-test report is required')
    if report['training_performed'] or report['selection_performed']:
        raise ValueError('Test evaluation must not fit or select models')
    summarizer = Path(__file__).with_name('summarize_lighting_diversity.py')
    if sha(summarizer) != report['summarizer_sha256']:
        raise ValueError('The original test-check implementation changed')
    sequence = report['plan']['test_sequence']
    if [c['index'] for c in report['cases']] != list(range(sequence['frames'])):
        raise ValueError('Missing or reordered test frames')
    result = {'schema_version': 1, 'status': 'analyzed', 'report_sha256': sha(args.report),
              'summarizer_sha256': sha(summarizer), 'script_sha256': sha(__file__),
              'selected_candidate': report['selected_candidate'], 'selection_performed': False,
              'scope': 'The predeclared checks applied to all three locked variants. This analysis does not change the validation-selected candidate.',
              'variants': {name: summarize(report['cases'], name, report['plan']['gates'])
                           for name in ('scene', 'relative', 'rgb')}}
    write(args.out, result)
    print(json.dumps({k: {'passed': v['passed'], 'gates': v['gates'],
                         'frame_failures': v['candidate_frame_failures']}
                      for k, v in result['variants'].items()}, indent=2))


if __name__ == '__main__':
    main()
