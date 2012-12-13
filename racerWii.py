#!/usr/bin/env python2
'''
Created on Oct 12, 2012
@author: Matt Zimmerman
@email: mzimmerman@gmail.com

Using code based upon MythPyWii by benjie
'''

import socket, asynchat, asyncore, time, cwiid, logging, os, thread, subprocess, threading, math
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
        global runners, startTime, screen, homeCount
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
                if state["buttons"] == cwiid.BTN_HOME:
                    homeCount += 1
                    print "Pressed HOME " + str(homeCount) + " time(s)"
                    if homeCount >= 5:
                        writeRaceResults(runners)
                        pygame.quit()
                        exit()
                if state["buttons"] == cwiid.BTN_MINUS:
                    if (len(runners) > 0):
                        runners.pop()
                if state["buttons"] == cwiid.BTN_A:
                    if (startTime == 0):
                        print "Race is not started yet!"
                    else:
                        runners.append(timeDiff(startTime,time.time()))
                        print str(len(runners)) + " : " + runners[len(runners)-1]
                if state["buttons"] == cwiid.BTN_B:
                    if (startTime == 0):
                        startTime = time.time()
                        runners = []
                        print "Race started at " + str(startTime)
                    else:
                        writeRaceResults(runners)
                        print "Race is already started, wrote file out!"
                        
            self.laststate = state.copy() #NOTE TO SELF: REMEMBER .copy() !!!

    def __init__(self):
        self.wm = cwiid.Wiimote()
        # Wiimote calibration data (cache this)
        self.wii_calibration = self.wm.get_acc_cal(cwiid.EXT_NONE)
        self.wm.led = cwiid.LED1_ON | cwiid.LED4_ON
        self.wm.rpt_mode = sum(self.reportvals[a] for a in self.report if self.report[a])
        self.wm.enable(cwiid.FLAG_MESG_IFC | cwiid.FLAG_REPEAT_BTN)
        self.wm.mesg_callback = self.wmcb
        
def writeRaceResults(runners):
    try:
        resultHtml = "<html><body><table>\n"
        x = 1
        for result in runners:
            resultHtml += "<tr><td>"+str(x)+"</td><td>"+result+"</td></tr>\n"
            x += 1
        resultHtml += "</table></body></html>\n"
        f = open('raceResults.html','w')
        f.write(resultHtml)
        f.close()
    except Exception, e:
        print e


def closeWiimote():
    global wc , screen
    if wc is not None:
        if wc.wm is not None:
            wc.wm.close()
            wc.wm = None
        wc = None
        
def factorTime(begin, end):
    diff = end-begin
    hours = math.floor(diff / (60 * 60))
    diff -= hours * 60 * 60
    minutes = math.floor(diff / 60)
    diff -= minutes * 60
    seconds = diff % 60
    return hours, minutes, seconds
        
def clockDisplay(begin, end):
    hours, minutes, seconds = factorTime(begin,end)
    seconds = math.floor(seconds)
    return '{:02.0f}:{:02.0f}:{:02.0f}'.format(hours,minutes,seconds)

def timeDiff(begin, end):
    hours, minutes, seconds = factorTime(begin,end)
    return '{:02.0f}:{:02.0f}:{:05.2f}'.format(hours,minutes,seconds)

def findMaxFontSize(x,y,phrase,fontSize):
    while True:
        size = pygame.font.Font(None, fontSize).size(phrase)
        if size[0] > x or size[1] > y:
            fontSize -= 5
            continue
        break
    return fontSize, size[0], size[1]

def writeText(screen, phrase1, phrase2=None, startingFontSize=500):
    size = screen.get_size()
    background = pygame.Surface(size)
    background = background.convert()
    background.fill((10,10,10))
    fontSize1 , x, y = findMaxFontSize(size[0],size[1],phrase1,startingFontSize)
    font = pygame.font.Font(None, fontSize1)
    text = font.render(phrase1, True, (250,250,250))
    background.blit(text, (0,0))
    if phrase2 != None:
        fontSize2 , x, y = findMaxFontSize(size[0],size[1]-y,phrase2,startingFontSize)
        font = pygame.font.Font(None, fontSize2)
        text = font.render(phrase2, True, (250,250,250))
        background.blit(text, (0,size[1]-y))
    screen.blit(background,(0,0))
    pygame.display.flip()
    return fontSize1

def main(screen):
    global wc, startTime, runners, homeCount
    clock = pygame.time.Clock()
#    lock = threading.RLock()
    startTime = 0
    runners = []
    homeCount = 0
    wc = None
    fontSize = 500
    while True:
        if wc is None:
            try:
                if (startTime != 0):
                    writeText(screen,"WiiMote disconnected! Press 1&2 on the WiiMote",clockDisplay(startTime,time.time()))
                else:
                    writeText(screen,"Press 1&2 on the WiiMote","To quit, press the home button 5 times")
                wc = WiiController()
                wc.rumble()
                thread.start_new_thread(asyncore.loop,())
            except Exception, errMessage:
                print "closing WiiMote, " + str(errMessage)
                closeWiimote()
        
        elif startTime == 0:
                writeText(screen,"Press trigger to start the race!")
        else: # if startTime != 0:
            now = time.time()
            fontSize = writeText(screen,clockDisplay(startTime,now),"Overall #" + str(len(runners)+1),fontSize)
            if round(now,1) % 5 == 0:
                try:
                    wc.wm.request_status()
                except Exception, errMessage:
                    print "Wiimote connection lost"
                    closeWiimote()
        clock.tick(10)

pygame.init()
screen = pygame.display.set_mode((0,0),pygame.FULLSCREEN)
#screen = pygame.display.set_mode((800,600))
pygame.display.set_caption('Racer Wii')
pygame.mouse.set_visible(0)
main(screen)
