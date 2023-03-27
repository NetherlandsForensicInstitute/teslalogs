from argparse import ArgumentParser
from pathlib import Path
from zlib import crc32

import numpy as np
import pandas as pd

from teslalogs.model_3.HRL.HRL_v5 import MDFWriter, Message
from teslalogs.model_3.HRL.model_3_hrl import Model3Hrl


class Message:
    def __init__(self, timestamp, record: Model3Hrl.CanFrame):
        self.timestamp = timestamp
        self.channel = record.bus_id.value + 1  # 0 refers to any bus in asammdf, so add 1
        self.arbitration_id = record.arb_id
        self.dlc = record.dlc
        self.data = [int(d) for d in record.data]


def verify_block(block):
    crc_calc = ~crc32(block.raw_records) & 0xFFFFFFFF
    if block.crc != crc_calc:
        raise ValueError("Invalid crc!")


def export_log(frames):
    for timestamp, frame in sorted(frames, key=lambda x: x[0]):  # The HRL blocks can be out of order
        data = frame.data.hex()[: frame.dlc * 2].upper()
        print(f"({timestamp:0.3f}) can{frame.bus_id.value} {frame.arb_id:03X}#{data}")


def parse_file(infile_path):
    parsed = Model3Hrl.from_file(infile_path)
    t_start = parsed.header.start_timestamp * 1000
    frame_generator = gen_frames(parsed.blocks, t_start=t_start)
    timestamps, records = zip(*frame_generator)
    tmp = {
        "timestamp": (np.array(timestamps, dtype="float64") * 1000).astype("datetime64[ms]"),
        "channel": np.array([r.bus_id.value for r in records], dtype="u1"),  # To get integer value
        "arbitration_id": np.array([r.arb_id for r in records], dtype="u2"),
        "dlc": np.array([r.dlc for r in records], dtype="u1"),
        "data": np.frombuffer(b"".join(r.data for r in records), dtype="<u8"),
    }
    return pd.DataFrame(tmp)


def gen_frames(blocks):
    rolling_time = 0
    for block in blocks:
        try:
            verify_block(block)
        except ValueError:
            print("CRC error, skipping block")
            continue
        for record in block.records:
            if record.end_of_records:
                break
            if record.flags == Model3Hrl.Record.RecordFlags.timestamp_frame:
                rolling_time = record.payload.milliseconds_from_start
            elif record.flags == Model3Hrl.Record.RecordFlags.can_frame:
                timestamp = rolling_time + record.counter
                # yield timestamp, record.payload
                yield Message(timestamp / 1000, record.payload)


def main(args):
    # parsed = Model3Hrl.from_file(infile_path)
    # t_start = parsed.header.start_timestamp * 1000
    # frame_generator = gen_frames(parsed.blocks, t_start=t_start)
    # export_log(frame_generator)

    parser = Model3Hrl.from_file(args.hrl_path)
    mdfwriter = MDFWriter(args.out_path)

    print(len([frame.timestamp for frame in gen_frames(parser.blocks)]))
    print(parser.header.start_timestamp)

    mdfwriter.set_start_timestamp(parser.header.start_timestamp)
    for can_frame in sorted(gen_frames(parser.blocks), key=lambda x: x.timestamp):  # The HRL blocks may be out of order
        mdfwriter.on_message_received(can_frame)

        # str_data = "".join([f"{d:02X}" for d in can_frame.data])
        # print(f"{can_frame.timestamp:0.6f} can{can_frame.channel} {can_frame.arbitration_id:03X}#{str_data}")

    print("finished adding can frames. Saving and closing...")
    mdfwriter.close()
    print("Closed!")


if __name__ == "__main__":
    args = ArgumentParser()
    args.add_argument("hrl_path", type=Path, help="Path to HRL file")
    args.add_argument("out_path", type=Path, help="Path to HRL file")
    args = args.parse_args()
    hrl_path = Path(args.hrl_path)
    if not hrl_path.exists() or not hrl_path.is_file():
        print("File not found, exiting")
        exit(1)
    main(args)
