import os
import sys
from argparse import ArgumentParser
from datetime import datetime
from hashlib import md5
from pathlib import Path
from typing import cast
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
from asammdf.blocks.v4_blocks import SourceInformation
from asammdf.blocks.v4_constants import BUS_TYPE_CAN, FLAG_CG_BUS_EVENT, SOURCE_BUS

# unsilence command-line output
sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

from teslalogs.model_3.HRL.hrl_v5_parser import HrlV5Parser

STD_DTYPE = np.dtype(
    [
        ("CAN_DataFrame.BusChannel", "<u1"),
        ("CAN_DataFrame.ID", "<u4"),
        ("CAN_DataFrame.IDE", "<u1"),
        ("CAN_DataFrame.DLC", "<u1"),
        ("CAN_DataFrame.DataLength", "<u1"),
        ("CAN_DataFrame.DataBytes", "(64,)u1"),
        ("CAN_DataFrame.Dir", "<u1"),
        ("CAN_DataFrame.EDL", "<u1"),
        ("CAN_DataFrame.BRS", "<u1"),
        ("CAN_DataFrame.ESI", "<u1"),
    ]
)

# ACQ_SOURCE = SourceInformation(source_type=SOURCE_BUS, bus_type=BUS_TYPE_CAN, flags=FLAG_CG_BUS_EVENT)
ACQ_SOURCE = SourceInformation(source_type=SOURCE_BUS, bus_type=BUS_TYPE_CAN)


class Message:
    def __init__(self, timestamp, record: HrlV5Parser.CanFrame):
        self.timestamp = timestamp
        self.channel = record.bus_id.value + 1  # 0 refers to any bus in asammdf, so add 1
        self.arbitration_id = record.arb_id
        self.dlc = record.dlc
        self.data = [int(d) for d in record.data]


class MDFWriter:
    def __init__(self, out_file: str | os.PathLike, database: str | os.PathLike = None, compression_level: int = 2):
        self.file = out_file
        self._mdf = cast(MDF4, MDF(version="4.10"))
        self._compression_level = compression_level
        self.max_timestamp = 0

        if database:
            database = Path(database).resolve()
            if database.exists():
                data = database.read_bytes()
                attachment = data, database.name, md5(data).digest()
            else:
                attachment = None
        else:
            attachment = None

        self._mdf.append(
            Signal(
                name="CAN_DataFrame",
                samples=np.array([], dtype=STD_DTYPE),
                timestamps=np.array([], dtype="<f8"),  # , dtype="<f8"),
                attachment=attachment,
                source=ACQ_SOURCE,
            )
        )

        self._std_buffer = np.zeros(1, dtype=STD_DTYPE)

    def close(self) -> None:
        self._mdf.save(self.file, compression=self._compression_level)
        self._mdf.close()

    def set_start_timestamp(self, timestamp: int):
        self.start_timestamp = timestamp
        self._mdf.header.start_time = datetime.fromtimestamp(timestamp)

    def on_message_received(self, msg: Message) -> None:
        if msg.timestamp <= self.max_timestamp:
            timestamp = self.max_timestamp + 0.000001
        else:
            timestamp = msg.timestamp
        self.max_timestamp = timestamp

        size = len(msg.data)

        self._std_buffer["CAN_DataFrame.BusChannel"] = msg.channel
        self._std_buffer["CAN_DataFrame.ID"] = msg.arbitration_id
        self._std_buffer["CAN_DataFrame.IDE"] = 0
        self._std_buffer["CAN_DataFrame.Dir"] = 0  # if msg.is_rx else 1
        self._std_buffer["CAN_DataFrame.DataLength"] = size
        self._std_buffer["CAN_DataFrame.DataBytes"][0, :size] = msg.data
        self._std_buffer["CAN_DataFrame.DLC"] = msg.dlc
        self._std_buffer["CAN_DataFrame.ESI"] = 0
        self._std_buffer["CAN_DataFrame.BRS"] = 0
        self._std_buffer["CAN_DataFrame.EDL"] = 0
        # print(f"{timestamp:9.6f}")
        sigs = [(np.array([timestamp]), None), (self._std_buffer, None)]
        self._mdf.extend(0, sigs)

        # self.index += 1

        # reset buffer structure
        self._std_buffer = np.zeros(1, dtype=STD_DTYPE)


