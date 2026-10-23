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
        self.time = None
    def send_TM(self,data):
        paket = packer(PacketType.TM,APID_OBC,self.seq.next(),data.encode())
        self.gnd.sendall(paket)
    def ack(self,cmd_id,seq,mes): self.send_TM(f"{TmType.ACK} {cmd_id} {seq} {mes}");  
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
        Id,args = data.decode().split()
        if int(Id)==self.tcs["SET-OBT"]["id"]:
            #TODO set the time
            print(f"Time was set to {s_to_HMS(int(args))}")
            self.ack(Id,hdr.seq_count,f"Time was set to {s_to_HMS(int(args))}")
        
            

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
