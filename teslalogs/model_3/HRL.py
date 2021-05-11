import numpy as np
import pandas as pd
from zlib import crc32
from argparse import ArgumentParser
from pathlib import Path
from .model_3_hrl import Model3Hrl


def verify_block(block):
    crc_calc = ~crc32(block.raw_records) & 0xffffffff
    if block.crc != crc_calc:
        raise ValueError('Invalid crc!')


def export_log(frames):
    for timestamp, frame in sorted(frames, key=lambda x: x[0]):  # The HRL blocks can be out of order
        data = frame.data.hex()[:frame.dlc * 2].upper()
        print(f'({timestamp:0.3f}) can{frame.bus_id.value} {frame.arb_id:03X}#{data}')


def parse_file(infile_path):
    parsed = Model3Hrl.from_file(infile_path)
    t_start = parsed.header.start_timestamp * 1000
    frame_generator = gen_frames(parsed.blocks, t_start=t_start)
    timestamps, records = zip(*frame_generator)
    tmp = {'timestamp': (np.array(timestamps, dtype='float64') * 1000).astype('datetime64[ms]'),
           'channel': np.array([r.bus_id.value for r in records], dtype='u1'),  # To get integer value
           'arbitration_id': np.array([r.arb_id for r in records], dtype='u2'),
           'dlc': np.array([r.dlc for r in records], dtype='u1'),
           'data': np.frombuffer(b''.join(r.data for r in records), dtype='<u8')}
    return pd.DataFrame(tmp)


def gen_frames(blocks, t_start):
    rolling_time = 0
    for block in blocks:
        try:
            verify_block(block)
        except ValueError:
            print('CRC error, skipping block')
            continue
        for record in block.records:
            if record.end_of_records:
                break
            if record.flags == Model3Hrl.Record.RecordFlags.timestamp_frame:
                rolling_time = record.payload.milliseconds_from_start
            elif record.flags == Model3Hrl.Record.RecordFlags.can_frame:
                timestamp = (t_start + rolling_time + record.counter) / 1000
                yield timestamp, record.payload


def main(infile_path):
    parsed = Model3Hrl.from_file(infile_path)
    t_start = parsed.header.start_timestamp * 1000
    frame_generator = gen_frames(parsed.blocks, t_start=t_start)
    export_log(frame_generator)


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('hrl_path', help='Path to HRL file')
    args = args.parse_args()
    hrl_path = Path(args.hrl_path)
    if not hrl_path.exists() or not hrl_path.is_file():
        print('File not found, exiting')
        exit(1)
    main(hrl_path)
