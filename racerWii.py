#!/usr/bin/env python2
'''
Created on Oct 12, 2012
w00t!
@author: Matt Zimmerman
@email: mzimmerman@gmail.com

Using code based upon MythPyWii by benjie
'''

import socket, asynchat, asyncore, time, cwiid, logging, os, thread, subprocess, threading
import pygame
from pygame.locals import *
from math import atan, cos

#logging.basicConfig(filename="/dev/stdout", level=logging.DEBUG)

logger = logging.getLogger("wiiRacer")
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

class WiiController(object):
    #Initialize variables
    wm = None
    reportvals = {"button":cwiid.RPT_BTN, "ext":cwiid.RPT_EXT,  "status":cwiid.RPT_STATUS}
    report={"button":True}
    state = {}
    lasttime = 0.0
    laststate = {}
    responsiveness = 0.15
    firstPress = True
    firstPressDelay = 0.5
    maxButtons = 0
    
    def rumble(self):
        self.wm.rumble=1
        time.sleep(.2)
        self.wm.rumble=0
    
    def wii_rel(self, v, axis):
        return float(v - self.wii_calibration[0][axis]) / (
        self.wii_calibration[1][axis] - self.wii_calibration[0][axis])

    def wmcb(self, messages,timeout="0"):
        state = self.state
        global runners, startTime, screen, lock
        for message in messages:
            if message[0] == cwiid.MESG_BTN:
                state["buttons"] = message[1]
            #elif message[0] == cwiid.MESG_STATUS:
            #    print "\nStatus: ", message[1]
            elif message[0] == cwiid.MESG_ERROR:
                if message[1] == cwiid.ERROR_DISCONNECT:
                    closeWiimote()
                    continue
                else:
                    writeTop(screen,lock,"ERROR: ", message[1])
            elif message[0] == cwiid.MESG_ACC:
                state["acc"] = message[1]
            else:
                writeTop(screen,lock,"Unknown message!" + message)
            laststate = self.laststate
            #print "B: %d/%d %d          \r" % (state["buttons"],self.maxButtons,self.ms.ok()),
            #sys.stdout.flush()
            if ('buttons' in laststate) and (laststate['buttons'] <> state['buttons']):
                if state['buttons'] == 0:
                    self.maxButtons = 0
                elif state['buttons'] < self.maxButtons:
                    continue
                else:
                    self.maxButtons = state['buttons']
                self.lasttime = 0
                self.firstPress = True
            if (self.wm is not None) and (state["buttons"] > 0) and (time.time() > self.lasttime+self.responsiveness):
                self.lasttime = time.time()
                wasFirstPress = False
                if self.firstPress:
                    wasFirstPress = True
                    self.lasttime = self.lasttime + self.firstPressDelay
                    self.firstPress = False
                # Stuff that doesn't need roll/etc calculations
#                if state["buttons"] == cwiid.BTN_HOME:
                if state["buttons"] == cwiid.BTN_A:
                        if (startTime == 0):
                            writeTop(screen,lock,"Race is not started yet, press the trigger!")
                        else:
                            curses.flash()
                            runners.append(timeDiff(startTime,time.time()))
                            with lock:
                                writeTop(screen,lock,str(len(runners)) + " - " + timeDiff(startTime, time.time()))
                                screen.insertln()
                            screen.refresh()
                if state["buttons"] == cwiid.BTN_B:
                        curses.flash()
                        if (startTime == 0):
                            startTime = time.time()
                            runners = []
                            screen.erase()
                            writeTop(screen,lock,"Race is started!")
                        else:
                            writeTop(screen,lock,"Race is already started!")
                        screen.refresh()
            self.laststate = state.copy() #NOTE TO SELF: REMEMBER .copy() !!!

    def __init__(self):
        self.wm = cwiid.Wiimote()
        # Wiimote calibration data (cache this)
        self.wii_calibration = self.wm.get_acc_cal(cwiid.EXT_NONE)
        self.wm.led = cwiid.LED1_ON | cwiid.LED4_ON
        self.wm.rpt_mode = sum(self.reportvals[a] for a in self.report if self.report[a])
        self.wm.enable(cwiid.FLAG_MESG_IFC | cwiid.FLAG_REPEAT_BTN)
        self.wm.mesg_callback = self.wmcb
        
def closeWiimote():
    global wc , screen
    if wc is not None:
        if wc.wm is not None:
            wc.wm.close()
            wc.wm = None
        wc = None
        
def clockDisplay(begin, end):
    diff = time.gmtime(end-begin)
    return '{!s}'.format(time.strftime("%H:%M:%S",diff))

def timeDiff(begin, end):
    diff = time.gmtime(end-begin)
    return '{!s}.{:2.0f}'.format(time.strftime("%H:%M:%S",diff),((end - begin)*100%100))

def writeText(screen, phrase, fontSize=500):
    size = screen.get_size()
    background = pygame.Surface(size)
    background = background.convert()
    background.fill((250, 250, 250))
    font = pygame.font.Font(None, fontSize)
    while True:
        newSize = font.size(phrase)
        if newSize[0] > size[0] or newSize[1] > size[1]:
            fontSize -= 5
            font = pygame.font.Font(None, fontSize)
            print "trying font size " + str(fontSize)
        else:
            break
    text = font.render(phrase, True, (10, 10, 10), (250,250,250))
#    textpos = text.get_rect(centerx=background.get_width()/2)
    background.blit(text, (0,0))
    screen.blit(background,(0,0))
    pygame.display.flip()
    return fontSize

def main(screen):
    global wc, startTime, runners
    clock = pygame.time.Clock()
#    lock = threading.RLock()
    startTime = 0
    runners = []
    wc = None
    fontSize = 500
    while True:
        while (wc is None):
            try:
                if (startTime == 0):
                    writeText(screen,"Press 1&2 on the WiiMote")
                    time.sleep(2)
                    writeText(screen,"Press trigger to start the race!")
                    time.sleep(2)
                    startTime = time.time()
                else:
                    fontSize = writeText(screen,clockDisplay(startTime,time.time()),fontSize)
#                wc = WiiController()
#                wc.rumble()
                thread.start_new_thread(asyncore.loop,())
            except Exception, errMessage:
#                writeTop(screen,lock,"Error - " + str(errMessage))
                print "closing WiiMote, " + str(errMessage)
                closeWiimote()
#        if (startTime != 0):
#                writeTop(screen,lock,"Time - " + timeDiff(startTime,time.time()))
            clock.tick(5)
pygame.init()
screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN)
pygame.display.set_caption('Racer Wii')
#pygame.mouse.set_visible(0)
main(screen)