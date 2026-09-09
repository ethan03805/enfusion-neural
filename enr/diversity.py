"""Disjoint scene groups and explicit feature selection for lighting experiments."""
import numpy as np
from . import lighting

FEATURE_COLUMNS={'rgb':list(range(3)),'scene':list(range(20)),
                 'relative':list(range(3))+list(range(6,20))}


def validate_plan(plan):
    scenes=plan['scenes'];cases=plan['cases']
    if len(scenes)!=6 or len({s['id'] for s in scenes})!=6 or len({s['group'] for s in scenes})!=6 or len({s['scene'] for s in scenes})!=6:
        raise ValueError('Six distinct scene definitions and groups required')
    if {split:sum(s['split']==split for s in scenes) for split in ('train','validation','test')}!={'train':4,'validation':1,'test':1}:
        raise ValueError('Expected four train, one validation and one untouched test group')
    mapping={s['id']:s for s in scenes}
    if len(cases)!=60 or len({c['id'] for c in cases})!=60:raise ValueError('Missing or repeated fitting cases')
    for case in cases:
        scene=mapping[case['scene_id']]
        if case['split'] not in ('train','validation') or any(case[k]!=scene[k] for k in ('split','group')):
            raise ValueError('Test access or cross-group leakage in fitting cases')
    if any(sum(c['scene_id']==s['id'] for c in cases)!=12 for s in scenes if s['split']!='test'):
        raise ValueError('Unequal per-scene fitting budget')
    if plan['features']!=FEATURE_COLUMNS:raise ValueError('Changed feature ablation')
    return mapping


def select(x,variant):
    if variant not in FEATURE_COLUMNS or x.shape[-1]!=len(lighting.FEATURES):raise ValueError('Unknown source feature variant')
    return x[...,FEATURE_COLUMNS[variant]]


def names(variant):
    return [lighting.FEATURES[i] for i in FEATURE_COLUMNS[variant]]


def validate_fit_run(run,plan):
    validate_plan(plan)
    if run['status']!='succeeded' or run['phase']!='fit' or run['plan']!=plan:
        raise ValueError('Only completed fitting data may enter training')
    if len(run['cases'])!=len(plan['cases']):raise ValueError('Incomplete fitting run')
    for case,definition in zip(run['cases'],plan['cases']):
        if any(case.get(k)!=v for k,v in definition.items()):raise ValueError('Fitting case differs from preregistration')
    if set(run['scenes'])!={s['id'] for s in plan['scenes'] if s['split']!='test'}:
        raise ValueError('Unplanned scene data in fitting run')


def choose_candidate(models):
    if set(models)!=set(FEATURE_COLUMNS):raise ValueError('All three variants must complete before selection')
    if any(not np.isfinite(m['validation_mse']) or m['validation_mse']<0 for m in models.values()):
        raise ValueError('Invalid validation metric')
    # Deterministic tie order is scene, relative, RGB; no test metrics accepted.
    return min(('scene','relative','rgb'),key=lambda name:models[name]['validation_mse'])
