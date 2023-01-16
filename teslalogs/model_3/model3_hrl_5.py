# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Model3Hrl5(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Model3Hrl5.Header(self._io, self, self._root)
        self._raw_blocks = []
        self.blocks = []
        i = 0
        while not self._io.is_eof():
            self._raw_blocks.append(self._io.read_bytes(self.header.block_size))
            _io__raw_blocks = KaitaiStream(BytesIO(self._raw_blocks[-1]))
            self.blocks.append(Model3Hrl5.Block(_io__raw_blocks, self, self._root))
            i += 1


    class BlockMetaData(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.block_magic = self._io.read_bytes(4)
            if not self.block_magic == b"\xBA\xDD\xCA\xFE":
                raise kaitaistruct.ValidationNotEqualError(b"\xBA\xDD\xCA\xFE", self.block_magic, self._io, u"/types/block_meta_data/seq/0")
            self.zero0 = self._io.read_bytes(3)
            if not self.zero0 == b"\x00\x00\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x00", self.zero0, self._io, u"/types/block_meta_data/seq/1")
            self.size = self._io.read_u4be()
            self.tstart = self._io.read_u4be()
            self.tend = self._io.read_u4be()
            self.obj_idx = self._io.read_u4be()
            self.startoffset = self._io.read_u4be()
            self.endoffset = self._io.read_u4be()
            self.zero1 = self._io.read_bytes(1)
            if not self.zero1 == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.zero1, self._io, u"/types/block_meta_data/seq/8")


    class Block(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.metadata = Model3Hrl5.BlockMetaData(self._io, self, self._root)
            self._raw_records = []
            self.records = []
            i = 0
            while True:
                _buf = self._io.read_bytes(11)
                self._raw_records.append(_buf)
                _io__raw_records = KaitaiStream(BytesIO(self._raw_records[-1]))
                _ = Model3Hrl5.Record(_io__raw_records, self, self._root)
                self.records.append(_)
                if  ((_.end_of_block) or (self._io.pos() >= self._root.header.block_size)) :
                    break
                i += 1


    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.version = self._io.read_u1()
            self.unknown_0 = self._io.read_u2be()
            self.vehicle_type = (KaitaiStream.bytes_terminate(self._io.read_bytes(10), 0, False)).decode(u"UTF-8")
            self.git_hash = self._io.read_bytes(20)
            self.unknown1 = self._io.read_u2be()
            self.start_time = self._io.read_u4be()
            self.end_time = self._io.read_u4be()
            self.unknown2 = self._io.read_u4be()
            self.unknown3 = self._io.read_u4be()
            self.file_index = self._io.read_u4be()
            self.unknown5 = self._io.read_bytes(10)
            self.vin = (KaitaiStream.bytes_terminate(self._io.read_bytes(18), 0, False)).decode(u"UTF-8")
            self.unknown6 = self._io.read_bytes(3)
            self.unknown_time = self._io.read_u4be()
            self.unknown7 = self._io.read_bytes(26)
            self.block_size = self._io.read_u4be()
            self.unknown8 = self._io.read_u4be()
            self.unknown9 = self._io.read_u4be()
            self.padding = self._io.read_bytes((self.block_size - self._io.pos()))


    class EmptyFrame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            pass


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
            self.bus_id = KaitaiStream.resolve_enum(Model3Hrl5.CanFrame.Buses, self._io.read_bits_int_be(2))
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

        class RecordType(Enum):
            can = 0
            time = 1
            end = 3
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.flags = KaitaiStream.resolve_enum(Model3Hrl5.Record.RecordType, self._io.read_bits_int_be(2))
            self.counter = self._io.read_bits_int_be(6)
            self._io.align_to_byte()
            _on = self.flags
            if _on == Model3Hrl5.Record.RecordType.can:
                self.payload = Model3Hrl5.CanFrame(self._io, self, self._root)
            elif _on == Model3Hrl5.Record.RecordType.time:
                self.payload = Model3Hrl5.TimestampFrame(self._io, self, self._root)
            elif _on == Model3Hrl5.Record.RecordType.end:
                self.payload = Model3Hrl5.EmptyFrame(self._io, self, self._root)

        @property
        def end_of_block(self):
            if hasattr(self, '_m_end_of_block'):
                return self._m_end_of_block

            self._m_end_of_block = self.flags == Model3Hrl5.Record.RecordType.end
            return getattr(self, '_m_end_of_block', None)


    class TimestampFrame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.time_ms_from_start = self._io.read_u4be()



