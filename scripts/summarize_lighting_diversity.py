"""Check display pixels, retain every failure and apply preregistered quality gates."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image
from lighting_diversity_data import sha,write

def read(path):return np.array(Image.open(path).convert('RGBA'))


def summarize(cases,candidate,gates,include_display=True):
    names=list(cases[0]['metrics']);pairs=[c for c in cases if 'temporal' in c]
    result={'mean_log1p_rmse':{n:float(np.mean([c['metrics'][n]['all']['log1p_rmse'] for c in cases])) for n in names},
            'mean_display_rgb_mae_8bit':{n:float(np.mean([c['outputs'][n]['rgb_mae_8bit'] for c in cases])) for n in names} if include_display else None,
            'mean_temporal_error_rmse':{n:float(np.mean([c['temporal']['error_change'][n]['rmse'] for c in pairs])) for n in names},
            'mean_reference_seed_log1p_rmse':float(np.mean([c['reference_seed_difference']['log1p_rmse'] for c in cases])),
            'temporal_coverage_min_mean_max':[float(f([c['temporal']['coverage']['valid_fraction'] for c in pairs])) for f in (np.min,np.mean,np.max)]}
    contrast=[c for c in cases if c['marking_contrast']['reference'] is not None]
    result['mean_absolute_marking_contrast_error']={n:float(np.mean([abs(c['marking_contrast'][n]-c['marking_contrast']['reference']) for c in contrast])) for n in names} if contrast else None
    losses=result['mean_log1p_rmse'];temporal_losses=result['mean_temporal_error_rmse']
    result['spatial_improvement_fractions']={n:(losses[n]-losses[candidate])/max(losses[n],1e-12) for n in ('source','affine-scene','affine-rgb')}
    result['spatial_gain_reference_seed_sensitivity']={}
    for n in ('source','affine-scene','affine-rgb'):
        gain=losses[n]-losses[candidate]
        paired_gain=float(np.mean([c['paired_reference_metrics'][n]['log1p_rmse']-c['paired_reference_metrics'][candidate]['log1p_rmse'] for c in cases]))
        result['spatial_gain_reference_seed_sensitivity'][n]={'independent_gain':gain,'paired_gain':paired_gain,'absolute_sensitivity':abs(gain-paired_gain),
                                                           'resolved':gain>0 and abs(gain-paired_gain)<=gates['reference_noise_fraction_of_measured_gain_max']*gain}
    gain=temporal_losses['source']-temporal_losses[candidate]
    paired_gain=float(np.mean([c['temporal']['paired_error_change']['source']['rmse']-c['temporal']['paired_error_change'][candidate]['rmse'] for c in pairs]))
    result['temporal_gain_reference_seed_sensitivity']={'independent_gain':gain,'paired_gain':paired_gain,'absolute_sensitivity':abs(gain-paired_gain),
                                                      'resolved':gain>0 and abs(gain-paired_gain)<=gates['reference_noise_fraction_of_measured_gain_max']*gain}
    failures=[];region_missing=[]
    for c in cases:
        issues=[]
        for region in ('object_edges','thin_posts'):
            a,b=c['metrics'][candidate][region],c['metrics']['source'][region]
            if a is None or b is None:region_missing.append({'case':c['id'],'region':region})
            elif a['log1p_rmse']>b['log1p_rmse']*(1+gates['maximum_boundary_or_post_rmse_regression_fraction']):issues.append(region)
        contrast=c['marking_contrast']
        if contrast['reference'] is not None:
            a=abs(contrast[candidate]-contrast['reference']);b=abs(contrast['source']-contrast['reference'])
            if a-b>gates['maximum_marking_contrast_error_regression']:issues.append('marking_contrast')
        if issues:failures.append({'case':c['id'],'regions':issues})
    result['candidate_frame_failures']=failures;result['missing_regions']=region_missing
    result['gates']={'spatial_improvement':all(v>=gates['minimum_mean_spatial_improvement_fraction'] for v in result['spatial_improvement_fractions'].values()),
                     'spatial_gain_resolved':all(v['resolved'] for v in result['spatial_gain_reference_seed_sensitivity'].values()),
                     'boundaries_and_posts':not region_missing and not any(set(f['regions'])&{'object_edges','thin_posts'} for f in failures),
                     'marking_contrast':False,
                     'temporal_non_regression':temporal_losses[candidate]<=temporal_losses['source']*(1+gates['maximum_temporal_rmse_regression_fraction'])}
    # Original-room regression lacks a marking panel; its contrast gate is untested.
    result['gates']['marking_contrast']=all(c['marking_contrast']['reference'] is not None for c in cases) and not any('marking_contrast' in f['regions'] for f in failures)
    result['passed']=all(result['gates'].values())
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--root',required=True);p.add_argument('--out',required=True)
    a=p.parse_args();root=Path(a.root);report=json.loads((root/'run.json').read_text())
    if report['status']!='succeeded':raise ValueError('Incomplete evaluation')
    report['display']=json.loads((root/'display.json').read_text());report['summarizer_sha256']=sha(__file__)
    for c in report['cases']:
        folder=root/c['id'];raw=Path(c['raw_folder']);target=read(raw/'independent.png');source=read(raw/'source.png')
        if sha(raw/'source.png')!=c['raw_source_png_sha256'] or sha(raw/'independent.png')!=c['raw_reference_png_sha256']:raise ValueError('Changed raw display image')
        c['display_roundtrip']={}
        for name,expected in [('source',source),('reference',target)]:
            delta=np.abs(read(folder/(name+'.png')).astype(np.int16)-expected.astype(np.int16))
            c['display_roundtrip'][name]={'rgba_max_error_8bit':int(delta.max())}
            if delta.max()>1:raise ValueError('Display transform roundtrip differs')
        for name,record in c['outputs'].items():
            path=folder/(name+'.png');value=read(path)
            if value.shape!=target.shape or not np.array_equal(value[...,3],source[...,3]):raise ValueError('Changed alpha or dimensions')
            delta=value[...,:3].astype(np.float64)-target[...,:3]
            record.update(png_sha256=sha(path),bytes=path.stat().st_size,dimensions=[value.shape[1],value.shape[0]],
                          rgb_mae_8bit=float(np.abs(delta).mean()),rgb_rmse_8bit=float(np.sqrt(np.mean(delta**2))),alpha_exact=True)
        del c['raw_folder']
    for s in report['sequences']:
        cases=[c for c in report['cases'] if c['sequence']==s['id']]
        s.update(summarize(cases,report['selected_candidate'],report['plan']['gates']))
    scope=report['evaluation_scope']
    expected=(report['plan']['test_sequence']['frames'] if scope!='regression' else 0)
    if scope!='test':expected+=sum(len(s['frames']) for s in report['regression_rendering']['sequences'])
    if len(report['cases'])!=expected:raise ValueError('Missing test/regression cases')
    report['verification']={'all_display_roundtrips_within_one_code_value':True,'all_output_alpha_exact':True,
                            'frozen_models':True,'all_frames_in_declared_scope_reported':True,
                            'test_gate_passed':next((s['passed'] for s in report['sequences'] if s['split']=='test'),None),
                            'live_engine_performance_verified':False}
    write(a.out,report)
    print(json.dumps({'candidate':report['selected_candidate'],'sequences':report['sequences']},indent=2))


if __name__=='__main__':main()
