import selectors
import socket

from spacepackets.ccsds.spacepacket import SpacePacketHeader
from threading import Timer
from common.common import *
from payload import Payload

HOST, PORT = "0.0.0.0", 5000

class OBC:
    def __init__(self):
        self.tcs, self.tcIDs = load_mib()
        self.seq = SequenceCount()
        self.frame = Framer()
        self.sel = selectors.DefaultSelector()
        self.gnd = None
        self.mode = OBC_MODES[0]
        self.pl = Payload(self.execute)
        self.t0 = time.monotonic(); self.time_set = False; self.obt_base = 0; self.obt_mono = 0 
        self.tc_rx=0;self.tc_rej=0
    def send_TM(self,TM_type,data):
        paket = packer(PacketType.TM,APID_OBC,self.seq.next(),f"{TM_type}_{self.now()}_{data}".encode())
        self.gnd.sendall(paket)
    def ack(self,cmd_id,seq): self.send_TM(TmType.ACK,f"{cmd_id},{seq}")
    def nack(self,cmd_id,seq,mes): self.send_TM(TmType.NACK,f"{cmd_id},{seq},{mes}")
    def obc_hk(self):self.send_TM(1,1)    
    def event(self,id,mes): self.send_TM(TmType.EVENT,f"{id},{mes}")

    def now(self):
        if self.time_set:
            return (self.obt_base + int(time.monotonic() - self.obt_mono))
        return int(time.monotonic() - self.t0)
    

    def gnd_acc(self,srv):
        conn, addr = srv.accept()
        self.gnd = conn
        print("Accepting connection from",addr, flush=True)
        self.start_pl()
        self.sel.register(conn,selectors.EVENT_READ,self.gnd_read)

    def gnd_read(self,conn):
        try:buf = conn.recv(4096)
        except ConnectionResetError:self.gnd=None;return print("dropped gnd")
        for hdr,data in self.frame.add(buf):
            self.on_tc(hdr,data)
            

    def on_tc(self,hdr,data):
        Id,tt,args = data.decode().split("_")
        self.tc_rx += 1
        #TODO check seq order
        #TODO check mode
        #TODO check tt
        self.ack(Id,hdr.seq_count)
        self.execute(Id,args)
        
    def execute(self,Id,args):       
        if int(Id)==self.tcs["SET-OBT"]["id"]:
            self.obt_base, self.obt_mono, self.time_set = int(args), time.monotonic(), True
            self.pl.sync_time(int(args))
            self.event(Evt.OBT_SET, f"OBT SET {s_to_HMS(int(args))}")
            print(f"Time was set to {s_to_HMS(int(args))}")
        
        #handle incoming pl
        if int(Id)==Evt.IMG_END:
            print(f"PL has returned with{args}")
        if int(Id)==Evt.PL_ON:
            self.event(Evt.PL_ON,f"[{self.now()}]PL ON")
        
    def start_pl(self):
        self.pl.execute(PL_CMD[1])#is this pretty no, does this work yes
        self.event(Evt.BOOT,f"OBC BOOTED, mode SAFE, time {self.now()}")
            
    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST,PORT))
        srv.listen()
        srv.setblocking(False)
        self.sel.register(srv,selectors.EVENT_READ,self.gnd_acc)
        while True:
            for key, _ in self.sel.select():
                key.data(key.fileobj)

if __name__ == "__main__": OBC().run()   
