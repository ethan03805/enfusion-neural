import copy
import json
import math
from pathlib import Path
import tempfile
import unittest

from PIL import Image
from enr.sequence import camera, load_config, verify

ROOT = Path(__file__).resolve().parents[1]


class SequenceContract(unittest.TestCase):
    def setUp(self):
        self.config = load_config(ROOT/"scenes/arland-motion-v1.json")

    def test_path_endpoints_and_static(self):
        p,d = camera(self.config,0)
        self.assertEqual(p,self.config["position_start"])
        self.assertAlmostEqual(d[0],1)
        p,d = camera(self.config,self.config["samples"]-1)
        self.assertEqual(p,self.config["position_end"])
        self.assertAlmostEqual(d[2],math.cos(math.radians(98)))
        self.config["samples"] = 1
        self.assertEqual(camera(self.config,0)[0],self.config["position_start"])

    def fixture(self,directory):
        c = copy.deepcopy(self.config);c["samples"]=2;c["dimensions"]=[128,128]
        delta = 128/(20*math.tan(math.radians(c["vertical_fov_degrees"])/2))
        events = [{"event":"setting","module":m,"key":k,"value":v}
                  for m,fields in c["quality_readback"].items() for k,v in fields.items()]
        events.append({"event":"environment","date":c["date"],"weather_state":"Clear","hour":13,"wind_speed_mps":0,"wind_direction_degrees":0})
        target = Path(directory)/"profile/profile";target.mkdir(parents=True)
        for i in range(2):
            p,d = camera(c,i)
            events.append({"event":"sample","index":i,"world_frame":500+i*6,"simulation_seconds":8.1+i*.2,"position":p,"direction":d})
            events.append({"event":"projection","index":i,"width":128,"height":128,"up_xy":[64,64-delta],"right_xy":[64+delta,64],"far_plane":c["far_plane_m"],"hdr_brightness":c["hdr_brightness"]})
            Image.new("RGBA",(128,128),(20+i,30,40,255)).save(target/f"sample-{i:05d}.png")
        run={"status":"succeeded","directory":str(directory),"run_id":"test","addon_sha256":{}}
        return c,events,run

    def test_rejects_missing_samples_camera_drift_and_wrong_settings(self):
        with tempfile.TemporaryDirectory() as temp:
            c,events,run = self.fixture(temp)
            def check(items):
                (Path(temp)/"console.log").write_text("\n".join("ENR "+json.dumps(e) for e in items))
                return verify(c,run)
            self.assertEqual(len(check(events)["frames"]),2)
            bad=copy.deepcopy(events);bad[0]["value"]=-1
            with self.assertRaisesRegex(ValueError,"settings readback"):check(bad)
            bad=copy.deepcopy(events);next(e for e in bad if e["event"]=="sample")["position"][0]+=1
            with self.assertRaisesRegex(ValueError,"Camera mismatch"):check(bad)
            bad=[e for e in events if not(e["event"]=="sample" and e["index"]==1)]
            with self.assertRaisesRegex(ValueError,"telemetry"):check(bad)
            bad=copy.deepcopy(events);next(e for e in bad if e["event"]=="projection")["up_xy"][1]+=1
            with self.assertRaisesRegex(ValueError,"Projection mismatch"):check(bad)
            bad=copy.deepcopy(events);next(e for e in bad if e["event"]=="environment")["hour"]=14
            with self.assertRaisesRegex(ValueError,"Environment drift"):check(bad)
            bad=copy.deepcopy(events);next(e for e in bad if e["event"]=="sample")["simulation_seconds"]=float("nan")
            with self.assertRaisesRegex(ValueError,"Invalid capture time"):check(bad)

    def test_rejects_unexpected_frame_and_bad_dimensions(self):
        with tempfile.TemporaryDirectory() as temp:
            c,events,run=self.fixture(temp)
            (Path(temp)/"console.log").write_text("\n".join("ENR "+json.dumps(e) for e in events))
            Image.new("RGBA",(128,128)).save(Path(temp)/"profile/profile/sample-00002.png")
            with self.assertRaisesRegex(ValueError,"frame files"):verify(c,run)

    def test_rejects_invalid_environment_before_generating_script(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/"config.json"
            for key,value in [("date",[1989,2,30]),("date",[1989,6,"21; code"]),
                              ("hour",float("nan")),("wind_speed_mps","0; code"),
                              ("wind_direction_degrees",361),("timeout_seconds",8)]:
                with self.subTest(key=key,value=value):
                    bad=copy.deepcopy(self.config);bad[key]=value
                    path.write_text(json.dumps(bad))
                    with self.assertRaises(ValueError):load_config(path)


if __name__ == "__main__": unittest.main()
