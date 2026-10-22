import os


MIB_PATH = os.environ.get("MIB_PATH", "mib.txt")


def load_mib(path=MIB_PATH):
  tcs, tms = {}, {}
with open(path) as f:
    for line in f:
      if line and not line.startswith("#"):
        parts = line.split()
        if len(parts) == 3:
          name, target, args = parts