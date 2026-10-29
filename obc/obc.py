import selectors
import socket

from spacepackets.ccsds.spacepacket import SpacePacketHeader
from threading import Timer
from common.common import *
from payload import Payload

HOST, PORT = "0.0.0.0", 5000
HK_TIME = 5
class OBC:
    def __init__(self):
        self.tcs, self.tcIDs = load_mib()
        self.seq = SequenceCount()
        self.frame = Framer()
        self.sel = selectors.DefaultSelector()
        self.gnd = None
        self.mode = OBC_MODES[2]; self.target = None; self.trans_time=0
        self.pl = Payload(self.execute)
        self.t0 = time.monotonic(); self.time_set = False; self.obt_base = 0; self.obt_mono = 0 
        self.tc_rx=0;self.tc_rej=0;self.last_tc_seq = None
        self.last_hk = time.monotonic()
    def send_TM(self,TM_type,data):
        paket = packer(PacketType.TM,APID_OBC,self.seq.next(),f"{TM_type}_{self.now()}_{data}".encode())
        self.gnd.sendall(paket)
    def ack(self,cmd_id,seq): self.send_TM(TmType.ACK,f"{cmd_id},{seq}")
    def nack(self,cmd_id,seq,mes):
        self.tc_rej+=1;
        print(f"rejected: {mes}") 
        self.send_TM(TmType.NACK,f"{cmd_id},{seq},{mes}") 
    def event(self,id,mes): self.send_TM(TmType.EVENT,f"{id},{mes}")
    def obc_hk(self):
        self.send_TM(TmType.HK_OBC,f"{self.pl.power},{self.tc_rx},{self.tc_rej}")
    def pl_hk(self,args):
        self.send_TM(TmType.HK_PL,args)

    def now(self):
        if self.time_set:
            return (self.obt_base + int(time.monotonic() - self.obt_mono))
        return int(time.monotonic() - self.t0)
    

    def gnd_acc(self,srv):
        conn, addr = srv.accept()
        self.gnd = conn
        print("Accepting connection from",addr, flush=True)
        self.event(Evt.BOOT,f"OBC BOOTED, mode SAFE, time {self.now()}")
        self.sel.register(conn,selectors.EVENT_READ,self.gnd_read)

    def gnd_read(self,conn):
        try:buf = conn.recv(4096)
        except ConnectionResetError:self.gnd=None;return print("dropped gnd")
        for hdr,data in self.frame.add(buf):
            self.on_tc(hdr,data)       

    def on_tc(self,hdr,data):
        Id,tt,args = data.decode().split("_")
        seq=hdr.seq_count
        try:#OBC 3.4
            tc = self.tcIDs[int(Id)]
        except (ValueError, KeyError):
            return self.nack(Id, seq, "Unknown or invalid TC ID")

        self.tc_rx += 1
        if self.last_tc_seq is not None and seq != (self.last_tc_seq + 1):
                self.event(Evt.SEQ_GAP, f"TC seq gap: got {seq} after {self.last_tc_seq}")
                self.last_tc_seq = seq
        why = self.check_mode(tc,args)
        if why:return self.nack(Id,seq,why)
        #TODO check tt
        self.ack(Id,seq)
        self.execute(tc,args)
    def check_mode(self,tc,args):
        if self.mode == OBC_MODES[3]: return "IN TRANSITION"
        if tc["target"]==APID_PL:
            if self.mode == OBC_MODES[0]:return "OBC IN SAFE MODE"
            if tc["name"]=="SET-PL-POWER" and int(args)==self.pl.power:return "PL POWER IS AT REQUESTED LEVEL"
            if tc["name"]!="SET-PL-POWER" and not self.pl.power: return "PL IS OFF"
        if tc["name"]=='SET-OBC-MODE' and self.mode==args:return "OBC ALREADY AT MODE"
        return None
    def set_mode(self,mode):
        if mode == OBC_MODES[0] and self.pl.power:
            self.pl.execute(PL_CMD[2])
        self.target, self.mode = mode,"TRANSITION"
        self.trans_time = time.monotonic()+5 #TODO add different times each mode
        

    def check_transition(self):
        if self.mode == OBC_MODES[3] and time.monotonic()>=self.trans_time:
            self.mode = self.target
            self.event(Evt.MODE_ACQ, f"MODE {self.mode} ACQUIRED at {s_to_HMS(self.now())}")


    def execute(self,tc,args):
        Type = tc["name"] if isinstance(tc, dict) else tc       
        if Type == "SET-OBT":
            self.obt_base, self.obt_mono, self.time_set = int(args), time.monotonic(), True
            self.pl.sync_time(int(args))
            self.event(Evt.OBT_SET, f"OBT SET {s_to_HMS(int(args))}")
            print(f"Time was set to {s_to_HMS(int(args))}")
        if Type=="REQ-HK":
            self.obc_hk()
        if Type=="SET-PL-POWER":
            if int(args):
                return self.pl.execute(PL_CMD[1])#Power on
            self.pl.execute(PL_CMD[2])
        if Type=="SET-OBC-MODE":
            self.set_mode(args)
        if Type=="PL-TAKE-IMAGE":
            self.pl.execute(PL_CMD[0])
        if Type=="REQ-PL-HK":
            self.pl.execute(PL_CMD[3])
        #handle incoming pl cmd
        if Type==Evt.IMG_END:
            print(f"PL has returned with{args}")
        if Type==Evt.PL_ON:
            self.event(Evt.PL_ON,f"[{self.now()}]PL ON")
        if Type==Evt.PL_OFF:
            self.event(Evt.PL_OFF,f"[{self.now()}]PL ON")
        if Type==Evt.HK_ACQ:
            self.pl_hk(Evt.HK_ACQ,args)
        
        
            
    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST,PORT))
        srv.listen()
        srv.setblocking(False)
        self.sel.register(srv,selectors.EVENT_READ,self.gnd_acc)
        print("OBC up, SAFE", flush=True)
        while True:
            for key, _ in self.sel.select(0.1):
                key.data(key.fileobj)
            self.check_transition()
            if time.monotonic()>=self.last_hk+HK_TIME:
                self.last_hk = time.monotonic()
                self.obc_hk()
            

if __name__ == "__main__": OBC().run()   
