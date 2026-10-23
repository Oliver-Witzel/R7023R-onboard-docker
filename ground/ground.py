import selectors
import socket
import sys
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
        self.pending = {}
        self.tcs = load_mib()[0]  # Load only TCs from MIB


    def connect(self):
        try: s = socket.create_connection((HOST, PORT), timeout=5)
        except: OSError: print("Whoops"); return
        s.setblocking(False)
        self.sock=s
        print("Connection to S/C established")
        self.sel.register(self.sock, selectors.EVENT_READ, self.readTM)


    def sendTC(self, input):
        seq = self.seq.next()
        self.sock.sendall(packer(PacketType.TM,APID_OBC,seq,input))
        self.pending[seq] = (APID_OBC,time.monotonic())
        print(f"Sent TC APID={APID_OBC} seq={seq}", flush=True)
    
    def readTM(self, sock):
        data = sock.recv(4096)
        for hdr, payload in self.frame.add(data):
            last_seq = self.pending.get(hdr.apid)
            if last_seq is not None and hdr.seq_count != last_seq+1:
                print(f"GAP in TM APID={hdr.apid}  at last_seq={last_seq}", flush=True)
            self.pending[hdr.apid] = hdr.seq_count

            print(f"APID={hdr.apid} seq={hdr.seq_count} "
                  f"type={hdr.packet_type.name} payload={payload!r}",
                  flush=True)
            del self.pending[hdr.seq_count]    
    def run(self):
        if not self.sock:self.connect()
        self.sel.register(sys.stdin, selectors.EVENT_READ, None)
        print("Enter command: ")
        while True:
            for key, _ in self.sel.select(timeout=0.2):
                if key.fileobj == sys.stdin:
                    cmd = sys.stdin.readline().strip()
                    if cmd == "QUIT": return 
                    if cmd: print(cmd)
                else: key.data(key.fileobj)
            for seg,(apid, timestamp) in self.pending.items():
                if seg and time.monotonic() - timestamp > 10:
                    print(f"TM APID={apid} timeout for seg={seg}", flush=True)
                    del self.pending[seg]
            #yo=True
            #if yo:
            #    for n in range(10):
            #        payload = f"helo {n}".encode()
            #       self.sendTC(payload)
            #        time.sleep(1)
            #yo=False



if __name__ == "__main__": Ground().run()
