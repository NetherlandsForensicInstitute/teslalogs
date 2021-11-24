import struct
import zlib
import pandas as pd
import numpy as np
from tqdm import tqdm
from teslalogs.utils import shift_mask

record = np.dtype([('flag_counter', '>u1'),
                   ('bus_dlc_id', '>u2'),
                   ('data', '<u8')])
rolling_timer = np.dtype([('startpadding', 'V1'),
                          ('milliseconds', '>u4'),
                          ('endpadding', 'V6')])
RECORD_SIZE = record.itemsize


def verify(block):
    blocksize = len(block)
    crc_pos = blocksize - (blocksize % RECORD_SIZE)
    tail_bytes = block[crc_pos:]
    num_tail_bytes = len(tail_bytes) - 4
    crc_tail = struct.unpack(">I", tail_bytes[:4])[0]
    crc = ~zlib.crc32(block[:crc_pos]) & 0xffffffff
    if crc != crc_tail:
        raise ValueError("bad crc")
    if tail_bytes[4:] not in [b'\xff' * num_tail_bytes, b'\x00' * num_tail_bytes]:
        raise ValueError("final byte(s) should be ff or 00")
    return crc_pos


def get_records(block):
    try:
        crc_pos = verify(block)
    except ValueError:
        # print('CRC fail')
        return None
    records = np.frombuffer(block[:crc_pos], record)
    # Discard after flag 0xC
    discarded = np.where(records['flag_counter'] == 0xC0)
    if np.any(discarded):
        records = records[:discarded[0][0]]
    return records


def build_can_df(records, starttime):
    df = pd.DataFrame(records)
    counter = shift_mask(df['flag_counter'], 0, 6)
    istimer = df['flag_counter'] == 0x40
    timer_index = df[istimer].index
    rolling_time = records.view(rolling_timer)[istimer]['milliseconds']
    rolling_time = pd.Series(rolling_time, index=timer_index).reindex(df.index, method='ffill')
    timestamp = pd.Series(starttime, index=df.index)
    timestamp = (timestamp.astype('datetime64[s]') +
                 rolling_time.astype('timedelta64[ms]') +
                 counter.astype('timedelta64[ms]'))

    arbitration_id = shift_mask(df['bus_dlc_id'], 0, 11)
    dlc = shift_mask(df['bus_dlc_id'], 11, 3) + 1
    bus = shift_mask(df['bus_dlc_id'], 14, 2)

    df = pd.DataFrame({'timestamp': timestamp,
                       'channel': bus,
                       'arbitration_id': arbitration_id,
                       'dlc': dlc,
                       'data': records['data']})
    df = df.drop(timer_index)
    return df


def parse_file(file):
    blockrecords = []
    assert file.stat().st_size % 0x4000 == 0, f'Corrupt file, incorrect size: {file.stat().st_size}'
    blockno = 1
    block_size = 0x4000
    with open(file, 'rb') as f:
        block = f.read(block_size)
        header_fmt = '>B20s17s3xI'
        version, git_hash, vin, t_start = struct.unpack(header_fmt, block[:struct.calcsize(header_fmt)])
        assert version in range(5), 'Have not seen this format yet'
        if version >= 2:
            block_size = 0x8000
        f.seek(block_size, 0)
        while True:
            block = f.read(block_size)
            blockno += 1
            if not block:
                break
            records = get_records(block)
            if records is None:
                pass
            else:
                blockrecords.append(records)
    if not blockrecords:
        return pd.DataFrame()
    records = np.concatenate(blockrecords, axis=0)
    df = build_can_df(records, t_start)
    return df


def parse_files(files):
    for f in tqdm(files):
        yield parse_file(f)


def parse_HRLs(target_dir):
    files = [file for file in target_dir.glob('*.HRL') if 'CUR' not in file.name.upper()]
    hrls = parse_files(files)
    return pd.concat(hrls, ignore_index=True) #.sort_values('timestamp').reset_index()
