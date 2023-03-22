import pandas as pd
import datetime as dt
from pathlib import Path
from zlib import crc32
from teslalogs.model_3.model_3_clb import Model3Clb
from teslalogs.model_3.model_3_clh import Model3Clh
from kaitaistruct import KaitaiStream, BytesIO, ValidationNotEqualError

class CL:
    def __init__(self, path):
        self.path = Path(path)
        self.headers = list(sorted(self.read_headers(), key=lambda x: x.tstart))

    def read_headers(self):
        for file in sorted(self.path.glob('*.CLH')):
            clh = Model3Clh.from_file(file)
            for row in clh.objects:
                yield row

    def get_timespan(self, tstart=None, tend=None):
        assert isinstance(tstart, dt.datetime) and isinstance(tend,dt.datetime)
        tstart = tstart.timestamp()
        tend = tend.timestamp()
        startidx = 0
        endidx = 0
        for idx, header in enumerate(self.headers):
            if not startidx and header.tstart >= tstart:
                startidx = idx
            if header.tend >= tend:
                endidx = idx
                break
        if not endidx:
            return self.headers[startidx:]
        else:
            return self.headers[startidx: endidx + 1]

    def read_object(self, header_row):
        with open(self.path / f'{header_row.clb_file:x}.CLB', 'rb') as f:
            f.seek(header_row.startoffset)
            object_raw = f.read(header_row.endoffset - header_row.startoffset)
        return object_raw

    def parse_object(self, header_row):
        object_raw = self.read_object(header_row)
        stream = KaitaiStream(BytesIO(object_raw))
        num_check = 0
        while not stream.is_eof():
            obj = Model3Clb.LogObject(stream)
            if not obj.number == num_check:
                print(f'Encountered blocknumber: {obj.number}, expected: {num_check}, stopping')
                break
            num_check += 1
            if not self.crc_check(obj.number, obj.crc, obj.raw_body):
                raise ValueError('Invalid CRC')
            for varint in obj.body.varints:
                yield varint.value

    def parse_objects(self, header_rows):
        objects = (ObjectParser(self.parse_object(header_row)).parse() for header_row in header_rows)
        return pd.concat(objects, ignore_index=True)

    def crc_check(self, num, crc_val, block):
        # In the code the crc is initialized with just the object number, with the len and crc field of zero
        # It is then updated with each byte that is put into the object
        head = bytes([num]) + b'\x00' * 6
        check = crc32(head + block) & 0xffffffff
        if crc_val != check:
            return False
        return True


class ObjectParser:
    def __init__(self, varint_stream):
        self.prevTimestamp = 0
        self.prevVal = 0
        self.prevSignal = 0
        self.signalHistory = dict()
        self.multiplexCount = 0
        self.vals = varint_stream

    def takeVal(self, subtract=0):
        return next(self.vals) - subtract

    def getDelta(self, val):
        signed = val & 1
        if self.multiplexCount:
            assert not signed, 'WTF'
        val >>= 1
        if signed:
            return -val
        return val

    def getAbsolute(self, signal, val):
        val = self.getDelta(val)
        if self.multiplexCount:
            return val
        if signal in self.signalHistory:
            prev = self.signalHistory[signal]
            val = prev + val
        self.signalHistory[signal] = val
        return val

    def takePoint(self):
        out = {}
        storeSig = True
        val = self.takeVal()
        if val in range(4):
            out['timestamp'] = self.prevTimestamp
            if val == 0:
                out['signal'] = self.prevSignal + 1
                out['value'] = self.prevVal
                self.signalHistory[out['signal']] = out['value']
            elif val == 1:
                out['signal'] = self.prevSignal + 1
                tmp = self.takeVal()
                tmp = self.getAbsolute(out['signal'], tmp)
                out['value'] = tmp
            elif val == 2:
                out['signal'] = self.takeVal(subtract=3)
                out['value'] = self.prevVal
                self.signalHistory[out['signal']] = out['value']
            else:  # val == 3:
                out['signal'] = self.takeVal(subtract=3)
                tmp = self.takeVal()
                tmp = self.getAbsolute(out['signal'], tmp)
                out['value'] = tmp
        else:
            out['timestamp'] = self.prevTimestamp + val - 4
            val = self.takeVal()
            if val in (0, 1):
                if val == 0:
                    out['signal'] = self.prevSignal + 1
                    out['value'] = self.prevVal
                    self.signalHistory[out['signal']] = out['value']
                else:  # val == 1:
                    out['signal'] = self.prevSignal + 1
                    tmp = self.takeVal()
                    tmp = self.getAbsolute(out['signal'], tmp)
                    out['value'] = tmp
            else:
                out['signal'] = val - 3
                tmp = self.takeVal()
                if out['signal'] == -1:
                    storeSig = False
                    tmp = self.getDelta(tmp)
                    self.multiplexCount = tmp + 1
                    out['value'] = tmp
                else:
                    tmp = self.getAbsolute(out['signal'], tmp)
                    out['value'] = tmp

        assert all(x in out for x in {'timestamp', 'signal', 'value'}), ' WTF'
        if self.multiplexCount:
            self.multiplexCount -= 1
        self.prevTimestamp = out['timestamp']
        if storeSig:
            self.prevSignal = out['signal']
        self.prevVal = out['value']
        return out['timestamp'], out['signal'], out['value']

    def stream_points(self):
        while self.vals:
            try:
                yield self.takePoint()
            except StopIteration:
                return

    def parse(self):
        return pd.DataFrame(self.stream_points(), columns=['timestamp', 'signal', 'value']).astype(
            {'timestamp': 'datetime64[ms]'})