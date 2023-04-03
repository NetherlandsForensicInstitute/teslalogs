import re
import mmap
import struct
from argparse import ArgumentParser
from zlib import crc32
from pathlib import Path
from kaitaistruct import KaitaiStream, BytesIO
from teslalogs.model_3.model_3_hrl import Model3Hrl

SEARCH_SIZE = 50 * 1024**2
RECORDSIZE = 11


def try_hrl_size(stream):
    header = Model3Hrl.FirstBlock(stream)
    blocksize = header.blocksize
    while True:
        block = stream.read_bytes(blocksize)
        try:
            verify_block(block)
        except ValueError:
            break
    stream.seek(stream.pos() - blocksize)
    print(f'{header.start_timestamp:08x}', stream.pos())
    if stream.pos() == blocksize:
        # Did not find a single valid block after the header
        return None
    return header.start_timestamp, stream.pos()


def verify_block(block):
    blocksize = len(block)
    crc_pos = blocksize - (blocksize % RECORDSIZE)
    crc = struct.unpack('>I', block[crc_pos: crc_pos + 4])[0]
    crc_calc = ~crc32(block[:crc_pos]) & 0xffffffff
    if crc != crc_calc:
        raise ValueError('Invalid crc!')


def search_image(data, vin, out_dir):
    vin = vin.encode('ascii') + b'\x00'
    pat = re.compile(vin)
    for hit in pat.finditer(data):
        start = hit.start() - 0x15  # offset of VIN from start of block
        tmp = data[start:start + SEARCH_SIZE]
        stream = KaitaiStream(BytesIO(tmp))
        result = try_hrl_size(stream)
        if result is not None:
            t_start, length = result
            save(t_start, tmp[:length], out_dir)


def save(t_start, data, out_dir):
    name = f'{t_start:08x}'
    num = 0
    suffix = ''
    while (out_dir / f'{name}{suffix}.HRL').exists():
        num += 1
        suffix = f'_{num}'
    (out_dir / f'{name}{suffix}.HRL').write_bytes(data)


def main(f_in, out_dir, vin):
    with open(f_in, 'rb') as f:
        with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as m:
            search_image(m, vin, out_dir)


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('f_in',
                      help='SD card image to carve in')
    args.add_argument('out_dir',
                      help="Output directory to put carved HRL's in")
    args.add_argument('VIN',
                      help='Vehicle VIN required for searching')
    args = args.parse_args()
    f_in = Path(args.f_in)
    out_dir = Path(args.out_dir)
    vin = args.VIN

    if not f_in.exists() or not f_in.is_file():
        print(f'Did not find image: {f_in}, exiting.')
        exit(1)
    if not out_dir.exists():
        out_dir.mkdir(parents=True)
    main(f_in, out_dir, vin)
