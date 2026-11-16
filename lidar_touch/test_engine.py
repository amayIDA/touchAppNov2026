import unittest,copy,socket
import numpy as np
from engine import fit_homography,project,SensorProcessor,TouchTracker,TuioOutput,scan_nodes
from studio import default_profile

class GeometryTests(unittest.TestCase):
 def test_nine_point_fit_and_degenerate_rejection(self):
  world=np.array([(x,y) for y in (100,850,1600) for x in (100,1500,2900)])
  true=np.array([[1/3000,.00001,.01],[.00001,-1/1700,1.],[.000001,.000001,1.]])
  target=project(true,world);fit=fit_homography(world,target)
  self.assertLess(np.linalg.norm(project(fit,world)-target,axis=1).max(),1e-8)
  with self.assertRaises(ValueError):fit_homography([[0,0],[1,0],[2,0],[3,0]],[[0,0],[1,0],[1,1],[0,1]])
 def test_background_and_unmapped_hand_detection(self):
  proc=SensorProcessor(copy.deepcopy(default_profile()['sensors'][0]));angle=np.arange(1440)/4
  base=np.column_stack([angle,np.full(1440,5000),np.full(1440,20)])
  proc.learn(3)
  for _ in range(3):proc.update(base)
  self.assertIsNotNone(proc.baseline)
  scan=base.copy();scan[(angle>=44.5)&(angle<=45.5),1]=np.sqrt(2)*1000
  proc.matrix=np.array([[100,0,500],[0,100,500],[0,0,1.]]) # Intentionally incorrect old guess
  proc.update(scan);self.assertEqual(len(proc.clusters),1)
  self.assertLess(np.linalg.norm(proc.clusters[0]['world']-[1000,1000]),2)
  proc.update(base);self.assertFalse(proc.clusters)
 def test_missing_background_rays_and_angular_jitter(self):
  config=copy.deepcopy(default_profile()['sensors'][0]);config['min_points']=1
  proc=SensorProcessor(config);proc.learn(3)
  proc.update(np.array([[0.,4000.,20.]]))
  for _ in range(2):proc.update(np.array([[0.,0.,0.]]))
  self.assertEqual(proc.baseline[0],4000,'Missing observations must not replace a known wall with infinity')
  proc.update(np.array([[.25,4000.,20.]]));self.assertFalse(proc.clusters,'Neighbouring bins must suppress wall jitter')
  proc.update(np.array([[.25,3800.,20.]]));self.assertEqual(len(proc.clusters),1)
 def test_fusion_ids_and_release(self):
  tracker=TouchTracker();a=np.array([.5,.5]);b=np.array([.501,.5])
  for _ in range(3):touches=tracker.update([(0,a),(1,b)],(1920,1080))
  self.assertEqual(len(touches),1);sid=next(iter(touches))
  touches=tracker.update([(1,b)],(1920,1080));self.assertIn(sid,touches)
  for _ in range(3):touches=tracker.update([],(1920,1080))
  self.assertFalse(touches)
  tracker=TouchTracker()
  for _ in range(3):touches=tracker.update([(0,a),(0,b)],(1920,1080))
  self.assertEqual(len(touches),2,'Do not merge two distinct fingers from the same lidar')
 def test_node_parser(self):
  angle=123.25;q=int(angle*64);packet=bytes([42,(q&127)<<1|1,q>>7,0x40,0x1f])
  nodes,remainder=scan_nodes(b'\x00'+packet+b'\x00\x01')
  self.assertEqual(len(nodes),1);self.assertEqual(nodes[0][1],angle);self.assertEqual(nodes[0][2],2000);self.assertEqual(remainder,b'\x00\x01')
 def test_tuio_udp(self):
  import sys
  from pathlib import Path
  sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
  from tuio import TuioState
  received=[];state=TuioState(lambda *args:received.append(args))
  with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
   s.bind(('127.0.0.1',0));s.settimeout(1);out=TuioOutput(port=s.getsockname()[1])
   out.send({7:(.25,.75)});data,sender=s.recvfrom(4096);state.feed(data,sender)
   self.assertEqual(len(received),1);self.assertAlmostEqual(received[0][2],.25)
   out.send({});data,sender=s.recvfrom(4096);state.feed(data,sender)
   self.assertFalse(next(iter(state.sources.values()))['active']);out.close()

if __name__=='__main__':unittest.main()
