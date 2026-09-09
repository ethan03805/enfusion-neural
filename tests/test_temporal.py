import unittest
import copy
import hashlib
import json
from pathlib import Path
import numpy as np
from enr import temporal


def plane(h=8,w=10):
    y,x=np.indices((h,w));depth=2.;focal=h/2
    position=np.stack([(x+.5-w/2)*depth/focal,(h/2-y-.5)*depth/focal,np.full((h,w),-depth)],axis=-1)
    normal=np.zeros_like(position);normal[...,2]=1
    return {"position":position,"normal":normal,"ids":np.ones((h,w),np.int32)}


class TemporalTests(unittest.TestCase):
    def test_published_artifact_integrity(self):
        root=Path(__file__).resolve().parents[1]
        path=root/"evidence/lighting-motion-v1.json"
        report=json.loads(path.read_text())
        video=json.loads((root/"evidence/lighting-motion-video-v1.json").read_text())
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),video["report_sha256"])
        self.assertEqual(report["plan_sha256"],hashlib.sha256((root/"scenes/lighting-motion-v1.json").read_bytes()).hexdigest())
        self.assertFalse(report["training_performed"])
        for sequence in report["sequences"]:
            cases=[c for c in report["cases"] if c["sequence"]==sequence["id"]]
            self.assertEqual([c["index"] for c in cases],list(range(32)))
            self.assertEqual(sum("temporal" in c for c in cases),31)
            encoded=next(v for v in video["videos"] if v["sequence"]==sequence["id"])
            self.assertEqual(encoded["frames"],len(cases))

    def test_sequence_rejects_missing_frames_and_changed_path(self):
        plan={"frames":2,"playback_fps":20,"camera_start":[0,0,0],"camera_end":[0,0,0],
              "camera_target":[0,0,-1],"light_start":[0,1,0],"light_end":[1,1,0]}
        definition={"id":"test"}
        seq={"id":"test","frames":[{"index":i,"time_seconds":i/20,"camera":[0,0,0],"light":[i,1,0],"camera_matrix":np.eye(4).tolist()} for i in range(2)]}
        temporal.validate_sequence(seq,definition,plan)
        changed=copy.deepcopy(seq);changed["frames"][1]["camera"][0]=.1
        with self.assertRaises(ValueError):temporal.validate_sequence(changed,definition,plan)
        changed=copy.deepcopy(seq);changed["frames"].pop()
        with self.assertRaises(ValueError):temporal.validate_sequence(changed,definition,plan)

    def test_projection_and_identity_sampling(self):
        d=plane();xy,depth=temporal.project(d["position"],np.eye(4),90)
        y,x=np.indices(d["ids"].shape)
        np.testing.assert_allclose(xy,np.stack([x,y],axis=-1),atol=1e-12)
        np.testing.assert_allclose(depth,2)
        values=np.random.default_rng(2).normal(size=d["position"].shape)
        np.testing.assert_allclose(temporal.sample(values,xy),values,atol=1e-12)

    def test_camera_translation(self):
        d=plane();camera=np.eye(4);camera[0,3]=.5
        xy,_=temporal.project(d["position"],camera,90)
        y,x=np.indices(d["ids"].shape)
        np.testing.assert_allclose(xy[...,0],x-1,atol=1e-12)
        np.testing.assert_allclose(xy[...,1],y,atol=1e-12)

    def test_visibility_rejection_and_error_change(self):
        current=plane();previous=plane()
        xy,mask,_=temporal.correspondence(current,previous,np.eye(4),90)
        self.assertGreater(mask.sum(),40)
        zero=np.zeros_like(current["position"])
        self.assertAlmostEqual(temporal.error_change(zero+.1,zero,xy,mask)["rmse"],.1)
        previous["position"]+=np.array([0,0,-1])
        _,rejected,_=temporal.correspondence(current,previous,np.eye(4),90)
        self.assertFalse(rejected.any())
        previous=plane();previous["ids"][:]=2
        self.assertFalse(temporal.correspondence(current,previous,np.eye(4),90)[1].any())
        with self.assertRaises(ValueError):temporal.error_change(zero,zero,xy,rejected)

    def test_errors_relative_to_changing_reference(self):
        d=plane();xy,mask,_=temporal.correspondence(d,d,np.eye(4),90)
        a=np.zeros_like(d["position"]);b=a+.3
        # A correct lighting change has no reconstruction-error change.
        self.assertEqual(temporal.error_change(b-b,a-a,xy,mask)["rmse"],0)
