"""TUIO 1.x /tuio/2Dcur receiver with source isolation and frame commits."""
import math, time
from pythonosc.osc_packet import OscPacket

class TuioState:
    def __init__(self, on_down, on_update=lambda *a: None):
        self.on_down, self.on_update = on_down, on_update
        self.sources = {}
        self.names = {}

    def feed(self, data, sender, now=None):
        now = time.monotonic() if now is None else now
        try:
            messages = OscPacket(data).messages
        except Exception:
            return
        source = self.names.get(sender, str(sender))
        for timed in messages:
            m = timed.message
            if m.address != '/tuio/2Dcur':
                continue
            a = list(m.params)
            if not a: continue
            if a[0] == 'source' and len(a) > 1:
                source = str(a[1]); self.names[sender] = source
                continue
            key = (sender[0], source)
            s = self.sources.setdefault(key, dict(active={}, pending={}, alive=None, seq=-1, seen=now))
            s['seen'] = now
            if a[0] == 'set' and len(a) >= 4:
                try:
                    sid, x, y = int(a[1]), float(a[2]), float(a[3])
                    if math.isfinite(x) and math.isfinite(y): s['pending'][sid] = (x, y)
                except (ValueError, TypeError): pass
            elif a[0] == 'alive':
                s['alive'] = set(a[1:])
            elif a[0] == 'fseq' and len(a) > 1:
                seq = int(a[1])
                # -1 denotes an unsequenced frame. Accept wrap from signed int max.
                fresh = seq == -1 or s['seq'] == -1 or seq > s['seq'] or (s['seq'] > 2147483000 and seq < 1000)
                if fresh:
                    active = s['active']
                    alive = s['alive'] if s['alive'] is not None else set(active) | set(s['pending'])
                    for sid, pos in s['pending'].items():
                        if sid in alive:
                            if sid not in active: self.on_down(source, sid, *pos)
                            active[sid] = pos
                    s['active'] = {i:p for i,p in active.items() if i in alive}
                    if seq != -1: s['seq'] = seq
                    self.on_update(key, s['active'])
                s['pending'] = {}; s['alive'] = None

    def expire(self, now=None):
        now = time.monotonic() if now is None else now
        for key in list(self.sources):
            if now - self.sources[key]['seen'] > 3:
                del self.sources[key]
                self.on_update(key, {})
