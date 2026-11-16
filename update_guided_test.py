from pathlib import Path
p=Path('lidar_touch/verify_studio.py');s=p.read_text();s=s.replace('steps=0;deadline=time.monotonic()+35','steps=0;wrong_since=None;wrong_checked=False;deadline=time.monotonic()+45');s=s.replace(' global steps',' global steps,wrong_since,wrong_checked');s=s.replace("  target=canvas.targets[canvas.index];world=project", """  target=canvas.targets[canvas.index]
  if canvas.phase=='verify' and not canvas.refine and not wrong_checked:
   assert len(canvas.targets)==12
   if wrong_since is None:wrong_since=time.monotonic()
   assert canvas.index==0, 'Wrong target must not advance validation'
   if time.monotonic()-wrong_since<1.3:target=np.array([.99,.99])
   else:wrong_checked=True
  world=project""");s=s.replace('center or precision validation; profile saved; UI renders','12 random target checks, rejected wrong touch, saved rotated mapping; UI renders');p.write_text(s)
