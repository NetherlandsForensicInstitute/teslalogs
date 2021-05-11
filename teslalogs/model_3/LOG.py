import numpy as np
import pandas as pd
from teslalogs.utils import shift_mask

record = np.dtype([('flag_counter', '>u2'),
                   ('bus_len_id', '>u2'),
                   ('data', '<u8'),
                   ('check', '>u1')])


def verify(records):
    # Sum of all bytes of each record mod 256 must be 0 (simple checksum byte at the end)
    raw = records.view('u1')
    raw = raw.reshape(len(records), record.itemsize)
    verified = np.sum(raw, axis=1, dtype='u1') == 0
    return records[verified]


def parse_file(file):
    records = np.fromfile(file, dtype=record)
    records = verify(records)
    df = pd.DataFrame(records)

    counter = shift_mask(df['flag_counter'], 0, 12)
    flag = shift_mask(df['flag_counter'], 12, 4)

    is_rolling_time = (flag == 8)
    timestamps = shift_mask(df['data'][is_rolling_time].view('>u8'), 32, 32)
    timestamps = timestamps.astype('datetime64[s]') + counter[is_rolling_time].astype('timedelta64[ms]')
    timestamps = timestamps.reindex(df.index, method='ffill')
    timestamps += counter.astype('timedelta64[ms]')

    arbitration_id = shift_mask(df['bus_len_id'], 0, 11)
    dlc = shift_mask(df['bus_len_id'], 11, 3) + 1
    bus = shift_mask(df['bus_len_id'], 14, 2)
    df = pd.DataFrame({'timestamp': timestamps,
                       'channel': bus,
                       'arbitration_id': arbitration_id,
                       'dlc': dlc,
                       'data': df['data']})
    return df.loc[flag == 0]  # only return valid CAN frames

