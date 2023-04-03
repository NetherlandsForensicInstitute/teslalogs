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
from asammdf.blocks.v4_constants import BUS_TYPE_CAN, SOURCE_BUS

# unsilence command-line output
sys.stdout, sys.stderr = sys.__stdout__, sys.__stderr__

from teslalogs.model_3.HRL.hrl_parser import HrlParser

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

ACQ_SOURCE = SourceInformation(source_type=SOURCE_BUS, bus_type=BUS_TYPE_CAN)


class Message:
    def __init__(self, timestamp, record: HrlParser.CanFrame):
        self.timestamp = timestamp
        self.channel = record.bus_id.value + 1  # in asammdf 0 refers to any bus, so add 1
        self.arbitration_id = record.arb_id
        self.dlc = record.dlc
        self.data = [int(d) for d in record.data]
        self.size = len(self.data)


class MDFWriter:
    def __init__(self, compression_level: int = 2):
        # self.file = out_file
        self._mdf = cast(MDF4, MDF(version="4.10"))
        self._compression_level = compression_level
        self.max_timestamp = 0

        self._mdf.append(
            Signal(
                name="CAN_DataFrame",
                samples=np.array([], dtype=STD_DTYPE),
                timestamps=np.array([], dtype="<f8"),
                source=ACQ_SOURCE,
            )
        )

        self._std_buffer = np.zeros(1, dtype=STD_DTYPE)

    def close(self) -> None:
        self._mdf.close()

    def save(self, file_name: str | os.PathLike) -> None:
        self._mdf.save(file_name, compression=self._compression_level)

    def set_start_timestamp(self, timestamp: int):
        self.start_timestamp = timestamp
        self._mdf.header.start_time = datetime.fromtimestamp(timestamp)

    def on_message_received(self, msg: Message) -> None:
        # TODO batch storing of messages to MDF (to speed things up)

        if msg.timestamp <= self.max_timestamp:
            timestamp = self.max_timestamp + 0.000001
        else:
            timestamp = msg.timestamp
        self.max_timestamp = timestamp

        self._std_buffer["CAN_DataFrame.BusChannel"] = msg.channel
        self._std_buffer["CAN_DataFrame.ID"] = msg.arbitration_id
        self._std_buffer["CAN_DataFrame.IDE"] = 0
        self._std_buffer["CAN_DataFrame.Dir"] = 0  # if msg.is_rx else 1
        self._std_buffer["CAN_DataFrame.DataLength"] = msg.size
        self._std_buffer["CAN_DataFrame.DataBytes"][0, : msg.size] = msg.data
        self._std_buffer["CAN_DataFrame.DLC"] = msg.dlc
        self._std_buffer["CAN_DataFrame.ESI"] = 0
        self._std_buffer["CAN_DataFrame.BRS"] = 0
        self._std_buffer["CAN_DataFrame.EDL"] = 0

        sigs = [(np.array([timestamp]), None), (self._std_buffer, None)]
        self._mdf.extend(0, sigs)

        # reset buffer structure
        self._std_buffer = np.zeros(1, dtype=STD_DTYPE)

    def extract_logging(self, dbc):
        if dbc:
            can_dbc = {"CAN": dbc}
            self._mdf = self._mdf.extract_bus_logging(database_files=can_dbc)


class HRL:
    def __init__(self, in_file):
        self._parser = HrlParser.from_file(in_file)

    @staticmethod
    def verify_block(block):
        crc_calc = ~crc32(block.as_raw_records) & 0xFFFFFFFF
        return block.crc == crc_calc

    def get_can_frames(self) -> Message:
        # TODO switch to vectorised parsing of frames (to speed things up)

        rolling_time = 0
        for i, block in enumerate(self._parser.blocks):
            if not block.valid:
                continue

            if not self.verify_block(block):
                print(f"CRC error in block {i}! Skipping block.")
                continue

            for record in block.records:
                if record.end_of_block:
                    break
                if record.flags == HrlParser.Record.RecordType.time:
                    rolling_time = record.payload.time_ms_from_start
                elif record.flags == HrlParser.Record.RecordType.can:
                    time = rolling_time + record.time_count
                    yield Message(time / 1000, record.payload)


if __name__ == "__main__":
    args = ArgumentParser()
    args.add_argument("hrl_path", type=Path, help="Path to HRL file")
    args.add_argument("out_path", type=str, help="Path to output file")
    args.add_argument(
        "-d", "--dbc", action="append", nargs=2, metavar=("path", "channel"), help="CAN database files and channel"
    )
    args = args.parse_args()

    if not args.hrl_path.exists() or not args.hrl_path.is_file():
        print(f"HRL file {args.hrl_path} not found, exiting")
        exit(1)

    # parse HRL
    print("Parsing HRL...", end="\r")
    hrl = HRL(args.hrl_path)
    print("HRL parsed!   ")

    # write CAN frames to MF4
    print("Saving to MF4...", end="\r")
    mdfwriter = MDFWriter()
    mdfwriter.set_start_timestamp(hrl._parser.header.start_timestamp)
    for can_frame in sorted(hrl.get_can_frames(), key=lambda x: x.timestamp):  # The HRL blocks may be out of order
        mdfwriter.on_message_received(can_frame)

    if args.dbc:
        for i in range(len(args.dbc)):
            path, channel = args.dbc[i]
            args.dbc[i] = [Path(path), int(channel) + 1]
            if not args.dbc[i][0].exists() or not args.dbc[i][0].is_file():
                print(f"DBC file {args.dbc[i][0]} not found, exiting")
                exit(1)

        # extract logging with dbc(s)
        mdfwriter.extract_logging(args.dbc)

    mdfwriter.save(args.out_path)
    print(f"Saved to MF4!   ")

    mdfwriter.close()
