from enum import IntEnum
import os
import struct
import time
from spacepackets.ccsds.spacepacket import (
    SpacePacket, SpacePacketHeader, PacketType, SequenceFlags,
)
APID_OBC = 0x10 
MIB_PATH = os.environ.get("MIB_PATH", "mib.txt")
HEADER_SIZE = 6

class TmType(IntEnum):
    ACK = 1; NACK = 2; HK_PF = 3; HK_PL = 4; EVENT = 5

class Evt(IntEnum):
    BOOT = 1; OBT_SET = 2; MODE_ACQ = 3; PL_ON = 4; PL_OFF = 5
    TT_EXEC = 6; TT_FAIL = 7; SEQ_GAP = 8; IMG_START = 9; IMG_END = 10

PF_MODES = ["SAFE", "NADIR", "TARGET", "TRANSITION"] 


def s_to_HMS(s):
  return f"{s//3600}:{s%3600//60}:{s%60}"

def HMS_to_s(hms):
  t,h,s = hms.split(":")
  return int(t)*3600+int(h)*60+int(s)

def get_s():
  t = time.localtime()
  return t.tm_hour * 3600 + t.tm_min * 60 + t.tm_sec

def load_mib(path=MIB_PATH):
  name = {}
  with open(path) as f:
    for line in f:
      if line and not line.startswith("#"):
        parts = line.split()
        if line.startswith("TC"):
          args = parts[4].split("=")[1:]
          name[parts[1]] = {"name": parts[1], "id":int(parts[2]),"target": parts[3], "args": args, "time_tag_allowed": parts[5] == "YES"}
        #TODO add tms
  return name, {t["id"]: t for t in name.values()}



class Framer:
  "Frames the incoming data stream into complete packets"
  def __init__(self):# The class is needed for multi connections such as the OBC
    self.buf=bytearray()

  def add(self,chunk):
    output=[]
    self.buf.extend(chunk)
    while len(self.buf)>=HEADER_SIZE:#only loop through when the header or more has arrived
      header = SpacePacketHeader.unpack(bytes(self.buf[:HEADER_SIZE]))
      total = HEADER_SIZE+header.data_len + 1 #CCSDS loves the minus one 
      if len(self.buf)>total: #Yeet short packages
        break
      output.append((header,bytes(self.buf[HEADER_SIZE:total])))
      del self.buf[:total]# remove packet and continue
    return output

def packer(Packet_Type, APID, seq,data):
  header= SpacePacketHeader(
    packet_type=Packet_Type,
    apid=APID,
    seq_count=seq,
    data_len=len(data) - 1,   # CCSDS lovs another minus one
    sec_header_flag=False,# No secondary header
    seq_flags=SequenceFlags.UNSEGMENTED,# Only sending complete packets
  )
  return SpacePacket(header,sec_header=None,user_data=data).pack()# No secondary header

#----
# I was trying to look into making the packet into structured byte arrays but that is was a rabbit hole, could be something for further development idk /Oliver

#def encode_pack(cmd_id,times,data=b""):# first five bits will always be command id and a timestamp
#  return struct.pack(">BI",cmd_id,times)+data
#def decode_pack(data):
#  return struct.unpack(">BI",data[:5]),data[5:]

#----

class SequenceCount:
  def __init__(self):
    self.n=0
  def next(self)-> int:# returns n and increments
    x=self.n
    self.n= self.n+1 #TODO avoid seq overflow
    return x
