import re
import struct
import pandas as pd
import numpy as np
from argparse import ArgumentParser
from pathlib import Path
from tqdm import tqdm
from collections import namedtuple
from datetime import datetime, timedelta
from model_sx_log import ModelSxLog
from kaitaistruct import KaitaiStream, BytesIO, ValidationNotEqualError

TIMESTAMP_IDS = (0xd00007dd, 0xd00007de)   # these id's update the rolling timestamp
HEADER_PAT = re.compile(b'\xd0\x00\x07\xde', re.MULTILINE)
agg_descriptor = namedtuple('periodicEntry', 'ID unknown size')
dataPoint = namedtuple('dataPoint', 'timestamp ID value')
MAX_LEN = 50000


def read_entries(data, start_offset=0):
    # Inspired by: https://stackoverflow.com/questions/49699820/parsing-binary-messages-with-kaitai-struct-python
    stream = KaitaiStream(BytesIO(data))
    stream.seek(start_offset)
    last = stream.pos()
    start = ModelSxLog(stream)
    log_entry = start.log_entry
    yield log_entry
    n_entries = 1
    with tqdm(total=stream.size() - start_offset, unit='B',
              unit_scale=True, desc='Processing log') as pbar:
        while not stream.is_eof():
            if n_entries % 1000 == 0:
                consumed = stream.pos() - last
                pbar.update(consumed)
                last = stream.pos()
            try:
                log_entry = ModelSxLog.Entry(stream, _root=start._root)
                if sum(log_entry.raw_bytes) % 256 != 0:
                    print(f'Checksum error at {stream.pos()}, seeking to the next entry...')
                    stream.read_bytes_term(0xaa, include_term=False, consume_term=False, eos_error=True)
                else:
                    yield log_entry
            except ValidationNotEqualError:
                print(f'Encountered an error at {stream.pos()}, probably a corrupt entry, seeking to next one...')
                stream.read_bytes_term(0xaa, include_term=False, consume_term=False, eos_error=True)
                pass
            n_entries += 1
        pbar.update(stream.pos() - last)
        stream.close()


def process_log(data,
                dt_min=None,
                dt_max=None,
                start_offset=0):
    agg_descriptors = dict()
    rollingTime = datetime.utcfromtimestamp(0)     # init rolling time

    for entry in read_entries(data, start_offset=start_offset):
        if entry.is_on_change and entry.body.sig_id in TIMESTAMP_IDS:
            rollingTime = datetime.utcfromtimestamp(struct.unpack('>L', entry.body.value[:4])[0])
            millis = struct.unpack('>H', entry.body.value[4:6])[0]
            rollingTime += timedelta(seconds=millis / 1000)
        timestamp = rollingTime + timedelta(seconds=entry.counter / 1000.0)
        if dt_max and timestamp >= dt_max:
            print('Reached end timestamp, stop processing', flush=True)
            break

        if not entry.is_on_change:
            if entry.body.is_descriptor:
                agg_id = entry.body.aggregate_body.aggregate_id
                agg_descriptors[agg_id] = [agg_descriptor(desc.sig_id, desc.unknown, desc.size)
                                           for desc in entry.body.aggregate_body.descriptors]
            else:
                if timestamp <= dt_min:
                    continue
                agg_id = entry.body.aggregate_id
                if agg_id not in agg_descriptors:
                    continue  # The descriptors are probably in a previous log file
                substream = entry.body.aggregate_body.values
                cursor = 0
                for descriptor in agg_descriptors[agg_id]:
                    yield dataPoint(timestamp, descriptor.ID, substream[cursor: cursor + descriptor.size])
                    cursor += descriptor.size
        else:
            if timestamp <= dt_min:
                continue
            yield dataPoint(timestamp, entry.body.sig_id, entry.body.value)


def process_row(d, key, max_len=50000, _cache=None, _store=None):
    """
    Append row d to the store 'key'.

    When the number of items in the key's cache reaches max_len,
    append the list of rows to the HDF5 store and clear the list.

    """
    # keep the rows for each key separate.
    lst = _cache.setdefault(key, [])
    if len(lst) >= max_len:
        store_and_clear(lst, key, _store=_store)
    lst.append(d)


def store_and_clear(lst, key, _store=None):
    """
    Convert key's cache list to a DataFrame and append that to HDF5.
    """
    key = f'/{key}'
    values = streamline_list(lst)
    if values is not None:
        df = pd.DataFrame(values)
        _store.append(key, df, format='table')
    lst.clear()


