# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Model3Hrl(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Model3Hrl.FirstBlock(self._io, self, self._root)
        self._raw_blocks = []
        self.blocks = []
        i = 0
        while not self._io.is_eof():
            self._raw_blocks.append(self._io.read_bytes(self.header.blocksize))
            _io__raw_blocks = KaitaiStream(BytesIO(self._raw_blocks[-1]))
            self.blocks.append(Model3Hrl.Block(_io__raw_blocks, self, self._root))
            i += 1


    class UnknownFrame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.payload = self._io.read_bytes((self._root.recordsize - 1))


    class FirstBlock(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.version = self._io.read_u1()
            self.git_hash = self._io.read_bytes(20)
            self.vin = (KaitaiStream.bytes_terminate(self._io.read_bytes(18), 0, False)).decode(u"UTF-8")
            self.unknown = self._io.read_u2be()
            self.start_timestamp = self._io.read_u4be()
            self.padding = self._io.read_bytes((self.blocksize - self._io.pos()))

        @property
        def blocksize(self):
            if hasattr(self, '_m_blocksize'):
                return self._m_blocksize if hasattr(self, '_m_blocksize') else None

            self._m_blocksize = (16384 if self.version <= 1 else 32768)
            return self._m_blocksize if hasattr(self, '_m_blocksize') else None


    class Block(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self._raw_records = []
            self.records = []
            i = 0
            while True:
                _buf = self._io.read_bytes(self._root.recordsize)
                self._raw_records.append(_buf)
                _io__raw_records = KaitaiStream(BytesIO(self._raw_records[-1]))
                _ = Model3Hrl.Record(_io__raw_records, self, self._root)
                self.records.append(_)
                if i == (self._root.header.blocksize // self._root.recordsize - 1):
                    break
                i += 1

        @property
        def crc(self):
            if hasattr(self, '_m_crc'):
                return self._m_crc if hasattr(self, '_m_crc') else None

            _pos = self._io.pos()
            self._io.seek((self._root.header.blocksize - (self._root.header.blocksize % self._root.recordsize)))
            self._m_crc = self._io.read_u4be()
            self._io.seek(_pos)
            return self._m_crc if hasattr(self, '_m_crc') else None

        @property
        def raw_records(self):
            if hasattr(self, '_m_raw_records'):
                return self._m_raw_records if hasattr(self, '_m_raw_records') else None

            _pos = self._io.pos()
            self._io.seek(0)
            self._m_raw_records = self._io.read_bytes((self._root.header.blocksize - (self._root.header.blocksize % self._root.recordsize)))
            self._io.seek(_pos)
            return self._m_raw_records if hasattr(self, '_m_raw_records') else None


    class CanFrame(KaitaiStruct):

        class Buses(Enum):
            veh = 0
            party = 1
            ch = 2
            eth = 3
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.bus_id = KaitaiStream.resolve_enum(Model3Hrl.CanFrame.Buses, self._io.read_bits_int_be(2))
            self.dlc_field = self._io.read_bits_int_be(3)
            self.arb_id = self._io.read_bits_int_be(11)
            self._io.align_to_byte()
            self.data = self._io.read_bytes(8)

        @property
        def dlc(self):
            if hasattr(self, '_m_dlc'):
                return self._m_dlc if hasattr(self, '_m_dlc') else None

            self._m_dlc = (self.dlc_field + 1)
            return self._m_dlc if hasattr(self, '_m_dlc') else None


    class Record(KaitaiStruct):

        class RecordFlags(Enum):
            can_frame = 0
            timestamp_frame = 1
            end_of_block = 3
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.flags = KaitaiStream.resolve_enum(Model3Hrl.Record.RecordFlags, self._io.read_bits_int_be(2))
            self.counter = self._io.read_bits_int_be(6)
            self._io.align_to_byte()
            _on = self.flags
            if _on == Model3Hrl.Record.RecordFlags.can_frame:
                self.payload = Model3Hrl.CanFrame(self._io, self, self._root)
            elif _on == Model3Hrl.Record.RecordFlags.timestamp_frame:
                self.payload = Model3Hrl.TimestampFrame(self._io, self, self._root)
            elif _on == Model3Hrl.Record.RecordFlags.end_of_block:
                self.payload = Model3Hrl.UnknownFrame(self._io, self, self._root)

        @property
        def raw_record(self):
            if hasattr(self, '_m_raw_record'):
                return self._m_raw_record if hasattr(self, '_m_raw_record') else None

            _pos = self._io.pos()
            self._io.seek(0)
            self._m_raw_record = self._io.read_bytes(self._root.recordsize)
            self._io.seek(_pos)
            return self._m_raw_record if hasattr(self, '_m_raw_record') else None

        @property
        def end_of_records(self):
            if hasattr(self, '_m_end_of_records'):
                return self._m_end_of_records if hasattr(self, '_m_end_of_records') else None

            self._m_end_of_records = self.flags == Model3Hrl.Record.RecordFlags.end_of_block
            return self._m_end_of_records if hasattr(self, '_m_end_of_records') else None


    class TimestampFrame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.milliseconds_from_start = self._io.read_u4be()


    @property
    def recordsize(self):
        if hasattr(self, '_m_recordsize'):
            return self._m_recordsize if hasattr(self, '_m_recordsize') else None

        self._m_recordsize = 11
        return self._m_recordsize if hasattr(self, '_m_recordsize') else None


