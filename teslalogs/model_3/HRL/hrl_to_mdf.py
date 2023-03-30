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
                timestamps=np.array([], dtype="<f8"),
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

        sigs = [(np.array([timestamp]), None), (self._std_buffer, None)]
        self._mdf.extend(0, sigs)

        # reset buffer structure
        self._std_buffer = np.zeros(1, dtype=STD_DTYPE)


class HRL:
    def __init__(self, in_file):
        self._parser = HrlParser.from_file(in_file)

    @staticmethod
    def verify_block(block):
        crc_calc = ~crc32(block.as_raw_records) & 0xFFFFFFFF
        return block.crc == crc_calc

    def get_can_frames(self) -> Message:
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
    args.add_argument("out_path", type=Path, help="Path to output file")
    args = args.parse_args()

    if not args.hrl_path.exists() or not args.hrl_path.is_file():
        print("File not found, exiting")
        exit(1)

    hrl = HRL(args.hrl_path)
    mdfwriter = MDFWriter(args.out_path)

    # print(len([frame.timestamp for frame in hrl.get_can_frames()]))
    # print(hrl._parser.header.start_timestamp)

    mdfwriter.set_start_timestamp(hrl._parser.header.start_timestamp)
    for can_frame in sorted(hrl.get_can_frames(), key=lambda x: x.timestamp):  # The HRL blocks may be out of order
        mdfwriter.on_message_received(can_frame)

        # str_data = "".join([f"{d:02X}" for d in can_frame.data])
        # print(f"{can_frame.timestamp:0.6f} can{can_frame.channel} {can_frame.arbitration_id:03X}#{str_data}")

    print("finished adding can frames. Saving and closing...")
    mdfwriter.close()

    # databases = {
    #     "CAN": [
    #         ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_VEH.compact.dbc", 1),
    #         ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_PARTY.compact.dbc", 2),
    #         ("/media/projects/Tesla_HRL/dbcs/Model3_dbcs/Model3_CH.compact.dbc", 3),
    #     ]
    # }
