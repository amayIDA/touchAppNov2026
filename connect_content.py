from pathlib import Path
p=Path('app.py');s=p.read_text(encoding='utf-8')
s=s.replace('from tuio import TuioState','from tuio import TuioState\nfrom content_model import load_content,draw_card,draw_chrome')
s=s.replace("        audio_config = config.get('audio', {})", "        self.content_path=resource('content.json')\n        self.editable=load_content(self.content_path)\n        self.content_stamp=self.content_path.stat().st_mtime_ns\n        self.last_content_check=0\n        audio_config = config.get('audio', {})")
s=s.replace('        now=time.monotonic()\n        for i in range(5):','''        now=time.monotonic()
        if now-self.last_content_check>.5:
            self.last_content_check=now
            try:
                stamp=self.content_path.stat().st_mtime_ns
                if stamp!=self.content_stamp:
                    updated=load_content(self.content_path)
                    self.editable=updated;self.content_stamp=stamp
                    logging.info('Applied admin content changes')
            except Exception as exc: logging.warning('Content reload: %s',exc)
        for i in range(5):''')
s=s.replace('        # Original PDF crops use the same 4920 x 2163 artwork coordinates as the video.','        draw_chrome(p,self.editable,self.arabic_font,self.frame)')
a=s.index('        pixmap=self.stats[index]');b=s.index('        # A restrained opening glint',a)
s=s[:a]+'''        cards=[c for c in self.editable['cards'] if c['kind']=='stat' and c['group']==index]
        for row,card in enumerate(cards):
            progress=ease((age-row*.14)/.65)
            if progress<=0: continue
            p.save();p.setOpacity(progress*opacity);p.translate(0,18*(1-progress))
            draw_card(p,card,self.arabic_font)
            p.restore()
'''+s[b:]
a=s.index('        p.setPen(QPen(QColor(85,206,241,85),1))',s.index('    def draw_invitation'));b=s.index('        p.restore()',a)
s=s[:a]+'''        for card in self.editable['cards']:
            if card['kind']=='invitation': draw_card(p,card,self.arabic_font)
'''+s[b:]
s=s.replace("            if self.frame is None: p.drawPixmap(QRectF(cx-133,485,266,50),self.buttons[i],QRectF(self.buttons[i].rect()))",'')
p.write_text(s,encoding='utf-8')
