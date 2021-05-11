import numpy as np
import pandas as pd
from .utils import shift_mask

record = np.dtype([('timestamp', '<u4'),
                   ('pad0', '<u4'),
                   ('ns', '<u4'),
                   ('pad1', '<u4'),
                   ('ID', '<u2'),
                   ('len_bus', '<u1'),
                   ('data', '<u8'),
                   ('pad2', '<u1')])


def parse_file(file):
    records = np.fromfile(file, dtype=record)
    df = pd.DataFrame(records)
    length = shift_mask(df['len_bus'], 4, 4)
    bus = shift_mask(df['len_bus'], 0, 4)
    timestamp = df['timestamp'] + df['ns'] / 1e9

    df = pd.DataFrame({'timestamp': timestamp,
                       'channel': bus,
                       'arbitration_id': df['ID'],
                       'dlc': length,
                       'data': df['data']})
    return df
