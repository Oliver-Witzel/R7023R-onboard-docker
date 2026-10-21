import os
import socket
import time
from datetime import datetime
from spacepackets.ccsds.spacepacket import (
    SpacePacket, SpacePacketHeader, PacketType, SequenceFlags,
)

HOST, PORT = "obc", 5000   # 'receiver' = compose service name
APID = 0x42

MIB_PATH = os.environ_get("MIB_PATH", "mib.txt")


def load_mib(path=MIB_PATH):
  tcs, tms = {}, {}



def connect_with_retry() -> socket.socket:
    while True:
        try:
            return socket.create_connection((HOST, PORT), timeout=5)
        except OSError:
            print("receiver not ready, retrying...", flush=True)
            time.sleep(1)

sock = connect_with_retry()
with sock:
    for seq in range(10):
        payload = f"hello {seq}".encode()
        header = SpacePacketHeader(
            packet_type=PacketType.TM,
            apid=APID,
            seq_count=seq,
            data_len=len(payload) - 1,   # CCSDS: length minus one
            sec_header_flag=False,
            seq_flags=SequenceFlags.UNSEGMENTED,
        )
        packet = SpacePacket(header, sec_header=None, user_data=payload)
        sock.sendall(packet.pack())
        print("sent", seq, flush=True)
        time.sleep(0.5)