def streamline_list(lst):
    timestamps, values = zip(*lst)
    size = len(values[0])  # Implicit assumption that values are same size for each ID
    if size in (1, 2, 4, 8):
        values = np.frombuffer(b''.join(values), dtype=f'<u{size}')
    else:
        values = [x.hex() for x in values]  # at least this will be accepted for serialization in hdf5
    return {'timestamp': timestamps, 'value': values}


def binary_search_start(data, dtmin):
    hits = [hit for hit in HEADER_PAT.finditer(data)]
    low = 0
    high = len(hits) - 1
    candidate = None
    while low <= high:
        mid = (high + low) // 2
        entry_start = hits[mid].start() - 6
        dt = get_tstamp_at(data, entry_start)
        candidate = entry_start
        # go top
        if dt < dtmin:
            low = mid + 1
        # go bottom
        elif dt > dtmin:
            high = mid - 1
        else:
            return hits[mid].start() - 6
    return candidate


def get_tstamp_at(data, offset):
    stream = KaitaiStream(BytesIO(data))
    stream.seek(offset)
    entry = ModelSxLog(stream).log_entry
    dt = datetime.utcfromtimestamp(struct.unpack('>L', entry.body.value[:4])[0])
    return dt


def sort_log_files(log_path):
    logfiles = list(log_path.glob('[0-4].log'))
    if not logfiles:
        logfiles = list(log_path.glob('[0-4].LOG'))
    result = list()
    for logfile in logfiles:
        with open(logfile, 'rb') as f:
            # peek first timestamp of each
            data = f.read(100_000)
            hit = next(HEADER_PAT.finditer(data))
            dt = get_tstamp_at(data, hit.start() - 6)
            result.append((logfile, dt))
    return list(sorted(result, key=lambda x: x[1]))


def find_start_file(sorted_log_files, dtmin):
    res = 0
    for idx, (logpath, dt) in enumerate(sorted_log_files):
        if dt > dtmin:
            return idx - 1 if (idx - 1) >= res else res
    return len(sorted_log_files) - 1


def main(dtmin, dtmax, log_path, hdf_path):
    sorted_log_files = sort_log_files(log_path)
    file_idx = find_start_file(sorted_log_files, dtmin)
    data = sorted_log_files[file_idx][0].read_bytes()
    start_offset = binary_search_start(data, dtmin)

    # We used this pattern to split out timeseries:
    # https://stackoverflow.com/questions/16740887/how-to-handle-incoming-real-time-data-with-python-pandas
    cache = {}
    store = pd.HDFStore(hdf_path)

    while file_idx < len(sorted_log_files):
        print(f'Processing {sorted_log_files[file_idx][0].name}')
        for datapoint in process_log(data,
                                     dt_min=dtmin,
                                     dt_max=dtmax,
                                     start_offset=start_offset):
            process_row((datapoint.timestamp, datapoint.value),
                        key=f'_{hex(datapoint.ID)}',  # Can't have the key start with numeric value
                        _cache=cache,
                        _store=store,
                        max_len=MAX_LEN)
        file_idx += 1
        start_offset = 0
        if file_idx >= len(sorted_log_files):
            break
        data = sorted_log_files[file_idx][0].read_bytes()

    # Finalize
    for k, lst in tqdm(cache.items(), desc='Storing signals to HDF'):
        store_and_clear(lst, k, _store=store)
    store.close()


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('-dtmin',
                      help='Starting datetime in YYYY,MM,DD,HH,MM,SS format, will be passed to datetime',
                      required=True)
    args.add_argument('-dtmax',
                      help='Ending datetime in YYYY,MM,DD,HH,MM,SS format, will be passed to datetime',
                      required=True)
    args.add_argument('log_path', help='Path to SD log directory')
    args.add_argument('hdf_path', help='Path to output HDF5 file')
    args.add_argument('--force', help='Force overwriting output HDF5 file, default will not',
                      action='store_true')
    args = args.parse_args()
    dtmin = datetime(*[int(x) for x in args.dtmin.split(',')])
    dtmax = datetime(*[int(x) for x in args.dtmax.split(',')])
    log_path = Path(args.log_path)
    hdf_path = Path(args.hdf_path)

    if not log_path.exists() or not log_path.is_dir():
        print(f'Did not find log dir: {log_path}, exiting.')
        exit(1)
    if hdf_path.exists() and hdf_path.is_file():
        if args.force:
            hdf_path.unlink()
        else:
            print(f'Target HDF5 file {hdf_path} already exists, exiting.')
            exit(1)
    main(dtmin, dtmax, log_path, hdf_path)
