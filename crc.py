from zlib import crc32

BLOCKSIZE = 0x8000

with open("/media/projects/Tesla_HRL/green_aeb_close_call/hrl_ecu-2022-03-02T14_15_38-2.hrl", "rb") as f:
    data = f.read()
    n = 3
    block = data[BLOCKSIZE*n:BLOCKSIZE*(n+1)]
    data = block[0x20:BLOCKSIZE-11]
    print(hex(~crc32(data) & 0xffffffff))
    print(block[-11:])

