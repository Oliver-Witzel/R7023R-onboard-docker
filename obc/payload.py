from common.common import *
from threading import Timer

class Payload:
    def __init__(self,report):
        self.mode = PL_MODES[0]
        self.power= False
        self.t0 = time.monotonic(); self.time_set = False; self.obt_base = 0; self.obt_mono = 0
        self.log = open(os.environ.get("PL_LOG", "Pl_log.txt"), "a+", buffering=1)
        self.log.seek(0)
        self.taken_images = sum(1 for _ in self.log)
        self.last_image_time = 0
        self.report = report
    def turn_on(self):
        if self.mode == PL_MODES[0]:
            self.power = True
            self.mode = PL_MODES[1]
            self.report(Evt.PL_ON,f"{self.now()}")

    def turn_off(self):
        self.power=False
        self.mode = PL_MODES[0]
        self.report(Evt.PL_OFF,f"{self.now()}")

    def start_imaging(self):
        if self.mode != PL_MODES[1]:
            return False
        self.mode = PL_MODES[2]
        Timer(5, self.done_imaging).start()
        self.report(Evt.IMG_START,f"{self.now()}")
         
    def done_imaging(self):
        self.log.write(f"[{s_to_HMS(self.now())}]<PL> Image taken\n")
        print(f"\033[33m[{s_to_HMS(self.now())}]<PL> Image taken\033[0m")
        self.taken_images += 1
        self.last_image_time = self.now()
        self.report(Evt.IMG_END,f"{self.now()}")
        self.stop_imaging()

    def stop_imaging(self):
        if self.mode == PL_MODES[2]:
            self.mode = PL_MODES[1]
    def sync_time(self,s):
        self.obt_base, self.obt_mono, self.time_set = s, time.monotonic(), True
        return True
    def now(self):
        if self.time_set:
            return (self.obt_base + int(time.monotonic() - self.obt_mono))
        return int(time.monotonic() - self.t0)
    def hk(self):
        self.report(Evt.HK_ACQ,f"{self.mode},{self.taken_images},{self.last_image_time}")

    def execute(self,cmd):
        txt=""
        if cmd not in PL_CMD:
            txt="Unknown PL command"
        if cmd == PL_CMD[2]:
            self.turn_off()
            txt="PL is powered OFF"
        if cmd == PL_CMD[1]:
            self.turn_on()
            txt="PL is powered ON"
        if cmd == PL_CMD[0]:
            if self.mode =="IMAGING" or self.mode =="OFF":
                txt="PL is busy\033[0m"
            else:
                self.start_imaging()
                txt="Imaging has started"
        if cmd == PL_CMD[3]:
            self.hk()
        print(f"\033[33m[{s_to_HMS(self.now())}]<PL> {txt}\033[0m")#\033[33m gives a splash of yellow for readability in terminal 
            
