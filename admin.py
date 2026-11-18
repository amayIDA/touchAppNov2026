"""Visual text editor for the TouchScreen exhibit."""
import sys,copy,shutil
from pathlib import Path
from PySide6.QtCore import Qt,QRectF,Signal
from PySide6.QtGui import QPainter,QColor,QImage,QFontDatabase,QFont,QPen,QKeySequence,QShortcut
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QHBoxLayout,QVBoxLayout,QLabel,QPushButton,QComboBox,QTextEdit,QSpinBox,QCheckBox,QFileDialog,QMessageBox,QSplitter,QScrollArea)
from content_model import load_content,save_content,draw_card,draw_chrome,fitted_font,register_fonts
ROOT=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
BUNDLE=Path(getattr(sys,'_MEIPASS',ROOT))
def asset(name): return (ROOT/name) if (ROOT/name).exists() else BUNDLE/name

class Preview(QWidget):
    selected=Signal(int)
    field_selected=Signal(int)
    def __init__(self,owner):
        super().__init__();self.owner=owner;self.setMinimumSize(640,400)
        self.bg=QImage(str(asset('assets/admin-background.jpg')))
    def viewport(self):
        scale=min(self.width()/1600,self.height()/696)
        return QRectF((self.width()-1600*scale)/2,(self.height()-696*scale)/2,1600*scale,696*scale)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(),QColor('#060f24'));r=self.viewport();p.translate(r.topLeft());p.scale(r.width()/1600,r.height()/696)
        p.drawImage(QRectF(0,0,1600,696),self.bg)
        draw_chrome(p,self.owner.data,self.owner.arabic,self.bg)
        for i,c in enumerate(self.owner.data['cards']):
            visible=c['kind']!='invitation' if self.owner.view.currentIndex()==0 else c['kind']!='stat'
            if not visible: continue
            if c['kind'] in ('stat','invitation'):draw_card(p,c,self.owner.arabic)
            if i==self.owner.current:
                p.setBrush(Qt.BrushStyle.NoBrush);p.setPen(QPen(QColor('#ffe08b'),3));p.drawRoundedRect(QRectF(*c['rect']).adjusted(-3,-3,3,3),18,18)
        p.end()
    def mousePressEvent(self,e):
        r=self.viewport();pos=e.position();x=(pos.x()-r.x())/r.width()*1600;y=(pos.y()-r.y())/r.height()*696
        for i in reversed(range(len(self.owner.data['cards']))):
            c=self.owner.data['cards'][i]
            visible=c['kind']!='invitation' if self.owner.view.currentIndex()==0 else c['kind']!='stat'
            if visible and QRectF(*c['rect']).contains(x,y):
                self.selected.emit(i)
                for index,field in enumerate(c['fields']):
                    if QRectF(*field['rect']).contains(x-c['rect'][0],y-c['rect'][1]):
                        self.field_selected.emit(index);break
                break

