"""Write the original scene layouts and preregistered diversity experiment.

No rendering or learning. Refuses to replace an existing frozen plan.
"""
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def write(path,value):
    if path.exists():raise ValueError('Definition already exists: '+str(path))
    path.write_bytes((json.dumps(value,indent=2)+'\n').encode('utf-8'))


def box(name,position,size,material):
    return {'id':name,'position':position,'size':size,'material':material}


def main():
    definitions=[
        ('corner-gallery','train','Open L-shaped gallery with a tall return wall',[
            box('return-wall',[-1.15,1.6,1.4],[.25,2.5,2.8],'red'),
            box('display-plinth',[1.1,1.6,.4],[1.6,1.5,.8],'neutral'),
            box('low-screen',[-.1,-.3,.4],[1.2,.3,.8],'blue')]),
        ('covered-court','train','Covered alcove and a narrow opening under a canopy',[
            box('canopy',[-.9,1.6,2.5],[3,2.8,.2],'neutral'),
            box('canopy-pillar',[-2,1.0,1.25],[.3,.3,2.5],'rough'),
            box('occluding-screen',[.3,1.8,1.15],[.3,2.3,2.3],'blue')]),
        ('staggered-workshop','train','Staggered benches, a shelf and reflective equipment',[
            box('bench-left',[-1.2,.8,.5],[1.6,1.8,1],'rough'),
            box('bench-right',[1.4,2.2,.85],[1.4,1.4,1.7],'blue'),
            box('shelf',[.0,2.7,2.4],[3.8,.8,.16],'metal'),
            box('upright',[.7,2.7,1.2],[.16,.8,2.4],'neutral')]),
        ('split-passage','train','Two corridors and a low opening between partitions',[
            box('partition-left',[-1.1,.8,1.4],[.25,3.4,2.8],'neutral'),
            box('partition-right',[1.1,1.7,1.4],[.25,2.6,2.8],'red'),
            box('lintel',[0,2.8,2.7],[2.2,.3,.45],'blue'),
            box('low-block',[-1.9,1.9,.5],[1.3,1.0,1.0],'rough')]),
        ('offset-loading-bay','validation','Offset loading platform and canopy outside training layouts',[
            box('loading-platform',[-1.0,2,.4],[2.3,2.2,.8],'neutral'),
            box('overhang',[.9,2.2,2.7],[2.8,2.0,.2],'blue'),
            box('return-screen',[.25,1.6,1.2],[.3,2.6,2.4],'rough'),
            box('rear-crate',[-1.6,2.6,1.25],[1,1,.9],'red')]),
        ('cross-courtyard','test','Unseen crossed partitions, recessed court and reflective block',[
            box('cross-a',[-.5,2.0,1.3],[3.3,.25,2.6],'blue'),
            box('cross-b',[-1.3,1.4,1.1],[.25,2.8,2.2],'neutral'),
            box('recess-roof',[1.55,2.75,2.8],[2.1,1.5,.2],'rough'),
            box('raised-block',[1.8,.9,.65],[1.1,1.3,1.3],'metal')])]
    scenes=[]
    for index,(name,split,description,objects) in enumerate(definitions):
        walls=[box('floor',[0,.5,-.1],[6,7,.2],'neutral'),
               box('back',[0,4,2],[6,.2,4],['neutral','red','blue'][index%3]),
               box('left',[-3,.5,2],[.2,7,4],['red','blue','neutral'][index%3]),
               box('right',[3,.5,2],[.2,7,4],['blue','neutral','red'][index%3])]
        # Every layout has a directly visible marking panel plus thin geometry.
        x=[.5,-.2,.3,-.3,.7,.1][index];y=-.55;z=1.15
        marks=[box('mark-board',[x,y,z],[1.15,.035,.62],'white')]
        for j,(offset,width) in enumerate(zip([-.43,-.24,-.05,.15,.4],[.025,.06,.035,.10,.045])):
            marks.append(box('mark-bar-'+str(j),[x+offset,y-.024,z],[width,.012,.45],'dark'))
        spheres=[{'id':'reflective-sphere','position':[-1.85,-.45,.42],'radius':.42,'material':'metal'},
                 {'id':'rough-sphere','position':[1.6,-.7,.35],'radius':.35,'material':'rough'}]
        config={'schema_version':1,'id':name+'-v1','group':name+'-v1','split':split,
                'license':'MIT; original procedural geometry and markings','material_library':'material-room-v1.json',
                'description':description,'boxes':walls+objects+marks,'spheres':spheres,
                'thin_posts':{'diameters_m':[.015,.03,.06],'height_m':1.7,'x_positions':[-.45,-.12,.25],'y':-1.4,'material':'dark'}}
        path=ROOT/'scenes'/(name+'-v1.json');write(path,config)
        scenes.append({'id':name,'scene':path.name,'group':config['group'],'split':split})
    plan={'schema_version':1,'id':'lighting-diversity-v1','scope':'Six original layouts with disjoint train/validation/test groups; fixed-budget source-feature ablation',
          'dimensions':[480,270],'samples':2048,'evaluation_samples':8192,
          'source_diffuse_bounces':1,'reference_diffuse_bounces':12,'max_bounces':12,'glossy_bounces':12,
          'vertical_fov_degrees':42,'light_power_watts':900,'light_size_m':2,
          'camera_target':[0,.8,1.25],'paired_seed':311,'independent_seed':7001,'seed_stride':31,
          'scenes':scenes,'cases':[],
          'training':{'seed':17,'steps':10000,'batch_size':1024,'pixels_per_case':8192,'hidden_width':32,'learning_rate':.001,'check_every':250},
          'features':{'rgb':list(range(3)),'scene':list(range(20)),'relative':list(range(3))+list(range(6,20))},
          'baselines':['identity','affine-scene','affine-rgb','frozen-lighting-v1','frozen-lighting-rgb-v1'],
          'sampling':'Same sampled pixel IDs, minibatch indices, step count and validation checkpoints for the three neural variants. Capacity differs only in input-layer columns. Uniform valid-surface pixels; no test-guided resampling.',
          'selection':'Lowest mean validation log1p residual MSE checkpoint per model. Select the candidate variant by the same validation metric before test access. Never choose on test or regression results.',
          'gates':{'minimum_mean_spatial_improvement_fraction':.05,'maximum_boundary_or_post_rmse_regression_fraction':.02,
                   'maximum_marking_contrast_error_regression':.002,'maximum_temporal_rmse_regression_fraction':.02,
                   'reference_noise_fraction_of_measured_gain_max':.5,
                   'rule':'Candidate must beat identity and both newly fitted affine baselines by 5% mean log1p RMSE on the untouched test scene; boundaries and posts may regress at most 2% relative to source on any evaluated frame, and marking-contrast error at most 0.002 weighted-log units. Mean temporal error may regress at most 2%. Reference-seed sensitivity above half a claimed gain makes that claim inconclusive, not passed. Report every variant and frame; never relax gates after inspection.'},
          'test_sequence':{'frames':48,'playback_fps':20,'camera_start':[-1,-7.4,3.0],'camera_end':[1.1,-6.8,3.5],
                           'light_start':[-1.1,.0,3.8],'light_end':[1.1,.9,3.8],'publication_frame':24},
          'regression_plan':'lighting-motion-v1.json','regression_policy':'Evaluate all existing 64 frames with frozen new models and old model controls. Retain old references and report their sampling limit. Do not use regression targets for selection.',
          'test_access':'Render and evaluate test only after saving all trained model hashes and the validation-selected candidate. No human inspection of test renders before that lock.',
          'limitations':['Original material constants; one untouched synthetic test layout is not all-asset coverage','Static original geometry; moving camera and one area light','Synthetic paired targets are not Enfusion ground truth','Integration and varied Reforger environments require separate measured evidence']}
    for s in scenes:
        if s['split']=='test':continue
        for i in range(12):
            cam=[[-1,-7.5,3],[0,-7.5,3],[1,-7.5,3],[.0,-6.7,3.6]][i%4]
            light=[[-1,.2,3.8],[0,.6,3.8],[1,1.,3.8]][i//4]
            plan['cases'].append({'id':s['id']+'-'+str(i).zfill(2),'scene_id':s['id'],'group':s['group'],'split':s['split'],'index':i,'camera':cam,'light':light})
    write(ROOT/'scenes/lighting-diversity-v1.json',plan)
    print('Defined four training layouts, one validation layout and one untouched test layout; 60 train/validation cases.')


if __name__=='__main__':main()
