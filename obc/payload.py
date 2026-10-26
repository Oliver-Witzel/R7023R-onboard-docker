from common.common import *


class Payload:
	def __init__(self):
		self.mode = PL_MODES[0]
		self.power= False
		self.t0 = time.monotonic(); self.time_set = False; self.obt_base = 0; self.obt_mono = 0
		
	def turn_on(self):
		if self.mode == PL_MODES[0]:
			self.power = True
			self.mode = PL_MODES[1]

	def turn_off(self):
		self.power=False
		self.mode = PL_MODES[0]

	def start_imaging(self):
		if self.mode != PL_MODES[1]:
			return False
		self.mode = PL_MODES[2]
		return True

	def stop_imaging(self):
		#add log to file and or generate noise image with timestamp
		if self.mode == PL_MODES[2]:
			self.mode = PL_MODES[1]
	def sync_time(self,s):
		self.obt_base, self.obt_mono, self.time_set = s, time.monotonic(), True
		return True
	def now(self):
		if self.time_set:
			return (self.obt_base + int(time.monotonic() - self.obt_mono))
		return int(time.monotonic() - self.t0)
    
	def set_mode(self, mode):
		if mode not in PL_MODES:
			return False
		if mode == PL_MODES[0]:
			self.turn_off()
		elif mode == PL_MODES[1]:
			if self.mode == PL_MODES[0]:
				self.turn_on()
			elif self.mode == PL_MODES[2]:
				self.stop_imaging()
		elif mode == PL_MODES[2]:
			return self.start_imaging()
		return True
