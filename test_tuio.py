import unittest
from pythonosc.osc_bundle_builder import OscBundleBuilder, IMMEDIATELY
from pythonosc.osc_message_builder import OscMessageBuilder
from tuio import TuioState

def packet(*messages):
    b=OscBundleBuilder(IMMEDIATELY)
    for args in messages:
        m=OscMessageBuilder(address='/tuio/2Dcur')
        for a in args: m.add_arg(a)
        b.add_content(m.build())
    return b.build().dgram

class ProtocolTests(unittest.TestCase):
    def test_lifetime_sequence_and_two_sources(self):
        hits=[]; state=TuioState(lambda *a:hits.append(a))
        def send(source,seq,alive,sets=()):
            state.feed(packet(('source',source),('alive',*alive),*sets,('fseq',seq)),('127.0.0.1',123),now=0)
        send('lidar-a',1,[1],[('set',1,.2,.65,0.,0.,0.)])
        send('lidar-a',2,[1],[('set',1,.3,.65,0.,0.,0.)])
        self.assertEqual(len(hits),1)
        send('lidar-b',1,[1],[('set',1,.7,.65,0.,0.,0.)])
        self.assertEqual(len(hits),2)
        send('lidar-a',1,[2],[('set',2,.1,.1,0.,0.,0.)])
        self.assertEqual(len(hits),2)
        send('lidar-a',3,[])
        send('lidar-a',4,[1],[('set',1,.2,.65,0.,0.,0.)])
        self.assertEqual(len(hits),3)
        state.expire(now=4); self.assertFalse(state.sources)
    def test_invalid_packet_and_nonfinite(self):
        hits=[]; state=TuioState(lambda *a:hits.append(a))
        state.feed(b'garbage',('local',1))
        state.feed(packet(('alive',1),('set',1,float('nan'),.2),('fseq',1)),('local',1))
        self.assertEqual(hits,[])

if __name__=='__main__': unittest.main()
