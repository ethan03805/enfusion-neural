"""Retain the bounded transition check, including unsuccessful UI observations."""
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    target = ROOT / 'evidence/playable-transitions-v1.json'
    if target.exists():
        raise FileExistsError('Retain the original transition evaluation')
    control = ROOT / 'runs/transitions-control-v1'
    run = ROOT / 'runs/playable-transitions-v1'
    plan_path = ROOT / 'scenes/playable-transitions-v1.json'
    plan, observer = read(plan_path), read(control / 'observer.json')
    assert sha(plan_path) == observer['plan_sha256']
    assert sha(ROOT / 'scripts/check_playable_transitions.py') == plan['driver_sha256']
    actions = [read(p) for p in sorted(control.glob('[0-9]*.json'))]
    for action in actions:
        action['window'] = {'title': action['window']['title'], 'id': action['window']['id']}
        for shot in action['screenshots']:
            assert sha(control / 'screenshots' / shot['file']) == shot['sha256']
    events = (run / 'companion/events.log').read_text()
    rows = list(csv.DictReader((run / 'companion/frames.csv').open(newline='')))
    for row in rows:
        for key in row:
            row[key] = float(row[key])
    game_pid = observer['game_pid']
    changes = observer['foreground_changes']
    away = next(c for c in changes if c['qpc_ms'] > observer['ready_qpc_ms'] and c['pid'] != game_pid)
    back = next(c for c in changes if c['qpc_ms'] > away['qpc_ms'] and c['pid'] == game_pid)
    hides = [float(x) for x in re.findall(r'^hide ([0-9.]+)$', events, re.M)]
    bypass = float(re.search(r'^bypass 1 ([0-9.]+)$', events, re.M)[1])
    focus_hide = next(x for x in hides if away['qpc_ms'] <= x < back['qpc_ms'])
    fresh = [r for r in rows if r['present_call_qpc_ms'] >= back['qpc_ms'] and r['capture_qpc_ms'] >= back['qpc_ms']]
    after_hide = [r for r in rows if focus_hide < r['present_call_qpc_ms'] < back['qpc_ms']]
    completed = re.search(r'^complete frames (\d+) elapsed_ms ([0-9.]+)$', events, re.M)
    assert completed and int(completed[1]) == len(rows)
    gates = {
        'exact_extracted_package_addon_settings': observer['actual_settings_and_addon_match'],
        'visible_menu_open_and_close': False,
        'source_menu_usable_through_bypass': False,
        'overlay_hides_while_game_loses_focus': bool(focus_hide and not after_hide),
        'fresh_captured_frames_presented_after_return': bool(fresh),
        'F10_success_game_continues': observer['launcher_exit_code'] == 0 and observer['game_alive_five_seconds_after_companion_exit'],
        'no_crash_or_presentation_timeout': observer['status'] == 'completed' and 'presentation wait timeout ' not in events,
    }
    closed = datetime.now(timezone.utc)
    report = {
        'schema_version': 1, 'outcome': 'partial_control_verification_menu_and_complete_visual_recovery_unverified',
        'started_at': plan['started_at'], 'closed_at': closed.isoformat(),
        'minutes_since_original_start': (closed - datetime.fromisoformat(plan['started_at'])).total_seconds() / 60,
        'within_original_20_minute_bound': closed <= datetime.fromisoformat(plan['deadline']),
        'plan_sha256': sha(plan_path), 'plan': plan, 'gates': gates, 'all_gates_pass': all(gates.values()),
        'package_scope': 'Exact extracted release play.py invoked with the existing Python runtime; Start-Playable.cmd itself was not clicked in this session. Unchanged guarded ZIP.',
        'session': {'scene': 'town', 'preset': 'combined', 'automatic': False, 'native_frame_count': len(rows),
                    'native_elapsed_ms': float(completed[2]), 'foreground_changes': changes,
                    'game_alive_five_seconds_after_companion_exit': True, 'owned_session_cleaned_up': True},
        'software_observations': {
            'f8_handler_to_hide_ms': hides[0] - bypass,
            'foreground_away_qpc_ms': away['qpc_ms'], 'focus_hide_qpc_ms': focus_hide,
            'observed_foreground_change_to_hide_ms': focus_hide - away['qpc_ms'],
            'foreground_return_qpc_ms': back['qpc_ms'], 'focus_away_ms': back['qpc_ms'] - away['qpc_ms'],
            'frames_presented_between_hide_and_observed_return': len(after_hide),
            'fresh_frames_after_observed_return': len(fresh), 'first_fresh_frame': fresh[0] if fresh else None,
            'observed_return_to_first_fresh_present_ms': fresh[0]['present_call_qpc_ms'] - back['qpc_ms'] if fresh else None,
        },
        'visual_review': [
            'Reviewed each retained UI screenshot after its action. Initial and source-bypass views are complete 2560x1440 street views.',
            'Escape did not show a menu with enhancement, including a settled observation. One diagnostic Escape while bypassed also did not show a menu. No unseen Resume button was clicked; dependent menu steps were not attempted.',
            'While another window was foreground, the source game remained visible behind it. That screenshot contains unrelated application content and remains private.',
            'After game activation, screenshots report 1280x720 at origin 1280,720 and show only part of the street scene. The same partial view persists after F10. Native events record no resize. Full-frame visual recovery is not accepted; cause is not isolated.',
            'Native capture/presentation resumes with fresh timestamps; this establishes processing recovery only. It does not establish complete display placement or physical input behavior.',
        ],
        'retained_tool_error': 'Metadata-only get_window_state after Steam activation was rejected. Requested text in the next observation without repeating activation; no Steam text is published.',
        'limits': 'Foreground is polled at a nominal 10 ms. Software event differences are observed offsets, not precise transition bounds, physical-input or display latency. This stationary control session is not a new performance benchmark. No WASD/mouse, menu, full visual recovery or appearance acceptance claim.',
        'next_requirement': 'Inspect the isolated session menu/input context and window activation geometry before another live transition trial; require specific source or geometry evidence and a frozen correction. Do not repeat Escape blindly.',
        'actions': actions, 'native_events': events.splitlines(),
        'retained_hashes': {p.relative_to(ROOT).as_posix(): sha(p) for p in [plan_path, Path(__file__), ROOT / 'scripts/check_playable_transitions.py', control / 'observer.json', control / 'launcher.log', run / 'launch.json', run / 'companion/events.log', run / 'companion/frames.csv']},
        'publication': 'Only redacted evidence and documentation are published; all UI screenshots remain local. No package, model or shader change.',
    }
    target.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['outcome', 'gates', 'minutes_since_original_start', 'within_original_20_minute_bound', 'software_observations']}, indent=2))


if __name__ == '__main__':
    main()
