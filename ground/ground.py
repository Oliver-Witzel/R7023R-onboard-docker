import selectors
import socket
import sys
import time
from threading import Thread

from prompt_toolkit import PromptSession
from prompt_toolkit.patch_stdout import patch_stdout
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
        print("\033[34mConnection to S/C established\033[0m", flush=True)
        self.sel.register(self.sock, selectors.EVENT_READ, self.readTM)


    def sendTC(self,target, input):
        seq = self.seq.next()
        self.sock.sendall(packer(PacketType.TM,target,seq,input.encode()))
        self.pending[seq] = (APID_OBC,time.monotonic())
        print(f"\033[34mSent TC APID={APID_OBC} seq={seq}\033[0m", flush=True)
    
    def readTM(self, sock):
        data = sock.recv(4096)
        for hdr, payload in self.frame.add(data):
            last_seq = self.last_tm_seq.get(hdr.apid)
            if last_seq is not None and hdr.seq_count != last_seq+1:
                print(f"\033[33mTM seq gap for APID={hdr.apid}  at last_seq={last_seq}\033[0m", flush=True)
            self.last_tm_seq[hdr.apid] = hdr.seq_count
            tm_type,obt,args=payload.decode().split("_")
            tm_type = int(tm_type)
            obt = int(obt)
            if args and "," in args:args=args.split(",")
            self.print_log(hdr,tm_type,obt,args)
            
            
    def print_log(self,hdr,tm_type,obt,args):
        txt=""
        if tm_type==TmType.ACK:
            self.pending.pop(hdr.seq_count, ("?", 0)) 
            app = "OBC" if hdr.apid==APID_OBC else "PL"
            txt=f"Acknowledgement: TC={self.tcIDs[int(args[0])]["name"]}  by {app}, seq:{args[1]}"
        if tm_type==TmType.NACK:
            self.pending.pop(hdr.seq_count, ("?", 0))  
            app = "OBC" if hdr.apid==APID_OBC else "PL"
            txt=f"NO Acknowledgement: TC={self.tcIDs[int(args[0])]["name"]}Rejected by {app} Because:{args[2]}, seq:{args[1]}"
        if tm_type==TmType.EVENT: txt=f"EVENT: {Evt(int(args[0])).name} message:{args[1]}"
        if tm_type==TmType.HK_OBC:txt=f"HOUSEKEEPING OBC: PL power {1 if args[0] else 0} Recieved TC:s {args[1]} Rejected TC:s{args[2]}"
        if tm_type==TmType.HK_PL:txt=f"HOUSEKEEPING PL: Mode {args[0]} Total images taken: {args[1]} Last image time {args[2]}"
        print(f"\033[32m[{s_to_HMS(get_s())}] | OBT:[{s_to_HMS(obt)}] | {txt}\033[0m", flush=True)
        if tm_type==TmType.HK_OBC or tm_type==TmType.HK_PL:
            self.log.write(f"[{s_to_HMS(get_s())}] OBT {s_to_HMS(obt)}  {txt}|\n")
        
        
    def parse_cmd(self,cmd):
        parts=cmd.split()
        if parts[0] not in self.tcs:  return print("\033[31mError: Unknown command\033[0m", flush=True)
        tc=self.tcs[parts[0]]
        args=""
        if len(parts) ==2 and parts[0] == "SET-OBT":
            time = parts[1]
            values = time.split(":")
            if len(values) == 3 and all(len(v) == 2 and v.isdigit() for v in values):
                hh = int(values[0])
                mm = int(values[1])
                ss = int(values[2])
                if 1 <= hh <= 24 and 0 <= mm <= 59 and 0 <= ss < 60:
                    args = HMS_to_s(parts[1])
                else:
                    return print("\033[31mError: Invalid time format. Please use HH:MM:SS with valid ranges.\033[0m", flush=True)

        if parts[0] == "SET-OBC-MODE":
            if len(parts) ==2 and parts[1] in OBC_MODES:
                args = parts[1]
            else:
                return print("\033[31mError: Invalid OBC mode. Valid modes are:\033[0m", ", ".join(OBC_MODES), flush=True)
        
        if parts[0] == "SET-PL-POWER":
            if len(parts) ==2 and (parts[1] == "1" or parts[1] == "0"):
                args = parts[1]
            else:
                return print("\033[31mError: Invalid PL power state. Use 1 for ON or 0 for OFF.\033[0m", flush=True)

        self.sendTC(tc["target"],f"{tc["id"]}_{0}_{args}")
        #The TC packet datafield should be of this format
        #"{cmd_id} {timestamp} {args} " #TODO add execution time
    def TM_handler(self):
        while True:
            for key, _ in self.sel.select(timeout=0.2):
                key.data(key.fileobj)#waits for TM to arrive on TCP LINK

            
            for seg,(apid, timestamp) in list(self.pending.items()):
                if seg and time.monotonic() - timestamp > 10:
                    print(f"\033[33mTC APID={apid} timeout for seq={seg}\033[0m", flush=True)
                    del self.pending[seg]
    def run(self):
        if not self.sock:self.connect()
        
        session = PromptSession()

        with patch_stdout(raw=True):
            Thread(target=self.TM_handler,daemon=True).start()#Put Tm in secondary thread to allow for smooth UI
            while True:
                try:
                    cmd = session.prompt("> ")
                except (EOFError, KeyboardInterrupt):
                    return

                if cmd == "QUIT":
                    return
                if cmd:
                    self.parse_cmd(cmd)
            



if __name__ == "__main__": Ground().run()
