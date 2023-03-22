import os
import sys


class NullWriter:
    def write(self, s):
        pass

    def flush(self):
        pass


# silence command-line output temporarily
sys.stdout, sys.stderr = NullWriter(), NullWriter()

from asammdf import MDF, SUPPORTED_VERSIONS, Signal

# unsilence command-line output
sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__
print("Hello")

# mdf = MDF("/media/projects/Tesla_HRL/asammdf/sample-data/UDS (Nissan Leaf EV)/LOG/2F6913DB/00000020/00000001-61D9D830.MF4")
# data = mdf.get('CAN_DataFrame.DataBytes')
# for idx in range(len(mdf.get('CAN_DataFrame.DataLength').samples)):
#     print(idx, end="\r")
#     if mdf.get('CAN_DataFrame.DataLength').samples[idx] != 8:
#         print(idx)
#         break
# a =1
