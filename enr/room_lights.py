"""Parse actual light readback separately from parameters only sent to the API."""
import math
import re


def check_readback(control, records):
    expected = control['requested']
    creation = ('created case=' + control['case'] + ' requested_lv=' + format(expected['native_LV'], '.9g')
                + ' requested_rgb=1,1,1 requested_attenuation=2 requested_flare=-1')
    followup = control.get('clipping_followup')
    count = 3 if followup else 2
    if len(records) != count or records[0] != creation:
        raise ValueError('Light creation record differs or is incomplete')
    match = re.fullmatch(r'readback enabled=([01]) shadow=([01]) radius=([0-9.eE+\-]+) near=([0-9.eE+\-]+) position=<([^>]+)>', records[1])
    if not match:
        raise ValueError('Malformed light readback')
    radius, near = float(match[3]), float(match[4])
    position = [float(v) for v in match[5].split(',')]
    if len(position) != 3 or not all(math.isfinite(v) for v in [radius, near] + position):
        raise ValueError('Invalid light readback values')
    spec = control['plan']['light']
    checks = {'enabled': bool(int(match[1])) == expected['enabled'],
              'cast_shadow': bool(int(match[2])) == spec['cast_shadow'],
              'radius_raw': math.isclose(radius, spec['radius_m'], abs_tol=1e-5, rel_tol=0),
              'near_plane': math.isclose(near, spec['near_plane_m'], abs_tol=1e-5, rel_tol=0),
              'position': all(abs(a-b) <= .001 for a,b in zip(position, control['world_position']))}
    if followup:
        required = 'clip requested_ev=' + format(followup['plan']['change']['requested_EV_bias'], '.9g')
        if records[2] != required:
            raise ValueError('Light clipping request record differs')
    return {'enabled': bool(int(match[1])), 'cast_shadow': bool(int(match[2])), 'radius_raw': radius,
            'near_plane': near, 'position': position, 'matches_requested': checks,
            'all_readbacks_match': all(checks.values()),
            'radius_magnitude_matches': math.isclose(abs(radius), spec['radius_m'], abs_tol=1e-5, rel_tol=0),
            'radius_note': 'Negative disabled-light radius is retained as a raw mismatch; its internal representation is not established.' if radius < 0 else None,
            'intensity_color_attenuation_and_clip_readback_verified': False}
