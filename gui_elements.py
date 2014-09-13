from PyQt4.QtCore import *
from PyQt4 import QtGui

class PlainComboField(QtGui.QComboBox):
    def __init__(self, parent=None,  label="", value=None,  choices=None):
        QtGui.QWidget.__init__( self, parent=parent)
        for t in choices:
            self.addItem(QString(t))
        if value!=None:
            self.setCurrentIndex(choices.index(value))
        self.combo=self

class LabeledComboField(QtGui.QWidget):
    def __init__(self, parent=None,  label="", value=None,  choices=None):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtGui.QLabel(label)
        self.layout.addWidget(self.label)
        self.combo=QtGui.QComboBox(parent=self)
        for t in choices:
            self.combo.addItem(QString(t))
        if value!=None:
            self.combo.setCurrentIndex(choices.index(value))
        self.layout.addWidget(self.combo)
        
        
class LabeledNumberField(QtGui.QWidget):
    def __init__(self, parent=None,  label="", min=None,  max=None,  value=0,  step=1.0):
        QtGui.QWidget.__init__( self, parent=parent)
        self.layout = QtGui.QHBoxLayout()
        self.setLayout(self.layout)
        self.label=QtGui.QLabel(label)
        self.layout.addWidget(self.label)
        self.number=QtGui.QDoubleSpinBox(parent=self)
        if min!=None:
            self.number.setMinimum(min)
        else:
            self.number.setMinimum(-10000000)
        if max!=None:
            self.number.setMaximum(max)
        else:
            self.number.setMaximum(10000000)
        self.number.setSingleStep(step);
        self.number.setValue(value)
        self.layout.addWidget(self.number)
