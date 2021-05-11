import can
import json
import cantools
import numpy as np
import pandas as pd
from pathlib import Path
from itertools import chain
from collections import namedtuple

can_message = namedtuple('can_message', 'channel timestamp arbitration_id dlc data')

def read_dbc(file):
    return cantools.db.load_file(file)

def shift_mask(data, shiftbits, maskbits):
    """
    Vectorized bit masking to extract bitfields.
    :param data: numpy array of integers
    :param shiftbits: number of bits to shift right
    :param maskbits: number of bits to mask after shifting
    :return: Shifted and masked bitfield
    """
    shifted = np.right_shift(data, shiftbits)
    out = np.bitwise_and(shifted, 2**maskbits - 1)
    return out


def gen_nodes(bus_json):
    for msg_name, msg in bus_json['messages'].items():
        yield msg['senders']
        for sig_name, json_sig in msg['signals'].items():
            yield json_sig['receivers']


def gen_dbc_messages(bus_json):
    for msg_name, msg in bus_json['messages'].items():
        muxers = [k for k, v in msg['signals'].items() if 'is_muxer' in v]
        muxer = muxers[0] if muxers else None
        signals = [cantools.db.Signal(name=sig_name,
                                      start=json_sig['start_position'],
                                      length=json_sig['width'],
                                      byte_order='little_endian' if json_sig[
                                                                        'endianness'] == 'LITTLE' else 'big_endian',
                                      is_signed=json_sig['signedness'] == 'SIGNED',
                                      initial=json_sig['start_value'] if 'start_value' in json_sig else None,
                                      scale=json_sig['scale'],
                                      offset=json_sig['offset'],
                                      minimum=json_sig['min'],
                                      maximum=json_sig['max'],
                                      unit=json_sig['units'],
                                      choices={v: k for k, v in json_sig[
                                          'value_description'].items()} if 'value_description' in json_sig else None,
                                      receivers=[x.lower() for x in json_sig['receivers']],
                                      is_multiplexer=json_sig['is_muxer'] if 'is_muxer' in json_sig else False,
                                      multiplexer_ids=[json_sig['mux_id']] if 'mux_id' in json_sig else None,
                                      multiplexer_signal=muxer if 'mux_id' in json_sig else None,
                                      )
                   for sig_name, json_sig in msg['signals'].items()]
        failed = False
        try:
            dbc_msg = cantools.db.Message(frame_id=msg['message_id'],
                                          name=msg_name,
                                          length=msg['length_bytes'],
                                          signals=signals,
                                          senders=[x.lower() for x in msg['senders']],
                                          cycle_time=msg['cycle_time'],
                                          is_extended_frame=False,
                                          strict=True
                                          ) #send_type=msg['send_type'],
            yield dbc_msg
        except cantools.db.Error as e:
            print(e)
            failed = True
        if failed:
            dbc_msg = cantools.db.Message(frame_id=msg['message_id'],
                                          name=msg_name,
                                          length=msg['length_bytes'],
                                          signals=signals,
                                          senders=[x.lower() for x in msg['senders']],
                                          cycle_time=msg['cycle_time'],
                                          is_extended_frame=False,
                                          strict=False
                                          )#send_type=msg['send_type'],
            yield dbc_msg


def json2dbc(json_file):
    bus_json = json.loads(json_file.read_text())
    print(bus_json['busMetadata'])
    msgs = [msg for msg in gen_dbc_messages(bus_json)]
    nodes = [cantools.db.Node(n, '') for n in set(x.lower() for x in chain(*gen_nodes(bus_json)))]
    db = cantools.db.Database(msgs, nodes=nodes)
    return db, bus_json['busMetadata']['id']


def read_jsons(dej_path):
    dbcs = dict()
    for file in dej_path.glob('*.json'):
        if 'DBG' in file.name:  # This will override our dict value for the full PT dbc :(
            continue
        print(f'Reading {file.name}...')
        dbc, bus_id = json2dbc(file)
        out_path = Path('/tmp/') / (file.stem + '.dbc')
        out_path.write_text(dbc.as_dbc_string())
        dbcs[bus_id] = dbc
    return dbcs


def read_log(file):
    msgs = [m for m in can.CanutilsLogReader(file)]
    df = pd.DataFrame(can_message(m.channel, m.timestamp, m.arbitration_id, m.dlc,
                                  np.frombuffer(m.data + bytearray([0] * (8 - m.dlc)), '<u8')[0]) for m in msgs)
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='s')
    return df
