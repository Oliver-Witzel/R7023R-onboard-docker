import selectors
import socket
from spacepackets.ccsds.spacepacket import SpacePacketHeader
from common.common import *

HOST, PORT = "0.0.0.0", 5000

class OBC:
    def __init__(self):
        self.tcs, self.tcIDs = load_mib()
        self.seq = SequenceCount()
        self.frame = Framer()
        self.sel = selectors.DefaultSelector()
        self.gnd = None
        self.t0 = time.monotonic(); self.time_set = False; self.obt_base = 0; self.obt_mono = 0
    def send_TM(self,TM_type,data):
        paket = packer(PacketType.TM,APID_OBC,self.seq.next(),f"{TM_type} {self.now()} {data}".encode())
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
        self.sel.register(conn,selectors.EVENT_READ,self.gnd_read)

    def gnd_read(self,conn):
        buf = conn.recv(4096)
        for hdr,data in self.frame.add(buf):
            self.on_tc(hdr,data)
            

    def on_tc(self,hdr,data):
        Id,tt,args = data.decode().split()
        #TODO check seq order
        #TODO check mode
        #TODO check tt
        self.ack(Id,hdr.seq_count)
        self.execute(Id,args)
        
    def execute(self,Id,args):       
        if int(Id)==self.tcs["SET-OBT"]["id"]:
            self.obt_base, self.obt_mono, self.time_set = int(args), time.monotonic(), True
            self.event(Evt.OBT_SET, f"OBT SET {s_to_HMS(int(args))}")
            print(f"Time was set to {s_to_HMS(int(args))}")

        
            
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
