import os
import socket
import time
from datetime import datetime

MIB_PATH = os.environ_get("MIB_PATH", "mib.txt")


def load_mib(path=MIB_PATH):
  tcs, tms = {}, {}
