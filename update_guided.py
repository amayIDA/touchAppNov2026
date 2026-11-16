from pathlib import Path
p=Path('lidar_touch/studio.py');s=p.read_text(encoding='utf-8')
s=s.replace("else:uv=[(.5,.5)] if validation else [(.08,.08),(.92,.08),(.92,.92),(.08,.92)]", """else:
   if validation:
    # One unpredictable target in each of twelve screen regions.
    rng=np.random.default_rng();uv=[((col+rng.uniform(.2,.8))/4,(row+rng.uniform(.2,.8))/3) for row in range(3) for col in range(4)];rng.shuffle(uv)
   else:uv=[(.04,.04),(.96,.04),(.96,.96),(.04,.96)]""")
s=s.replace("self.world.append(median.tolist());self.armed=False", """if self.phase=='verify' and not self.refine:
    uv=project(proc.matrix,[median])[0]
    error=float(np.linalg.norm((uv-self.targets[self.index])*[self.width(),self.height()]))
    tolerance=max(18.,min(self.width(),self.height())*.025)
    if not np.isfinite(error) or error>tolerance:
     self.samples=[];self.anchor=None;self.progress=0;self.note=f'Touch the highlighted target — detected contact is {error:.0f}px away';return
   self.world.append(median.tolist());self.armed=False""")
s=s.replace("self.note='Now verify the center' if not self.refine else 'Independent accuracy checks'", "self.note='Orientation detected. Touch each of the 12 highlighted test points' if not self.refine else 'Independent accuracy checks'")
s=s.replace("passed=maximum<=self.owner.accuracy.value() if self.refine else fraction<.08", "passed=maximum<=self.owner.accuracy.value() if self.refine else maximum<=max(18.,min(self.width(),self.height())*.025)")
s=s.replace("f'Center check missed by {fraction*100:.1f}% of the screen.'", "f'Touch test missed by {maximum:.1f}px.'")
s=s.replace("'demo-four-corners-center'", "'four-corners-12-random-tests'")
s=s.replace("f'center error {fraction*100:.1f}% ({maximum:.1f}px)'", "f'12/12 targets passed, maximum error {maximum:.1f}px'")
s=s.replace("Test touches; precise 9-point refinement is available separately.", "Touch area ready. TUIO will be enabled.")
s=s.replace("   self.close()\n  except Exception", "   self.close()\n   QTimer.singleShot(0,lambda:self.owner.output.setChecked(True))\n  except Exception")
s=s.replace("'Demo calibration')+f' • {step}/{14 if self.refine else 5}'", "'Corners → 12 touch tests')+f' • {step}/{14 if self.refine else 16}'")
s=s.replace("  p.setFont(QFont('Segoe UI',13));p.drawText", "  if self.sensor is not None and self.phase=='fit' and not self.refine:\n   p.setFont(QFont('Segoe UI',16));p.drawText(QRectF(20,75,self.width()-40,50),Qt.AlignmentFlag.AlignCenter,'Touch '+['TOP LEFT','TOP RIGHT','BOTTOM RIGHT','BOTTOM LEFT'][min(self.index,3)]+' corner target')\n  p.setFont(QFont('Segoe UI',13));p.drawText")
s=s.replace('Touch four corners + center','Touch four corners + 12 test points').replace('five-target calibration from your demo','corner calibration to automatically determine screen orientation')
s=s.replace('Guided calibration: four corners + center','Start guided calibration: corners + 12 tests')
s=s.replace("b.addWidget(self.refine_button)", "self.refine_button.hide()")
s=s.replace('Record with the scan plane empty. Then run the same five-target flow as your demo: TL → TR → BR → BL → center. Hold one hand still until captured; fully remove it between targets. Orange raw hand detections work before any mapping. Refine precision later if needed.', 'Record the empty background, then start guided calibration for each sensor. Touch TL → TR → BR → BL: orientation and rotation are calculated automatically. Then touch 12 random targets within the screen. Lift between targets. After all pass, TUIO touch input is enabled for the exhibit.')
s=s.replace('Demo alignment ready (optional precision refinement available)','Touch area verified — 12 targets passed')
p.write_text(s,encoding='utf-8')
