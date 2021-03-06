'''
MAVUE v0.1 (beta)
Graphical inspector for MAVLink enabled embedded systems.

Copyright (c) 2009-2014, Felix Schill
All rights reserved. 
Refer to the file LICENSE.TXT which should be included in all distributions of this project.
'''

import time
import traceback

KEY_SEPARATOR = ":"


def rgetattr(item, attribute):
    subItem = item
    attList = attribute.split('.')
    while len(attList) > 0:
        testsubItem = getattr(subItem, attList[0])
        subItem = testsubItem
        attList = attList[1:]
    return subItem


class RootNode(object):
    def __init__(self, name, parent=None, checked=False, content=None, key_attribute=None):
        self._name = name
        self._content = content
        self._children = dict()
        self._parent = parent
        self._checked = checked

        self._key_attribute = key_attribute
        self._subscribers = set()
        self._messageCounter = 0;  # continuous counter of incoming messages (incremented with each call of updateContent)

        if content != None and self._key_attribute != None:
            self._name = rgetattr(content, self._key_attribute)

        if parent is not None:
            parent.addChild(self)

    def addChild(self, child):
        self._children[child.name()] = child
    
    def getChildrenNames(self):
        return self._children.keys()

    def getMessageCounter(self):  # get message counter of root node
        if self._parent is not None:
            return self._parent.getMessageCounter()
        else:
            return self._messageCounter

    def getRootNode(self):  # get message counter of root node
        if self._parent is not None:
            return self._parent.getRootNode()
        else:
            return self

    def content(self):
        return self._content

    def updateContent(self, key_attribute_list, content):
        msgNode=None
        if len(key_attribute_list) == 0:
            return

        # check if we are at top level and increment message counter
        if self._parent is None:
            self._messageCounter += 1

        child_name = None
        try:
            child_name = rgetattr(content, key_attribute_list[0])
        except AttributeError:
            pass

        # test remaining keys to see if any are valid
        future_keys = 0
        for a in key_attribute_list:
            try:
                if rgetattr(content, a) != None:
                    future_keys += 1
            except AttributeError:
                pass
        # skip non-existent keys
        while future_keys >= 1 and child_name == None:
            key_attribute_list = key_attribute_list[1:]
            try:
                child_name = rgetattr(content, key_attribute_list[0])
            except AttributeError:
                pass
        if child_name == None:
            return

        if future_keys == 1:
            if not (child_name in self._children.keys()):
                if content._type == "PARAM_VALUE":
                    msgNode=ParamNode(name=child_name, parent=self, content=content, key_attribute=key_attribute_list[0])
                else:
                    msgNode=MsgNode(name=child_name, parent=self, content=content, key_attribute=key_attribute_list[0])
            self._children[child_name].updateContent(content=content)
            msgNode=self._children[child_name]

        else:
            if not (child_name in self._children.keys()):
                RootNode(name=child_name, parent=self, content=content, key_attribute=key_attribute_list[0])
            msgNode=self._children[child_name].updateContent(key_attribute_list=key_attribute_list[1:], content=content)

        return msgNode

    def insertChild(self, position, child):
        self._children[child.name()] = child
        return True

    def name(self):
        return self._name

    def getKey(self):
        return str(self._key_attribute) + '=' + str(self._name)

    def getFullKey(self):
        if self._parent != None:
            return str(self._parent.getFullKey() + KEY_SEPARATOR + self.getKey())
        else:
            return self._name

    def retrieveByKey(self, key):
        key_list = key
        if len(key_list) == 0:
            return None
        local_key = key_list[0].split('=')
        if (len(local_key) == 1 and local_key[0] == str(self._key_attribute)) or (
                    len(local_key) > 1 and local_key[0] == str(self._key_attribute) and local_key[1] == str(
                self._name)):
            if len(key_list) == 1:
                return self
            else:
                for c in self._children.values():
                    r = c.retrieveByKey(key_list[1:])
                    if r != None:
                        return r
        else:
            return None

    def checked(self):
        return self._checked

    def setChecked(self, state):
        None

    def child(self, row):
        return self._children[sorted(self._children.keys())[row]]

    def childCount(self):
        return len(self._children)

    def parent(self):
        return self._parent

    def row(self):
        if self._parent is not None:
            return sorted(self._parent._children.keys()).index(self.name())

    def columnCount(self, parent):
        return 2

    #def content(self):
    #    return self._content

    def isMessage(self):
        return False

    def displayContent(self):
        #return str(self._name)
        # return self._key_attribute
        return ""

    def displayName(self):
        if self._parent != None:
            return str(self._parent._name) + ':' + str(self._name)
        else:
            return str(self._name)
            # return self._key_attribute

    def notifyAllSubscribers(self):
        self.notifySubscribers()
        for c in self._children.values():
            c.notifyAllSubscribers()

    def notifySubscribers(self):
        for s in self._subscribers:
            try:
                s()
            except:
                print "subscriber error"
                traceback.print_exc()

    def subscribe(self, subscriber):
        self._subscribers.add(subscriber)
        print "subscribed"

    def unsubscribe(self, subscriber):
        self._subscribers.remove(subscriber)
        print "unsubscribed"

    def unsubscribeAllRecursive(self):
        self._subscribers = set()
        for c in self._children.values():
            c.unsubscribeAllRecursive()


