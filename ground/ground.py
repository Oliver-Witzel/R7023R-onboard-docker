import selectors
import socket
import time

from spacepackets.ccsds.spacepacket import PacketType

from common.common import *

HOST, PORT = "obc", 5000   # 'receiver' = compose service name
APID = 0x42

class Ground:
    def __init__(self):
        #self.tcs = load_mib()
        self.seq = SequenceCount()
        self.sock = None
        self.frame = Framer()
        self.sel = selectors.DefaultSelector()


    def connect(self):
        s = socket.create_connection((HOST, PORT), timeout=5)
        #except OSError: print("Whoops"); return
        s.setblocking(False)
        self.sock=s
        print("Connection to S/C established")


    def sendTC(self, input):
        self.sock.sendall(packer(PacketType.TM,APID_OBC,self.seq.next(),input))
        print("sent",self.seq.n)

    def run(self):
        if not self.sock:self.connect()

        for n in range(10):
            payload = f"helo {n}".encode()
            self.sendTC(payload)
            time.sleep(1)

        
if __name__ == "__main__": Ground().run()   
