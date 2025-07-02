# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Hrl5(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Hrl5.FirstBlock(self._io, self, self._root)
        self._raw_blocks = []
        self.blocks = []
        i = 0
        while not self._io.is_eof():
            self._raw_blocks.append(self._io.read_bytes(self.header.blocksize))
            _io__raw_blocks = KaitaiStream(BytesIO(self._raw_blocks[-1]))
            self.blocks.append(Hrl5.Block(_io__raw_blocks, self, self._root))
            i += 1


    class ObjectMetadata(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.signature = self._io.read_u4be()
            self.zero_0 = self._io.read_bytes(3)
            self.size = self._io.read_u4be()
            self.tstart = self._io.read_u4be()
            self.tend = self._io.read_u4be()
            self.obj_idx = self._io.read_u4be()
            self.startoffset = self._io.read_u4be()
            self.endoffset = self._io.read_u4be()
            self.zero_1 = self._io.read_bytes(1)

        @property
        def is_valid(self):
            if hasattr(self, '_m_is_valid'):
                return self._m_is_valid

            self._m_is_valid = self.signature == 3135097598
            return getattr(self, '_m_is_valid', None)


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
            self.clh = Hrl5.ClhHeader(self._io, self, self._root)
            self.vin = (KaitaiStream.bytes_terminate(self._io.read_bytes(18), 0, False)).decode(u"UTF-8")
            self.unknown = self._io.read_bytes(3)
            self.start_timestamp = self._io.read_u4be()
            self.unknown1 = self._io.read_bytes(2)
            self.zeros = self._io.read_bytes(36)
            self.padding = self._io.read_bytes((self.blocksize - self._io.pos()))

        @property
        def blocksize(self):
            if hasattr(self, '_m_blocksize'):
                return self._m_blocksize

            self._m_blocksize = (16384 if self.version <= 1 else 32768)
            return getattr(self, '_m_blocksize', None)


    class Block(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.header = Hrl5.ObjectMetadata(self._io, self, self._root)
            self._raw_records = []
            self.records = []
            for i in range((32736 // self._root.recordsize - 1)):
                self._raw_records.append(self._io.read_bytes(self._root.recordsize))
                _io__raw_records = KaitaiStream(BytesIO(self._raw_records[i]))
                self.records.append(Hrl5.Record(_io__raw_records, self, self._root))

            self.crc = self._io.read_u4be()


    class ClhHeader(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unknown_0 = self._io.read_u2be()
            self.vehicle_type = (self._io.read_bytes(6)).decode(u"UTF-8")
            self.unknown_1 = self._io.read_u4be()
            self.git_hash = self._io.read_bytes(20)
            self.unknown_2 = self._io.read_u2be()
            self.first_timestamp = self._io.read_u4be()
            self.last_timestamp = self._io.read_u4be()
            self.first_obj_idx = self._io.read_u4be()
            self.last_obj_idx = self._io.read_u4be()
            self.file_number = self._io.read_u4be()
            self.unknown_5 = self._io.read_bytes(4)
            self.unknown_6 = self._io.read_bytes(6)


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
            self.bus_id = KaitaiStream.resolve_enum(Hrl5.CanFrame.Buses, self._io.read_bits_int_be(2))
            self.dlc_field = self._io.read_bits_int_be(3)
            self.arb_id = self._io.read_bits_int_be(11)
            self._io.align_to_byte()
            self.data = self._io.read_bytes(8)

        @property
        def dlc(self):
            if hasattr(self, '_m_dlc'):
                return self._m_dlc

            self._m_dlc = (self.dlc_field + 1)
            return getattr(self, '_m_dlc', None)


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
            self.flags = KaitaiStream.resolve_enum(Hrl5.Record.RecordFlags, self._io.read_bits_int_be(2))
            self.counter = self._io.read_bits_int_be(6)
            self._io.align_to_byte()
            _on = self.flags
            if _on == Hrl5.Record.RecordFlags.can_frame:
                self.payload = Hrl5.CanFrame(self._io, self, self._root)
            elif _on == Hrl5.Record.RecordFlags.timestamp_frame:
                self.payload = Hrl5.TimestampFrame(self._io, self, self._root)
            elif _on == Hrl5.Record.RecordFlags.end_of_block:
                self.payload = Hrl5.UnknownFrame(self._io, self, self._root)

        @property
        def raw_record(self):
            if hasattr(self, '_m_raw_record'):
                return self._m_raw_record

            _pos = self._io.pos()
            self._io.seek(0)
            self._m_raw_record = self._io.read_bytes(self._root.recordsize)
            self._io.seek(_pos)
            return getattr(self, '_m_raw_record', None)

        @property
        def end_of_records(self):
            if hasattr(self, '_m_end_of_records'):
                return self._m_end_of_records

            self._m_end_of_records = self.flags == Hrl5.Record.RecordFlags.end_of_block
            return getattr(self, '_m_end_of_records', None)


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
            return self._m_recordsize

        self._m_recordsize = 11
        return getattr(self, '_m_recordsize', None)


