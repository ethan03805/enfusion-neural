"""CPU file protocol controls; these tests do not certify Workbench presentation."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from PIL import Image
from enr import model
from enr import image_bridge,sequence

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bridge_probe',ROOT/'scripts/probe_enfusion_image_bridge.py')
bridge=importlib.util.module_from_spec(spec);spec.loader.exec_module(bridge)


class ImageBridgeControls(unittest.TestCase):
    def test_file_controls_preserve_alpha_and_cpu_model_at_odd_dimensions(self):
        source=np.random.default_rng(23).integers(0,256,(7,11,4),dtype=np.uint8)
        weights,_=model.load(ROOT/'models/bootstrap-v0.json')
        for mode in ('identity','invert','v0'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as name:
                folder=Path(name);Image.fromarray(source).save(folder/'bridge-input.png')
                report=bridge.process_image(folder,mode)
                actual=np.array(Image.open(folder/'bridge-output.png'))
                expected=source.copy()
                if mode=='invert':expected[...,:3]=255-source[...,:3]
                if mode=='v0':expected[...,:3]=np.floor(model.infer(source[...,:3].astype(np.float32)/255,weights,rows=3)*255+.5).astype(np.uint8)
                np.testing.assert_array_equal(actual,expected)
                self.assertTrue(report['alpha_exact'])
                self.assertEqual(report['dimensions'],[11,7])
                self.assertEqual(json.loads((folder/'bridge-worker.json').read_text())['output_sha256'],bridge.digest(folder/'bridge-output.png'))
                self.assertTrue((folder/'bridge-worker.done').is_file())

    def test_rejects_implicit_color_conversion(self):
        with tempfile.TemporaryDirectory() as name:
            folder=Path(name);Image.new('RGB',(11,7)).save(folder/'bridge-input.png')
            with self.assertRaises(ValueError):bridge.process_image(folder,'identity')
            self.assertFalse((folder/'bridge-worker.done').exists())

    def fixture(self,root,mode='invert',bad_screen=False,failure=False):
        c=sequence.load_config(ROOT/'scenes/arland-motion-v1.json');c['samples']=1;w,h=129,131;c['dimensions']=[w,h]
        cap='20260909T010000-1234567890';val='20260909T000000-1234567890'
        run_dir=root/'runs'/cap;profile=run_dir/'profile/profile';profile.mkdir(parents=True)
        validation=root/'runs'/val;validation.mkdir()
        bridge.write_json(root/'capture-config.json',c)
        source=np.random.default_rng(31).integers(0,256,(h,w,4),dtype=np.uint8)
        Image.fromarray(source).save(profile/'bridge-input.png');worker=bridge.process_image(profile,mode)
        out=np.array(Image.open(profile/'bridge-output.png'))
        Image.fromarray(out).save(profile/'bridge-texture.png')
        screen=out.copy()
        if bad_screen:screen[2,3,1]^=1
        Image.fromarray(screen).save(profile/'bridge-presented.png')
        events=[{'event':'requested','mode':mode,'width':w,'height':h,'world_frame':10,'tick_ms':100},
                {'event':'file_texture','loaded':1,'tick_ms':110},
                {'event':'presented','texture_size':[w,h],'screen_size':[w,h],'visible':1,'raw_requested':1,'world_frame':11,'tick_ms':120}]
        for name in ('bridge-input','bridge-texture','bridge-presented'):
            events.append({'event':'saved','name':name+'.png','width':w,'height':h,'stride':w*4,'success':1,'tick_ms':130})
        events.append({'event':'completed','tick_ms':140})
        if failure:events.append({'event':'failure','reason':'local PNG load rejected','tick_ms':141})
        p,d=sequence.camera(c,0)
        native=[{'event':'camera','position':p,'direction':d},{'event':'started','viewport_width':w,'viewport_height':h}]
        readings=[{'event':'setting','module':m,'key':k,'value':v} for m,fields in c['quality_readback'].items() for k,v in fields.items()]
        readings.append({'event':'environment',**{k:c[k] for k in ['date','weather_state','hour','wind_speed_mps','wind_direction_degrees']}})
        console='\n'.join(prefix+json.dumps(e) for prefix,rows in [('ENR_BRIDGE ',events),('ELAB ',native),('ENR ',readings)] for e in rows)
        (run_dir/'console.log').write_text(console)
        run={'run_id':cap,'command':'capture','status':'succeeded','world':c['world'],'position':p,'direction':d}
        bridge.write_json(run_dir/'run.json',run);bridge.write_json(validation/'run.json',{'run_id':val,'command':'validate','status':'succeeded'})
        snapshot=run_dir/'addon/Scripts/Game';snapshot.mkdir(parents=True)
        for name in ('ENR_ImageBridge.c','ENR_BridgeEntities.c'):(snapshot/name).write_text('unit fixture; not actual engine evidence\n')
        report={'schema_version':1,'mode':mode,'capture_run':cap,'validation_run':val,'capture_status':'succeeded','entities_requested':False,
                'worker_records':[worker],'worker_errors':[],'worker_script_sha256':worker['worker_sha256']}
        for key,path in [('config_sha256',root/'capture-config.json'),('console_sha256',run_dir/'console.log'),
                         ('capture_manifest_sha256',run_dir/'run.json'),('validation_manifest_sha256',validation/'run.json'),
                         ('probe_sha256',snapshot/'ENR_ImageBridge.c'),('entities_script_sha256',snapshot/'ENR_BridgeEntities.c')]:report[key]=bridge.digest(path)
        bridge.write_json(root/'bridge.json',report)

    def test_display_evidence_does_not_certify_render_pass_or_accept_one_wrong_pixel(self):
        for changed in (False,True):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as name:
                root=Path(name);self.fixture(root,bad_screen=changed);result=image_bridge.inspect(root)
                self.assertEqual(result['verification']['pixel_exact_screenshot_ui_return'],not changed)
                self.assertFalse(result['verification']['live_neural_lighting_integration'])
                self.assertFalse(result['verification']['scene_buffer_access'])
                self.assertEqual(result['comparisons']['screen_return']['rgba_max_error_8bit'],int(changed))

    def test_outer_capture_success_and_changed_evidence_cannot_pass_bridge(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);self.fixture(root,failure=True);result=image_bridge.inspect(root)
            self.assertEqual(result['capture_status'],'succeeded')
            self.assertFalse(result['verification']['pixel_exact_screenshot_ui_return'])
            self.assertIn('local PNG load rejected',result['errors'])
            path=next((root/'runs').glob('*/console.log'));path.write_text(path.read_text()+'\nchanged')
            with self.assertRaisesRegex(ValueError,'Changed bridge evidence'):image_bridge.inspect(root)

    def test_native_capture_failure_retains_cause_even_with_valid_image_files(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);self.fixture(root)
            report=json.loads((root/'bridge.json').read_text());run_path=root/'runs'/report['capture_run']/'run.json'
            run=json.loads(run_path.read_text());run['status']='failed';bridge.write_json(run_path,run)
            report.update(capture_status='failed',capture_error='Workbench timed out.',capture_manifest_sha256=bridge.digest(run_path))
            bridge.write_json(root/'bridge.json',report)
            checked=image_bridge.inspect(root)
            self.assertIn('Workbench timed out.',checked['errors'])
            self.assertFalse(any(checked['verification'].values()))

    def test_additional_world_requires_observed_resource_without_relaxing_default(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);config=root/'config.json';c=sequence.load_config(ROOT/'scenes/arland-motion-v1.json')
            c['world']='worlds/UnitFixture/UnitFixture.ent';bridge.write_json(config,c)
            with self.assertRaises(ValueError):sequence.load_config(config)
            with self.assertRaisesRegex(ValueError,'completed resource inventory'):image_bridge.load_probe_config(config)
            cap='20260909T030000-1234567890';val='20260909T020000-1234567890';inventory=root/'resources.json'
            for run,command in [(cap,'capture'),(val,'validate')]:
                folder=root/'runs'/run;folder.mkdir(parents=True)
                bridge.write_json(folder/'run.json',{'run_id':run,'command':command,'status':'succeeded'})
            folder=root/'runs'/cap;snapshot=folder/'addon/Scripts/WorkbenchGame/ENR_ResourceProbe.c';snapshot.parent.mkdir(parents=True);snapshot.write_text('unit fixture\n')
            console=folder/'console.log';console.write_text('ENR_RESOURCE query=Fixture resource={1234567890ABCDEF}worlds/UnitFixture/UnitFixture.ent path=fixture\n')
            record={'schema_version':1,'status':'succeeded','capture_run':cap,'validation_run':val,'console_sha256':bridge.digest(console),'probe_sha256':bridge.digest(snapshot)}
            bridge.write_json(inventory,record)
            checked,binding=image_bridge.load_probe_config(config,inventory)
            self.assertEqual(checked['world'],c['world']);self.assertEqual(binding['inventory_sha256'],bridge.digest(inventory))
            c['world']='worlds/Other/Other.ent';bridge.write_json(config,c)
            with self.assertRaisesRegex(ValueError,'was not observed'):image_bridge.load_probe_config(config,inventory)
            c['world']=None;bridge.write_json(config,c)
            with self.assertRaises(ValueError):sequence.load_config(config)

    def test_resource_only_inventory_requires_real_completion_and_unchanged_manifests(self):
        with tempfile.TemporaryDirectory() as name:
            root=Path(name);config=root/'config.json';c=sequence.load_config(ROOT/'scenes/arland-motion-v1.json')
            c['world']='worlds/UnitFixture/UnitFixture.ent';bridge.write_json(config,c)
            inv='20260909T030000-1234567890';val='20260909T020000-1234567890'
            folder=root/'runs'/inv;vfolder=root/'runs'/val;vfolder.mkdir(parents=True)
            snapshot=folder/'addon/Scripts/WorkbenchGame';snapshot.mkdir(parents=True)
            for f in ('ENR_ResourceProbe.c','ENR_ResourceInventoryPlugin.c'):(snapshot/f).write_text('unit fixture; not native evidence\n')
            native={'run_id':inv,'command':'resource-inventory','status':'succeeded','process_exit_code':0,'terminated_owned_process':False}
            bridge.write_json(folder/'run.json',native)
            bridge.write_json(vfolder/'run.json',{'run_id':val,'command':'validate','status':'succeeded'})
            console=folder/'console.log'
            trace='ENR_INVENTORY {"event":"started"}\nENR_RESOURCE query=Fixture resource={1234567890ABCDEF}worlds/UnitFixture/UnitFixture.ent path=fixture\nENR_RESOURCE_DONE query=Fixture count=1 success=1\nENR_INVENTORY {"event":"completed"}\n'
            console.write_text(trace)
            record={'schema_version':1,'status':'succeeded','operation':'resource-inventory','inventory_run':inv,'validation_run':val,'queries':['Fixture'],
                    'inventory_manifest_sha256':bridge.digest(folder/'run.json'),'validation_manifest_sha256':bridge.digest(vfolder/'run.json'),
                    'probe_sha256':bridge.digest(snapshot/'ENR_ResourceProbe.c'),'plugin_sha256':bridge.digest(snapshot/'ENR_ResourceInventoryPlugin.c'),
                    'console_sha256':bridge.digest(console)}
            inventory=root/'resources.json';bridge.write_json(inventory,record)
            checked,binding=image_bridge.load_probe_config(config,inventory)
            self.assertEqual(checked['world'],c['world']);self.assertEqual(binding['inventory_run'],inv)
            self.assertNotIn('capture_run',binding)
            native['process_exit_code']=1;bridge.write_json(folder/'run.json',native)
            with self.assertRaisesRegex(ValueError,'manifest changed'):image_bridge.load_probe_config(config,inventory)
            record['inventory_manifest_sha256']=bridge.digest(folder/'run.json');bridge.write_json(inventory,record)
            with self.assertRaisesRegex(ValueError,'exit naturally'):image_bridge.load_probe_config(config,inventory)
            native['process_exit_code']=0;bridge.write_json(folder/'run.json',native)
            record['inventory_manifest_sha256']=bridge.digest(folder/'run.json')
            console.write_text(trace.replace('ENR_INVENTORY {"event":"completed"}\n',''))
            record['console_sha256']=bridge.digest(console);bridge.write_json(inventory,record)
            with self.assertRaisesRegex(ValueError,'callback did not complete'):image_bridge.load_probe_config(config,inventory)
