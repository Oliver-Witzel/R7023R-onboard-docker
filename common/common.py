import os
from spacepackets.ccsds.spacepacket import (
    SpacePacket, SpacePacketHeader, PacketType, SequenceFlags,
)
APID_OBC = 0x10 
MIB_PATH = os.environ.get("MIB_PATH", "mib.txt")
HEADER_SIZE = 6

def load_mib(path=MIB_PATH):
  tcs, tms = {}, {}
  with open(path) as f:
    for line in f:
      if line and not line.startswith("#"):
        parts = line.split()
        if line.startswith("TC"):
          args = parts[3].split("=")[1:]
          tcs[parts[1]] = {"name": parts[1], "target": parts[2], "args": args, "time_tag_allowed": parts[4] == "YES"}
        elif line.startswith("TM"):
          tms[parts[1]] = {"name": parts[1], "type": parts[2], "fields": parts[3:]}
  return tcs, tms



#-----Packing Functions-----
#def encode_tc():

#def decode_tc():

#def encode_tm():

#def decode_tm():


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

class SequenceCount:
  def __init__(self):
    self.n=0
  def next(self)-> int:# returns n and increments
    x=self.n
    self.n= self.n+1 #TODO avoid seq overflow
    return x
