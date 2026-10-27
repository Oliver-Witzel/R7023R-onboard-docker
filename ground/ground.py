import selectors
import socket
import sys
import time

from spacepackets.ccsds.spacepacket import PacketType

from common.common import *

HOST, PORT = "obc", 5000   # 'receiver' = compose service name

class Ground:
    def __init__(self):
        self.seq = SequenceCount()
        self.sock = None
        self.frame = Framer()
        self.sel = selectors.DefaultSelector()
        self.pending = {}
        self.last_tm_seq={}
        self.tcs, self.tcIDs = load_mib()  # Load only TCs from MIB
        self.log = open(os.environ.get("HK_LOG", "HK_log.txt"), "a", buffering=1)
        

    def connect(self):
        try: s = socket.create_connection((HOST, PORT), timeout=5)
        except OSError: print("Whoops"); return
        s.setblocking(False)
        self.sock=s
        print("Connection to S/C established")
        self.sel.register(self.sock, selectors.EVENT_READ, self.readTM)


    def sendTC(self,target, input):
        seq = self.seq.next()
        self.sock.sendall(packer(PacketType.TM,target,seq,input.encode()))
        self.pending[seq] = (APID_OBC,time.monotonic())
        print(f"Sent TC APID={APID_OBC} seq={seq}", flush=True)
    
    def readTM(self, sock):
        data = sock.recv(4096)
        for hdr, payload in self.frame.add(data):
            last_seq = self.last_tm_seq.get(hdr.apid)
            if last_seq is not None and hdr.seq_count != last_seq+1:
                print(f"TM seq gap for APID={hdr.apid}  at last_seq={last_seq}", flush=True)
            self.last_tm_seq[hdr.apid] = hdr.seq_count
            tm_type,obt,args=payload.decode().split("_")
            tm_type = int(tm_type)
            obt = int(obt)
            if args and "," in args:args=args.split(",")
            self.print_log(hdr,tm_type,obt,args)
            
            
    def print_log(self,hdr,tm_type,obt,args):
        txt=""
        if tm_type==TmType.ACK: txt=f"TC {self.tcIDs[int(args[0])]["name"]} seq:{args[1]} Acknowledged by APID:{hdr.apid}"
        if tm_type==TmType.NACK: txt=f"TC {self.tcIDs[int(args[0])]["name"]} seq:{args[1]} Rejected. Reason:{args[2]}"
        if tm_type==TmType.EVENT: txt=f"EVENT: {Evt(int(args[0])).name} message:{args[1]}"
        print(f"[{s_to_HMS(get_s())}] OBT {s_to_HMS(obt)}  {txt}")
        if tm_type==TmType.HK_PF or tm_type==TmType.HK_PL:
            self.log.write(f"[{s_to_HMS(get_s())}] OBT {s_to_HMS(obt)}  {txt}")
        #del self.pending[hdr.seq_count]
    def parse_cmd(self,cmd):
        parts=cmd.split()
        if parts[0] not in self.tcs:  return print("Error: Unknown command")
        tc=self.tcs[parts[0]]
        args=""
        
        if parts[0] == "SET-OBT":
            time = parts[1]
            values = time.split(":")
            if len(values) == 3 and all(len(v) == 2 and v.isdigit() for v in values):
                hh = int(values[0])
                mm = int(values[1])
                ss = int(values[2])
                if 1 <= hh <= 24 and 0 <= mm <= 59 and 0 <= ss < 60:
                    args = HMS_to_s(parts[1])
                else:
                    return print("Error: Invalid time format. Please use HH:MM:SS with valid ranges.")

        if parts[0] == "REQ-HK":

        if parts[0] == "SET-OBC-MODE":
            if parts[1] in OBC_MODES:
                args = parts[1]
            else:
                return print("Error: Invalid OBC mode. Valid modes are:", ", ".join(OBC_MODES))
        
        if parts[0] == "SET-PL-POWER":
            if parts[1] == "1" or parts[1] == "0":
                args = parts[1]
            else:
                return print("Error: Invalid PL power state. Use 1 for ON or 0 for OFF.")
        
        if parts[0] == "PL-TAKE-IMAGE":
        
        if parts[0] == "REQ-PL-HK":

        self.sendTC(tc["target"],f"{tc["id"]}_{0}_{args} ")
        #The TC packet should be of this format
        #"{cmd_id} {timestamp} {args} " #TODO add execution time
        
    def run(self):
        if not self.sock:self.connect()
        self.sel.register(sys.stdin, selectors.EVENT_READ, None)
        print("Enter command: ")
        while True:
            for key, _ in self.sel.select(timeout=0.2):
                if key.fileobj == sys.stdin:# if selcetor event comes from stdin its from the terminal
                    cmd = sys.stdin.readline().strip()
                    if cmd == "QUIT": return 
                    if cmd: self.parse_cmd(cmd)
                    print(">")
                else: key.data(key.fileobj)#otherwise call the passed function

            
            for seg,(apid, timestamp) in list(self.pending.items()):
                if seg and time.monotonic() - timestamp > 10:
                    print(f"TC APID={apid} timeout for seg={seg}", flush=True)
                    del self.pending[seg]
            



if __name__ == "__main__": Ground().run()
