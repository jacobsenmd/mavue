'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.

mavue.py
This is the main file. 

Usage: mavue.py [options]

Options:
  -h, --help            show this help message and exit
  --baudrate=BAUDRATE   master port baud rate
  --device=DEVICE       serial device
  --dialect=DIALECT     Mavlink dialect
  --logfile=LOGFILE_RAW
                        output log file
  --notimestamps=NOTIMESTAMPS
                        logfile format
  --source-system=SOURCE_SYSTEM
                        MAVLink source system for this GCS

After startup, the message inspector window will show a tree of all received messages. 
To plot values, click "add plot" and drag and drop message contents onto the plot window, or onto the "x" or "y" button of an existing plot item.
Message streams can be activated/deactivated by clicking the checkbox in front of them. 
Double-clicking the frequency allows to edit the message stream frequency (only supported on the MAVRIC autopilot).
MAVlink parameters can be edited by double-clicking on the value behind the parameter message. 
'''

#!/usr/bin/python

#from PyQt4 import QtCore, QtGui
from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

import sys
import mavlink_receiver
import threading
import pickle
import time

import plugins as plugins
import gui_elements

colors=[[1.0, 0.0, 0.0],  [0.0,  1.0,  0.0],  [0.0,  0.0,  1.0],  [1.0, 1.0, 0.0],  [0.0,  1.0,  1.0],  [1.0,  0.0,  1.0]]
        

from plot_widget import *
from message_viewer import *


# define sorting order of MAVlink attributes (this controls the subtree structure of the message viewer).
key_attribute_list=('_header.srcSystem',  '_header.srcComponent', '_type',  'name',  'param_id', 'stream_id')
    
class Update_Thread():
    def __init__(self, treeViewInstance):
        self._treeViewInstance= treeViewInstance
        self.mavlinkReceiver=mavlink_receiver.MAVlinkReceiver()
        self.running=True      
        self.lastTreeUpdate=time.time()
        self.treeUpdateFrequency=1.0
        self.t = QtCore.QTimer()
        self.t.timeout.connect(self.update)
        self.t.start(2)
        self.plugin_manager=plugins.plugin_manager(self.plugin_callback)

    def plugin_callback(self,  msg):
        if msg!=None:
            self._treeViewInstance.rootNode.updateContent(msg)
        
    def update(self):
        try:
            msg_key, msg=self.mavlinkReceiver.wait_message()
        except:
            print "error in wait_message"

        if msg_key=='':
          return
       #print "updating tree: ",msg_key
        msgNode=self._treeViewInstance.rootNode.updateContent(key_attribute_list ,  content=msg)

        #call plugins
        self.plugin_manager.run_plugins(msg)

              
       #self._treeViewInstance.treeView.update()

        if time.time()>self.lastTreeUpdate+1/(self.treeUpdateFrequency):
            self._treeViewInstance.model.layoutChanged.emit()
            self.lastTreeUpdate=time.time()

    def reloadPlugins(self):
        global plugins
        reload(plugins)
        import plugins
        self.plugin_manager=plugins.plugin_manager(self.plugin_callback)

    def stop(self):
        self.t.stop()
        self.mavlinkReceiver.close()

    def reopen(self, device):
        self.stop()
        self.mavlinkReceiver.reopenDevice(device)
        self.t.start()

class MainWindow(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)
        
        self.messageTreeView=MessageTreeView()
        self.updater=Update_Thread(self.messageTreeView)

        self.serialPorts= self.updater.mavlinkReceiver.scanForSerials()
        print self.serialPorts
        self.setWindowTitle('MavLink viewer')
        self.resize(500,900)
        cw = QtGui.QWidget()
        self.setCentralWidget(cw)
        self.l = QtGui.QGridLayout()
        self.setCentralWidget(cw)
        cw.setLayout(self.l)
        
        self.menubar=QtGui.QWidget()
        self.menubarLayout=QtGui.QHBoxLayout()
        self.menubar.setLayout(self.menubarLayout)
        
        self.widgetbar=QtGui.QWidget()
        self.widgetbarLayout=QtGui.QHBoxLayout()
        self.widgetbar.setLayout(self.widgetbarLayout)
        
        self.serialSelect=gui_elements.PlainComboField(parent=self,  label='Serial port',  choices=['udp:localhost:14550']+[s.device for s in self.serialPorts],  value=self.updater.mavlinkReceiver.opts.device)
        self.connect(self.serialSelect,  QtCore.SIGNAL("currentIndexChanged(const QString&)"),  self.openConnection)
        
        self.menubarLayout.addWidget(self.serialSelect)
        self.refreshButton=QtGui.QPushButton("refresh streams")
        self.menubarLayout.addWidget(self.refreshButton)
        self.connect(self.refreshButton,  QtCore.SIGNAL("clicked()"),  self.updater.mavlinkReceiver.requestAllStreams)
        
        self.reloadPluginsButton=QtGui.QPushButton("reload plugins")
        self.menubarLayout.addWidget(self.reloadPluginsButton)
        self.connect(self.reloadPluginsButton,  QtCore.SIGNAL("clicked()"),  self.updater.reloadPlugins)
        
        self.l.addWidget(self.menubar, 0, 0)
        self.l.addWidget(self.messageTreeView.treeView,  1,  0)  
        self.l.addWidget(self.widgetbar)
        
        self.addButton=QtGui.QPushButton("add plot")
        self.connect(self.addButton,  QtCore.SIGNAL("clicked()"),  self.addPlot)
        
        self.widgetbarLayout.addWidget(self.addButton)

        self.addParamButton=QtGui.QPushButton("add param-slider")
        self.connect(self.addParamButton,  QtCore.SIGNAL("clicked()"),  self.addParamSlider)        
        self.widgetbarLayout.addWidget(self.addParamButton)

        
        #self.addPlot()
        #self.addPlot()
        
        self.show()
        
    def addPlot(self):
        pw1 = DropPlot() 
        #self.l.addWidget(pw1,  0,  1)
        dock1=DockPlot(title="plot",  parent=self,  widget=pw1)
        #self.addDockWidget(QtCore.Qt.NoDockWidgetArea,  dock1)
        dock1.show()

    def addParamSlider(self):
        
        #self.l.addWidget(pw1,  0,  1)
        slider=ParamSlider(title="slider",  parent=self)
        slider.show()


    def openConnection(self,  index):
        try:
            self.updater.stop
            print "closed previous connection"
        except:
            print "no connection to close."

        print "opening connection"
        print index
        self.updater.mavlinkReceiver.reopenDevice(str(index))


    def closeEvent(self,  event):
        mw.updater.t.stop()
        mw.messageTreeView.close()

        try:
            self.updater.mavlinkReceiver.master.close()
            print "closed connection"
        except:
            print "no connection to close."

        self.deleteLater()
        sys.exit(0)

    
if __name__ == '__main__':
    app = QtGui.QApplication(sys.argv)
    print "creating main window"
    mw = MainWindow()
    print "starting app"
    app.exec_()
    print "shutting down"
    mw.updater.t.stop()
    print "updater stopped"
    mw.messageTreeView.close()
    print "tree closed"