class Admin(QMainWindow):
    def __init__(self,path=None):
        super().__init__();self.setWindowTitle('TouchScreen Admin — Text & Typography');self.resize(1500,900)
        candidate=ROOT.parent/'TouchScreen'/'content.json'
        self.path=Path(path) if path else (candidate if candidate.exists() else ROOT/'content.json')
        self.data=load_content(self.path);self.saved=copy.deepcopy(self.data);self.current=0;self.loading=False;self.dirty=False
        self.arabic=register_fonts(asset)
        shell=QWidget();self.setCentralWidget(shell);layout=QVBoxLayout(shell)
        top=QHBoxLayout();title=QLabel('TouchScreen Studio');title.setStyleSheet('font-size:24px;font-weight:700;');top.addWidget(title);top.addStretch()
        self.view=QComboBox();self.view.addItems(['All statistic cards','Standby']);top.addWidget(self.view)
        self.heading_button=QPushButton('Edit heading');top.addWidget(self.heading_button)
        self.open_button=QPushButton('Open content file…');top.addWidget(self.open_button)
        self.save_button=QPushButton('Save to exhibit');self.save_button.setStyleSheet('background:#137ea3;font-weight:700;padding:12px;');top.addWidget(self.save_button);layout.addLayout(top)
        self.path_label=QLabel(str(self.path));self.path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse);layout.addWidget(self.path_label)
        split=QSplitter();layout.addWidget(split,1)
        left=QWidget();ll=QVBoxLayout(left);ll.setContentsMargins(0,0,0,0)
        ll.addWidget(QLabel('Click a heading line, card or label to edit it. Use Edit heading for title and subtitle fields.'))
        self.preview=Preview(self);ll.addWidget(self.preview,1);split.addWidget(left)
        panel=QWidget();panel.setMinimumWidth(340);pl=QVBoxLayout(panel)
        pl.addWidget(QLabel('SELECTED CARD'));self.card_select=QComboBox();self.card_select.addItems([c['label'] for c in self.data['cards']]);pl.addWidget(self.card_select)
        pl.addWidget(QLabel('Text field'));self.field_select=QComboBox();pl.addWidget(self.field_select)
        self.editor=QTextEdit();self.editor.setMinimumHeight(150);pl.addWidget(self.editor)
        pl.addWidget(QLabel('Font size (design pixels)'));self.size=QSpinBox();self.size.setRange(6,120);pl.addWidget(self.size)
        self.bold=QCheckBox('Bold');self.bold.hide();self.weight=QComboBox();self.weight.addItems(['Black','ExtraBold','Plain']);pl.addWidget(QLabel('Bahij font weight'));pl.addWidget(self.weight)
        pl.addWidget(QLabel('Text color'));self.color=QComboBox();self.color.addItem('White','#ffffff');self.color.addItem('Cyan','#c9f1ff');self.color.addItem('Orange','#ff941e');pl.addWidget(self.color)
        self.fit_label=QLabel();self.fit_label.setWordWrap(True);pl.addWidget(self.fit_label)
        self.revert=QPushButton('Revert selected card to last save');pl.addWidget(self.revert)
        pl.addStretch();help=QLabel('Edits preview immediately here. Save applies changes to the running exhibit within one second. Text automatically fits inside its card when needed. Ctrl+S saves.');help.setWordWrap(True);pl.addWidget(help)
        split.addWidget(panel);split.setSizes([1090,380]);self.status=QLabel('Ready — select a card to begin');layout.addWidget(self.status)
        self.setStyleSheet('QWidget{background:#101e31;color:#e5f3ff;font-family:Bahij TheSansArabic;font-size:14px;} QTextEdit,QComboBox,QSpinBox{background:#1c3048;border:1px solid #38526b;border-radius:5px;padding:7px;} QPushButton{background:#253e57;border:1px solid #38526b;border-radius:6px;padding:9px;} QPushButton:hover{background:#315a73;} QSplitter::handle{background:#32455c;}')
        self.preview.selected.connect(self.choose_card);self.card_select.currentIndexChanged.connect(self.choose_card)
        self.preview.field_selected.connect(self.field_select.setCurrentIndex)
        self.heading_button.clicked.connect(self.select_heading)
        self.field_select.currentIndexChanged.connect(self.load_field)
        self.editor.textChanged.connect(self.edit_field);self.size.valueChanged.connect(self.edit_field);self.weight.currentTextChanged.connect(self.edit_field);self.color.currentIndexChanged.connect(self.edit_field)
        self.save_button.clicked.connect(self.save);self.open_button.clicked.connect(self.open_file);self.revert.clicked.connect(self.revert_card);self.view.currentIndexChanged.connect(lambda:self.preview.update())
        QShortcut(QKeySequence.StandardKey.Save,self,activated=self.save)
        self.choose_card(0)
    def select_heading(self):
        index=next((i for i,c in enumerate(self.data['cards']) if c['kind']=='header'),None)
        if index is not None:
            self.choose_card(index)
            self.status.setText('Heading selected — choose Arabic/English heading or subtitle, then Save to exhibit.')
    def choose_card(self,index):
        if index<0:return
        self.loading=True;self.current=index;self.card_select.setCurrentIndex(index)
        self.field_select.clear();self.field_select.addItems([f['label'] for f in self.data['cards'][index]['fields']]);self.field_select.setCurrentIndex(0)
        self.loading=False
        kind=self.data['cards'][index]['kind']
        if kind=='invitation':self.view.setCurrentIndex(1)
        elif kind=='stat':self.view.setCurrentIndex(0)
        self.load_field(0);self.preview.update()
    def load_field(self,index):
        if self.loading or index<0:return
        self.loading=True;f=self.data['cards'][self.current]['fields'][index]
        self.editor.setPlainText(f['text']);self.editor.setLayoutDirection(Qt.LayoutDirection.RightToLeft if f.get('lang')=='ar' else Qt.LayoutDirection.LeftToRight)
        font=QFont(self.arabic if f.get('lang')=='ar' else 'Bahij TheSansArabic');font.setPointSize(16);self.editor.setFont(font)
        self.size.setValue(round(f['size']));self.bold.setChecked(f.get('bold',True));self.weight.setCurrentText(f.get('weight','ExtraBold'))
        color_index=self.color.findData(f['color'])
        if color_index<0:self.color.addItem(f['color'],f['color']);color_index=self.color.count()-1
        self.color.setCurrentIndex(color_index);self.loading=False;self.update_fit()
    def edit_field(self,*args):
        if self.loading:return
        index=self.field_select.currentIndex()
        if index<0:return
        f=self.data['cards'][self.current]['fields'][index]
        f.update(text=self.editor.toPlainText(),size=self.size.value(),bold=self.weight.currentText()!='Plain',weight=self.weight.currentText(),color=self.color.currentData())
        self.dirty=True;self.status.setText('Unsaved changes — preview updated. Save to apply to exhibit.');self.update_fit();self.preview.update()
    def update_fit(self):
        f=self.data['cards'][self.current]['fields'][self.field_select.currentIndex()]
        actual=fitted_font(f,self.arabic).pixelSize()
        self.fit_label.setText(f'Requested: {f["size"]} px • Displayed: {actual} px'+ (' — reduced to fit. Shorten the text to use the full requested size.' if actual<f['size'] else ' — fits inside the card.'))
    def save(self):
        try:
            if self.path.exists():shutil.copy2(self.path,self.path.with_suffix('.json.bak'))
            save_content(self.path,self.data);self.saved=copy.deepcopy(self.data);self.dirty=False
            self.status.setText('Saved — the exhibit applies this file automatically within one second.')
        except Exception as exc:QMessageBox.critical(self,'Unable to save',str(exc))
    def revert_card(self):
        self.data['cards'][self.current]=copy.deepcopy(self.saved['cards'][self.current]);self.dirty=True;self.choose_card(self.current);self.status.setText('Selected card reverted. Save to apply.')
    def confirm_discard(self):
        if not self.dirty:return True
        return QMessageBox.question(self,'Unsaved edits','Discard unsaved edits?',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)==QMessageBox.StandardButton.Discard
    def open_file(self):
        if not self.confirm_discard():return
        name,_=QFileDialog.getOpenFileName(self,'Open exhibit content',str(self.path),'Content JSON (*.json)')
        if not name:return
        try:
            data=load_content(name);self.data=data;self.saved=copy.deepcopy(data);self.path=Path(name);self.dirty=False
            self.path_label.setText(str(self.path));self.loading=True;self.card_select.clear();self.card_select.addItems([c['label'] for c in data['cards']]);self.loading=False;self.choose_card(0)
        except Exception as exc:QMessageBox.critical(self,'Unable to open',str(exc))
    def closeEvent(self,e):
        if self.confirm_discard():e.accept()
        else:e.ignore()

if __name__=='__main__':
    app=QApplication(sys.argv)
    try:window=Admin(sys.argv[1] if len(sys.argv)>1 else None)
    except Exception as exc:QMessageBox.critical(None,'Unable to load exhibit content',str(exc));sys.exit(1)
    window.show();sys.exit(app.exec())
