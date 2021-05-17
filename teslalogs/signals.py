import can
import pandas as pd
import numpy as np
from collections import namedtuple
import param
import panel as pn
import holoviews as hv

can_message = namedtuple('can_message', 'timestamp channel arbitration_id dlc data')

def readCanUtilsLog(file):
    for msg in can.io.CanutilsLogReader(file):
        data = int.from_bytes(msg.data, 'little', signed=False)
        yield can_message(msg.timestamp,
                          msg.channel,
                          msg.arbitration_id,
                          msg.dlc,
                          data)


def can_to_df(msgs):
    columns = can_message._fields
    df = pd.DataFrame(msgs, columns=columns).astype({'arbitration_id': 'int32',
                                                     'dlc': 'int8',
                                                     'data': 'uint64'})
    return df


def save_df(df, filename, key):
    with pd.HDFStore(filename, append=True) as store:
        if key in store:
            raise ValueError
        store.append(f'/{key}', df, format='table', data_columns=['channel', 'arbitration_id'])



def bit_numbering_invert(b):
    """
    Convert between lsb0 and msb0 CAN dbc numbering.
    This operation is symmetric.
    Reference: https://github.com/ebroecker/canmatrix/wiki/signal-Byteorder
    :param b: bit number
    :return: inverted bit number
    """
    return b - (b % 8) + 7 - (b % 8)


def msbit2lsbit(b, length):
    """
    Convert from lsbit of signal data to msbit of signal data, when bit numbering is msb0
    Reference: https://github.com/ebroecker/canmatrix/wiki/signal-Byteorder
    :param b: msbit in msb0 numbering
    :param length: signal length in bits
    :return: lsbit in msb0 numbering
    """
    return b + length - 1

def extract_sig(data, startbit, length, endian, signed, is_float=False):
    """
    Extract the raw signal value from a CAN message given the dbc startbit, length and endianess.
    DBC bit numbering makes sense for little_endian: 0-63, the startbit is the lsb
    For big_endian, the start bit is the msb, but still using the lsb numbering ... which is messed up
    After accounting for the numbering, we can extract the signals using simple bit-shift and masks
    Kvaser DB editor says start-bit is the lsbit, inconsistent with DBC 'spec'.
    :param data: full 64 bit CAN payload
    :param startbit: dbc signal startbit
    :param length: dbc signal length in bits
    :param endian: 'big_endian' or 'little_endian'
    :param signed: dbc signal sign (True if signed)
    :param is_float: dbc signal is float
    :return: raw integer signal value
    """
    mask = 2 ** length - 1
    if endian == 'big_endian':
        # Using msb numbering (msb = 0)
        start = bit_numbering_invert(startbit)
        shiftcount = 63 - msbit2lsbit(start, length)
    else:
        shiftcount = startbit
    shifted = np.right_shift(data, shiftcount)
    val = np.bitwise_and(shifted, mask)
    if is_float:
        assert length == 32, 'Invalid float length'
        val = val.astype('uint32')
        return val.view('f4')
    if signed:
        tmp = val[val >= 2**(length - 1)].copy()
        tmp = -1 * (((tmp ^ mask) + 1) & mask).astype('int64')
        val = val.astype('int64')
        val[val >= 2 ** (length - 1)] = tmp
    return val


class DecoderDict(dict):
    # Simple dictionary subclass to decode signal enum values and handle missing values
    def __missing__(self, key):
        return str(key)


def decode_id_vectorized(df, dbc, ID, choice=True):
    """
    Vectorized message decoder, decodes all signals in a dbc message
    :param df: pandas DataFrame with columns like can_message namedtuple
    :param dbc: cantools Database object
    :param ID: Message arbitration_id
    :param choice: decode raw values to signal choices or ont
    :return: pandas DataFrame with decoded values
    """
    msg = dbc.get_message_by_frame_id(ID)
    if not msg:
        raise KeyError(f'ID: {ID} not in dbc')
    tmp = df[df['arbitration_id'] == ID]

    if msg.is_multiplexed():
        muxers = [s for s in msg.signals if s.is_multiplexer]
        assert len(muxers) == 1, 'Only supports single multiplexer for now!'
        return decode_mux(tmp, msg, choice=choice)

    out = dict()
    raw = tmp['data'].copy().values
    for signal in msg.signals:
        sig = decode_signal(raw, signal, choice=choice)
        out[signal.name] = sig
    decoded = pd.DataFrame(out).set_index(tmp.index)
    decoded[['timestamp', 'channel']] = tmp[['timestamp', 'channel']]
    return decoded


