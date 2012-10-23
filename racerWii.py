#!/usr/bin/env python2
'''
Created on Oct 12, 2012
w00t!
@author: Matt Zimmerman
@email: mzimmerman@gmail.com

Using code based upon MythPyWii by benjie
'''

import socket, asynchat, asyncore, time, cwiid, logging, os, thread, subprocess, curses, threading
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
		global runnerCount , startTime, screen, lock
		for message in messages:
			if message[0] == cwiid.MESG_BTN:
				state["buttons"] = message[1]
			#elif message[0] == cwiid.MESG_STATUS:
			#	print "\nStatus: ", message[1]
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
			#print "B: %d/%d %d		  \r" % (state["buttons"],self.maxButtons,self.ms.ok()),
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
#				if state["buttons"] == cwiid.BTN_HOME:
				if state["buttons"] == cwiid.BTN_A:
						if (startTime == 0):
								writeTop(screen,lock,"Race is not started yet, press the trigger!")
						else:
								curses.flash()
								runnerCount = runnerCount + 1
								with lock:
										writeTop(screen,lock,str(runnerCount) + " - " + timeDiff(startTime, time.time()))
										screen.insertln()
								screen.refresh()
				if state["buttons"] == cwiid.BTN_B:
						curses.flash()
						if (startTime == 0):
								startTime = time.time()
								screen.erase()
								writeTop(screen,lock,"Race is started!")
						else:
								writeTop(screen,lock,"Race is already started!")
						screen.refresh()
 #			   if state["buttons"] == cwiid.BTN_MINUS:
 #			   if state["buttons"] == cwiid.BTN_UP:
 #			   if state["buttons"] == cwiid.BTN_DOWN:
 #			   if state["buttons"] == cwiid.BTN_LEFT:
 #			   if state["buttons"] == cwiid.BTN_RIGHT:
 #			   if state["buttons"] == cwiid.BTN_PLUS:
 #			   if state["buttons"] == cwiid.BTN_1:
 #			   if state["buttons"] == cwiid.BTN_2:
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

def timeDiff(begin, end):
		diff = time.gmtime(end-begin)
		return '{!s}.{:2.0f}'.format(time.strftime("%H:%M:%S",diff),((end - begin)*100%100))

def writeTop(screen, lock, phrase):
		with lock:
				screen.move(0,0)
				screen.addstr(0,0,phrase)
				screen.clrtoeol()
				screen.move(0,0)
		screen.refresh()

def main(createdScreen):
	global wc, startTime, runnerCount, screen, lock
	lock = threading.RLock()
	startTime = 0
	runnerCount = 0
	screen = createdScreen
	screen.erase()
	curses.curs_set(0)
	wc = None
	while True:
		while (wc is None):
			try:
				if (startTime == 0):
						screen.clear()
						writeTop(screen,lock,"Press 1&2 on the Wiimote")
				else:
						writeTop(screen,lock,"Time :" + timeDiff(startTime,time.time()) + " - Wiimote disconnected, press 1&2 on the Wiimote")
				wc = WiiController()
				wc.rumble()
				writeTop(screen,lock,"WiiMote Conected, press the trigger to start the race")
				thread.start_new_thread(asyncore.loop,())
			except Exception, errMessage:
				writeTop(screen,lock,"Error - " + str(errMessage))
				closeWiimote()
		if (startTime != 0):
				writeTop(screen,lock,"Time - " + timeDiff(startTime,time.time()))
		time.sleep(1)

# start the application with a curses wrapper
curses.wrapper(main)