class MsgNode(RootNode):
    def __init__(self, *args, **kwargs):
        RootNode.__init__(self, *args, **kwargs)

        self.trace = []
        self.max_trace_length = 100
        self.last_update = None
        self.update_period = 0

        if self._parent is not None:
            self._parent.addChild(self)

    def updateContent(self, content):
        self._content = content

        for valueName in content.get_fieldnames():
            value = getattr(content, valueName)
            if not (valueName in self._children.keys()):
                ValueNode(name=valueName, parent=self, content=value)
            self._children[valueName].updateContent(value)

        update_time = time.time()
        if self.last_update != None:
            if self.update_period == 0:
                self.update_period = (update_time - self.last_update)
            else:
                self.update_period = 0.7 * self.update_period + 0.3 * (update_time - self.last_update)
        self.last_update = update_time
        self.notifySubscribers()
        
    def isMessage(self):
        return True

    def get_srcSystem(self):
        return self._content._header.srcSystem

    def get_srcComponent(self):
        return self._content._header.srcComponent
    
    def get_msgType(self):
        return self._content._type

    def getMavlinkKey(self):
        return "(%i:%i) %s"%(self._content._header.srcSystem,  self._content._header.srcComponent,  self._name)

    def getValueByName(self, name):
        if name in self._children.keys():
            return self._children[name]
        else:
            return None

    def displayContent(self):
        if self.last_update != None and (time.time() - self.last_update) > min(1.5, 2.0 * self.update_period + 0.3):
            self.update_period = 0

        if self.update_period == 0:
            self._checked = False
            return "inactive"
        else:
            self._checked = True
            return "{:4.1f} Hz".format(1.0 / self.update_period)

    def setChecked(self, state):
        self.content().mavlinkReceiver.requestStream(self.content(), state)
        self._checked = state

    def editValue(self, new_value):
        self.content().mavlinkReceiver.requestStream(self.content(), True, new_value)


class ParamNode(MsgNode):
    def __init__(self, *args, **kwargs):
        MsgNode.__init__(self, *args, **kwargs)

    def displayContent(self):
        return self._children['param_value'].displayContent()

    def updateContent(self, content):
        MsgNode.updateContent(self, content)
        self._checked = False

    def setChecked(self, state):
        print "fetching ", self._children['param_index']._content
        self.content().mavlinkReceiver.master.param_fetch_one(self._children['param_id']._content)
        self._checked = state

    def editValue(self, new_value):
        print "change parameter", self._children['param_id'].content(), " to ", new_value
        # self.content().mavlinkReceiver.master.param_set_send(self._children['param_id'].content(),  new_value)
        for i in range(0, 3):
            self.content().mavlinkReceiver.master.mav.param_set_send(self.content().get_srcSystem(),
                                                                     self.content().get_srcComponent(),
                                                                     self._children['param_id'].content(), new_value, 9)


class ValueNode(RootNode):
    def __init__(self, *args, **kwargs):
        RootNode.__init__(self, *args, **kwargs)

        self._key_attribute = "fieldname"
        self.trace = []
        self.counterTrace = []
        self.max_trace_length = 1000000
        self.last_update = None
        self.update_period = 0

        if self._parent is not None:
            self._parent.addChild(self)

    def content(self):
        return self._content

    def findTraceIndex(self, counterValue):
        if counterValue < 0:
            if -counterValue >= len(self.counterTrace):
                return 0
            else:
                return int(counterValue)
        start = 0
        end = len(self.counterTrace)
        while end-start>1:
            middle = (start+end)/2
            if counterValue < self.counterTrace[middle]:
                end = middle
            else:
                start = middle
        return start

    def getTrace(self, range=[-100, 0],  only_1D=True):
        if only_1D and isinstance(self._content, list):
            if range[1]==0:
                return self._content
            else:
                ti=self.findTraceIndex(range[1])
                return self.trace[ti]
        else:
            if range[1]==0:
                return self.trace[self.findTraceIndex(range[0]):]
            else:
                return self.trace[max(0, self.findTraceIndex(range[0])):self.findTraceIndex(range[1])]

    def getCounterTrace(self, range=[-100, 0]):
        if range[1]==0:
            return self.counterTrace[self.findTraceIndex(range[0]):]
        else:
            return self.counterTrace[self.findTraceIndex(range[0]):self.findTraceIndex(range[1])]

    def updateContent(self, content):
        if isinstance(content, list):
            self.trace.append([x for x in content])
            #for i in range(0,len(content)):
            #    if not(i in self._children.keys()):
            #        ValueNode(name=i,   parent=self, content=content)
            #    self._children[i].updateContent(content[i])
        else:
            # keep traces of scalar values
            #if isinstance(self._content, int) or isinstance(self._content, float):
            self.trace.append(content)
        self.counterTrace.append(self.getMessageCounter())
        if len(self.trace) > self.max_trace_length:
            self.trace = self.trace[-self.max_trace_length:]
            self.counterTrace = self.counterTrace[-self.max_trace_length:]
        self._content = content
        self.notifySubscribers()
        return self


    def displayContent(self):
        if isinstance(self._content, str) or isinstance(self._content, int) or isinstance(self._content, float):
            return str(self._content)
        return "?"
        
    # pass subscribers upwards to message node, as values generally only update as a whole message
    # (no need to notify individually for each value - it could lead to multiple updates)
    def subscribe(self, subscriber):
        self._parent.subscribe(subscriber)

    def unsubscribe(self, subscriber):
        self._parent.unsubscribe(subscriber)