def decode_mux(df, msg, choice=True):
    mux = [s for s in msg.signals if s.is_multiplexer][0]
    out = dict()
    empty_num = np.empty((len(df),))
    empty_str = pd.Series(np.empty((len(df),), dtype=np.object))
    empty_num[:] = np.nan
    empty_str[:] = None
    raw = df['data'].copy().values

    mux_sig = decode_signal(raw, mux, choice=False)
    tree = msg.signal_tree[0][mux.name]
    for mux_val in [int(v) for v in mux_sig.unique()]:
        mux_sigs = tree[mux_val]
        mux_idx = (mux_sig == mux_val)
        for signal in mux_sigs:
            signal = msg.get_signal_by_name(signal)
            if choice and signal.choices and not just_SNA(signal):
                empty = empty_str.copy()
            else:
                empty = empty_num.copy()
            sig_out = empty
            sig = decode_signal(raw, signal, choice=choice)
            sig_out[mux_idx] = sig[mux_idx]
            out[signal.name] = sig_out
    if len(msg.signal_tree) > 1:
        for s in msg.signal_tree[1:]:
            out[s] = decode_signal(raw, msg.get_signal_by_name(s), choice=choice)
    out[mux.name] = decode_signal(raw, mux, choice=choice)
    decoded = pd.DataFrame(out)
    decoded.index = df.index
    decoded[['timestamp', 'channel']] = df[['timestamp', 'channel']]
    return decoded


def just_SNA(signal):
    out = False
    if signal.choices and (len(signal.choices) == 1) and any('SNA' in v for v in signal.choices.values()):
        out = True
    return out


def decode_signal(raw, signal, choice=True):
    endian = signal.byte_order
    if endian == 'big_endian':
        raw = raw.view('>Q')
    else:
        raw = raw.view('<Q')
    sig = extract_sig(raw, signal.start, signal.length, signal.byte_order, signal.is_signed, signal.is_float)
    if choice and signal.choices and not just_SNA(signal):
        return pd.Series(sig).map(DecoderDict(signal.choices))
    return pd.Series(sig * signal.scale + signal.offset)


def decode_log_signal(raw, mapped_sig, choice=True):
    endian = mapped_sig.byte_order
    if endian == 'big_endian':
        sig = raw.copy().view(f'>u{raw.dtype.itemsize}').astype('float64')
    else:
        sig = raw.copy().view(f'<u{raw.dtype.itemsize}').astype('float64')
    if choice and mapped_sig.choices and not just_SNA(mapped_sig):
        return pd.Series(sig).map(DecoderDict(mapped_sig.choices))
    return pd.Series(sig * mapped_sig.scale + mapped_sig.offset)


def guess_signal_sign_length(signal, length=None, threshold=0.9):
    if signal.min() < 0:
        # Already a signed signal
        return True, length
    sign_df = pd.DataFrame((2 ** i for i in range(64)), columns=['max_val'])
    diffs = signal.astype('int64').diff()
    sign_df['overflow'] = diffs.min() <= sign_df['max_val'] * threshold * -1
    sign_df['underflow'] = diffs.max() >= sign_df['max_val'] * threshold
    sign_df['max_fits'] = signal.max() <= sign_df['max_val']
    if not length:
        length = sign_df[sign_df['max_fits']].index[0]
    signed = False
    length = length + 1 if not length else length  # Length 0 will not play nice with extract_sig later on
    if sign_df['overflow'].loc[length] & sign_df['underflow'].loc[length]:
        signed = True
    return signed, length