class HRLParser:
    def __init__(self, in_file):
        self._parser = HrlV5Parser.from_file(in_file)

    @staticmethod
    def verify_block(block):
        crc_calc = ~crc32(block.raw_data) & 0xFFFFFFFF
        return block.crc == crc_calc

    def get_can_frames(self) -> Message:
        # t_start = self._parser.header.start_time * 1000

        rolling_time = 0
        for block in self._parser.blocks:
            if not self.verify_block(block):
                print("CRC error, skipping block")
                continue

            for record in block.records:
                if record.end_of_block:
                    break
                if record.flags == HrlV5Parser.Record.RecordType.time:
                    rolling_time = record.payload.time_ms_from_start
                elif record.flags == HrlV5Parser.Record.RecordType.can:
                    time = rolling_time + record.time_count
                    yield Message(time / 1000, record.payload)

    # def to_mdf(self, out_file, dbcs=None):
    #     count = 0
    #     for time, frame in sorted(self.get_can_frames(), key=lambda x: x[0]):  # The HRL blocks can be out of order
    #         self.on_message_received

    #         count += 1

    # str_data = frame.data.hex()[: frame.dlc * 2].upper()
    # print(f"({time:0.6f}) can{frame.bus_id.value} {frame.arb_id:03X}#{str_data}")

    # zeros = [0] * len(timestamp)
    # samples = [bus, arb_id, zeros, dlc, dlc, data, zeros, zeros, zeros, zeros]
    # types = np.dtype(
    #     [
    #         ("CAN_DataFrame.BusChannel", "u1"),
    #         ("CAN_DataFrame.ID", "<u4"),
    #         ("CAN_DataFrame.IDE", "u1"),
    #         ("CAN_DataFrame.DLC", "u1"),
    #         ("CAN_DataFrame.DataLength", "u1"),
    #         ("CAN_DataFrame.DataBytes", "u1", (8,)),
    #         ("CAN_DataFrame.Dir", "u1"),
    #         ("CAN_DataFrame.EDL", "u1"),
    #         ("CAN_DataFrame.ESI", "u1"),
    #         ("CAN_DataFrame.BRS", "u1"),
    #     ]
    # )

    # mdf = MDF()
    # sig = Signal(
    #     samples=np.core.records.fromarrays(samples, dtype=types),
    #     timestamps=np.array(timestamp, dtype="<f8"),
    #     name="CAN_DataFrame",
    #     comment="CAN_DataFrame",
    #     flags=BUS_TYPE_CAN,
    #     source=ACQ_SOURCE,
    # )

    # source = SourceInformation(source_type=SOURCE_BUS, bus_type=BUS_TYPE_CAN, flags=FLAG_CG_BUS_EVENT)
    # mdf.append([sig], acq_source=source)
    # mdf.groups[0].channel_group.flags = FLAG_CG_BUS_EVENT

    # mdf.export("csv", "/media/projects/hrl5_.txt")
    # mdf.save(out_file, overwrite=True)

    # if dbcs:
    #     mdf = mdf.extract_bus_logging(database_files=dbcs)
    #     mdf.save(out_file, overwrite=False)

    # return mdf


if __name__ == "__main__":
    args = ArgumentParser()
    args.add_argument("hrl_path", type=Path, help="Path to HRL file")
    args.add_argument("out_path", type=Path, help="Path to output file")
    args = args.parse_args()

    if not args.hrl_path.exists() or not args.hrl_path.is_file():
        print("File not found, exiting")
        exit(1)

    parser = HRLParser(args.hrl_path)
    mdfwriter = MDFWriter(args.out_path)

    print(len([frame.timestamp for frame in parser.get_can_frames()]))
    print(parser._parser.header.start_time)

    mdfwriter.set_start_timestamp(parser._parser.header.start_time)
    for can_frame in sorted(parser.get_can_frames(), key=lambda x: x.timestamp):  # The HRL blocks may be out of order
        mdfwriter.on_message_received(can_frame)

        # str_data = "".join([f"{d:02X}" for d in can_frame.data])
        # print(f"{can_frame.timestamp:0.6f} can{can_frame.channel} {can_frame.arbitration_id:03X}#{str_data}")

    print("finished adding can frames. Saving to csv...")
    mdfwriter._mdf.export("csv", "/media/projects/hrl5_.csv")
    print("Saved to csv! Closing...")
    mdfwriter.close()
    print("Closed!")

    # a = 1

    # databases = {
    #     "CAN": [
    #         ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_VEH.compact.dbc", 1),
    #         ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_PARTY.compact.dbc", 2),
    #         ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_CH.compact.dbc", 3),
    #     ]
    # }
