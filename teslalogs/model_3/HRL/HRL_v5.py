import datetime
import sys
from argparse import ArgumentParser
from pathlib import Path
from zlib import crc32

import numpy as np


class NullWriter:
    def write(self, s):
        pass

    def flush(self):
        pass


# silence command-line output temporarily
sys.stdout, sys.stderr = NullWriter(), NullWriter()


from asammdf import MDF, Signal
from asammdf.blocks.mdf_v4 import MDF4
from asammdf.blocks.v4_blocks import SourceInformation, v4c

# unsilence command-line output
sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

from teslalogs.model_3.HRL.hrl_v5_parser import HrlV5Parser

# STD_DTYPE = np.dtype(
#         [
#             ("CAN_DataFrame.BusChannel", "<u1"),
#             ("CAN_DataFrame.ID", "<u4"),
#             ("CAN_DataFrame.IDE", "<u1"),
#             ("CAN_DataFrame.DLC", "<u1"),
#             ("CAN_DataFrame.DataLength", "<u1"),
#             ("CAN_DataFrame.DataBytes", "(64,)u1"),
#             ("CAN_DataFrame.Dir", "<u1"),
#             ("CAN_DataFrame.EDL", "<u1"),
#             ("CAN_DataFrame.BRS", "<u1"),
#             ("CAN_DataFrame.ESI", "<u1"),
#         ]
#     )


# class MDFWriter:
#     def __init__(self, file, database):
#         now = datetime.now()
#         self._mdf = cast(MDF4, MDF(version="4.10"))
#         self._mdf.header.start_time = now
#         self.last_timestamp = self._start_time = now.timestamp()


def verify_block(block):
    crc_calc = ~crc32(block.raw_data) & 0xFFFFFFFF
    if block.crc != crc_calc:
        raise ValueError("Invalid crc!")


def to_mdf(frames, out_file, dbcs=None):
    bus, arb_id, dlc, data = [], [], [], []
    Timestamp = []

    count = 0
    for time, frame in sorted(frames, key=lambda x: x[0]):  # The HRL blocks can be out of order
        if frame.arb_id:
            Timestamp.append(time)
            bus.append(frame.bus_id.value + 1)  # 0 refers to any bus in asammdf, so add 1
            arb_id.append(frame.arb_id)
            dlc.append(frame.dlc)
            data.append([int(b) for b in frame.data])

            count += 1
        #     str_data = frame.data.hex()[: frame.dlc * 2].upper()
        #     print(f"({time:0.6f}) can{frame.bus_id.value} {frame.arb_id:03X}#{str_data}")

        # str_data = frame.data.hex()[: frame.dlc * 2].upper()
        # print(f"({time:0.6f}) can{frame.bus_id.value} {frame.arb_id:03X}#{str_data}")

    print(len(Timestamp), count)
    zeros = [0] * len(Timestamp)
    samples = [bus, arb_id, zeros, dlc, dlc, data, zeros, zeros, zeros, zeros]
    types = np.dtype(
        [
            ("CAN_DataFrame.BusChannel", "u1"),
            ("CAN_DataFrame.ID", "<u4"),
            ("CAN_DataFrame.IDE", "u1"),
            ("CAN_DataFrame.DLC", "u1"),
            ("CAN_DataFrame.DataLength", "u1"),
            ("CAN_DataFrame.DataBytes", "u1", (8,)),
            ("CAN_DataFrame.Dir", "u1"),
            ("CAN_DataFrame.EDL", "u1"),
            ("CAN_DataFrame.ESI", "u1"),
            ("CAN_DataFrame.BRS", "u1"),
        ]
    )

    mdf = MDF()
    sig = Signal(np.core.records.fromarrays(samples, dtype=types), Timestamp, name="CAN_DataFrame", comment="CAN_DataFrame", flags=v4c.BUS_TYPE_CAN)

    source = SourceInformation(source_type=v4c.SOURCE_BUS, bus_type=v4c.BUS_TYPE_CAN, flags=v4c.FLAG_CG_BUS_EVENT)
    mdf.append([sig], acq_source=source)
    mdf.groups[0].channel_group.flags = v4c.FLAG_CG_BUS_EVENT

    mdf.export("csv", "/media/projects/hrl5_.txt")
    mdf.save(out_file, overwrite=True)

    # if dbcs:
    #     mdf = mdf.extract_bus_logging(database_files=dbcs)
    #     mdf.save(out_file, overwrite=False)

    return mdf


def gen_can_frames(blocks, t_start):
    rolling_time = 0
    for block in blocks:
        try:
            verify_block(block)
        except ValueError:
            print("CRC error, skipping block")
            continue

        for record in block.records:
            if record.end_of_block:
                break
            if record.flags == HrlV5Parser.Record.RecordType.time:
                rolling_time = record.payload.time_ms_from_start
            elif record.flags == HrlV5Parser.Record.RecordType.can:
                time = t_start + rolling_time + record.time_count
                yield time, record.payload


if __name__ == "__main__":
    args = ArgumentParser()
    args.add_argument("hrl_path", type=Path, help="Path to HRL file")
    args.add_argument("out_path", type=Path, help="Path to output file")
    args = args.parse_args()

    if not args.hrl_path.exists() or not args.hrl_path.is_file():
        print("File not found, exiting")
        exit(1)

    parser = HrlV5Parser.from_file(args.hrl_path)

    t_start = parser.header.start_time * 1000
    frame_generator = gen_can_frames(parser.blocks, t_start)
    databases = {
        "CAN": [
            ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_VEH.compact.dbc", 1),
            ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_PARTY.compact.dbc", 2),
            ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_CH.compact.dbc", 3),
        ]
    }
    mdf = to_mdf(frame_generator, args.out_path, databases)