class SignalViewer(param.Parameterized):
    # Simple signal viewer using Param, Panel and Holoviews to be displayed in a jupyter notebook
    message = param.ObjectSelector()
    signal = param.ObjectSelector()

    def __init__(self, df, dbc, plot_type='Curve', choice=True, **params):
        super().__init__(**params)
        self.df = df
        self.dbc = dbc
        self.choice = choice
        self.plot_type = plot_type
        ids_in_dbc = {x.frame_id for x in dbc.messages}
        ids_in_log = set(df['arbitration_id'].unique())
        common_ids = ids_in_dbc.intersection(ids_in_log)
        decodable = {m.name: m for m in filter(lambda x: x.frame_id in common_ids, dbc.messages)}
        self._messages = list(sorted(decodable.keys(), key=lambda x: self.dbc.get_message_by_name(x).frame_id))
        self._signals = {msg.name: [sig.name for sig in msg.signals] for msg in
                         (dbc.get_message_by_frame_id(int(ID)) for ID in common_ids)}
        self._data = decode_id_vectorized(df, dbc, dbc.get_message_by_name(self._messages[0]).frame_id)
        self.param['message'].objects = self._messages
        self.message = self._messages[0]
        self.param['signal'].objects = self._signals[self.message]
        self.signal = self._signals[self.message][0]
        self.text_widget = pn.pane.Markdown()

    @param.depends('message', watch=True)
    def _update_signals(self):
        signals = self._signals[self.message]
        self._data = decode_id_vectorized(self.df, self.dbc, self.dbc.get_message_by_name(self.message).frame_id, choice=self.choice)
        signals = [s for s in signals if s in self._data.columns]
        self.param['signal'].objects = signals
        self.signal = signals[0]

    @param.depends('signal')
    def update_plot(self):
        data = self._data.loc[self._data[self.signal].notna()]
        data['channel'] = data['channel'].astype(str)
        if self.plot_type == 'Curve':
            interpolation = 'steps-post' if pd.api.types.is_string_dtype(data[self.signal]) else 'linear'
            plot = hv.Curve(data, 'timestamp', [self.signal, 'channel'], label=self.signal).opts(interpolation=interpolation)
        elif self.plot_type == 'Scatter':
            plot = hv.Scatter(data, 'timestamp', [self.signal, 'channel']).opts(color='channel', cmap='Dark2')
        else:
            raise ValueError('Invalid plot type given!')
        self.text_widget.object = f'''Copy this and call it on the viewer to get the plot:
                                    \n\n\t.get_plot("{self.message}", "{self.signal}")'''
        return plot.opts(width=1000, height=600)

    def get_plot(self, msg, sig):
        self.message = msg
        self.signal = sig
        return self.update_plot()

    def nbview(self):
        return pn.Row(pn.Column(self.param, self.text_widget), self.update_plot)



class ModelSXLogviewer(param.Parameterized):
    # Simple signal viewer using Param, Panel and Holoviews to be displayed in a jupyter notebook
    # Based on: https://panel.holoviz.org/user_guide/Param.html
    signal = param.ObjectSelector()
    force_line_plot = param.Boolean(False)  # Sometimes a single or few choice values mess up a line plot
    force_steps_plot = param.Boolean(False)  # Sometimes a binary signal looks better this way

    def __init__(self, storepath, matches, plot_type='Curve', **params):
        super().__init__(**params)
        self.storepath = storepath
        self.matches = matches
        self.plot_type = plot_type
        with pd.HDFStore(storepath) as store:
            logged_ids = {x[2:] for x in store.keys()}  # Cut of leading '/_'
        matched_log_ids = set(matches.keys())
        log_ids = list(sorted(logged_ids & matched_log_ids))
        objects = [self.pretty_match(self.matches, log_id) for log_id in log_ids]
        self.param['signal'].objects = objects
        self.signal = objects[0]
        self.text_widget = pn.pane.Markdown()

    @staticmethod
    def pretty_match(matches, log_id):
        match = matches[log_id]
        return f'{log_id}_{match.bus}_{match.message}_{match.signal}'

    @param.depends('force_line_plot', 'force_steps_plot', 'signal')
    def update_plot(self):
        log_id = self.signal.split('_')[0]
        with pd.HDFStore(self.storepath) as store:
            df = store[f'_{log_id}']
        match = self.matches[log_id]
        val = decode_log_signal(df['value'], match, choice=(True and not self.force_line_plot))
        df[match.signal] = val

        interpolation = 'steps-post' if (pd.api.types.is_string_dtype(val) or self.force_steps_plot) else 'linear'
        unit = f' [{match.unit}]' if match.unit else ''

        if self.plot_type == 'Curve' or self.force_line_plot:
            plot = hv.Curve(df, 'timestamp', match.signal).opts(interpolation=interpolation,
                                                                title=f'{log_id}_{match.bus}_{match.message}_{match.signal} {unit}')
        elif self.plot_type == 'Scatter':
            plot = hv.Scatter(df, 'timestamp', match.signal).opts(interolationp=interpolation,
                                                                  title=f'{log_id}_{match.bus}_{match.message}_{match.signal} {unit}')
        else:
            raise ValueError('Invalid plot type given!')
        self.text_widget.object = f'''Copy this and call it on the viewer to get the plot:
                                    \n\n\t.get_plot("{log_id}")'''
        return plot.opts(width=1000, height=600)


    def get_plot(self, signal):
        log_id = signal.split('_')[0]
        objects = self.param['signal'].objects
        candidate = list(filter(lambda x: x.startswith(log_id), objects))
        if candidate:
            self.signal = candidate[0]
            return self.update_plot()
        return None

    def nbview(self):
        return pn.Row(pn.Column(self.param, self.text_widget), self.update_plot)

