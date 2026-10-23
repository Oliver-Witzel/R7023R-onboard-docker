import selectors
import socket
from spacepackets.ccsds.spacepacket import SpacePacketHeader
from common.common import *

HOST, PORT = "0.0.0.0", 5000

class OBC:
    def __init__(self):
        self.tcs, self.tms = load_mib()
        self.seq = SequenceCount()
        self.sock = None
        self.frame = Framer()
        self.sel = selectors.DefaultSelector()
    def gnd_acc(self,srv):
        conn, addr = srv.accept()
        print("Accepting connection from",addr, flush=True)
        self.sel.register(conn,selectors.EVENT_READ,self.gnd_read)

    def gnd_read(self,conn):
        buf = conn.recv(4096)
        for hdr,data in self.frame.add(buf):
            print(f"APID={hdr.apid} seq={hdr.seq_count} "
                                      f"type={hdr.packet_type.name} payload={data!r}",
                                      flush=True)

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
