# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class HrlV5Parser(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = HrlV5Parser.Header(self._io, self, self._root)
        self._raw_blocks = []
        self.blocks = []
        for i in range(3):
            self._raw_blocks.append(self._io.read_bytes(self.blocksize))
            _io__raw_blocks = KaitaiStream(BytesIO(self._raw_blocks[i]))
            self.blocks.append(HrlV5Parser.Block(_io__raw_blocks, self, self._root))


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
            self.data_size = self._io.read_u4be()
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
            if self._root.header.version >= 5:
                self.metadata = HrlV5Parser.BlockMetaData(self._io, self, self._root)

            self._raw_records = []
            self.records = []
            for i in range((self.data_size // self._root.record_size - 1)):
                self._raw_records.append(self._io.read_bytes(self._root.record_size))
                _io__raw_records = KaitaiStream(BytesIO(self._raw_records[i]))
                self.records.append(HrlV5Parser.Record(_io__raw_records, self, self._root))

            self.crc = self._io.read_u4be()

        @property
        def data_size(self):
            if hasattr(self, '_m_data_size'):
                return self._m_data_size

            self._m_data_size = (self.metadata.data_size if self._root.header.version >= 5 else self._root.blocksize)
            return getattr(self, '_m_data_size', None)

        @property
        def raw_data(self):
            if hasattr(self, '_m_raw_data'):
                return self._m_raw_data

            _pos = self._io.pos()
            self._io.seek((32 if self._root.header.version >= 5 else 0))
            self._m_raw_data = self._io.read_bytes((self.data_size - self._root.record_size))
            self._io.seek(_pos)
            return getattr(self, '_m_raw_data', None)


    class HeaderV5(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.unknown_0 = self._io.read_u2be()
            self.vehicle_type = (KaitaiStream.bytes_terminate(self._io.read_bytes(10), 0, False)).decode(u"UTF-8")
            self.git_hash = self._io.read_bytes(20)
            self.unknown1 = self._io.read_u2be()
            self.start_time = self._io.read_u4be()
            self.end_time = self._io.read_u4be()
            self.start_obj_idx = self._io.read_u4be()
            self.end_obj_idx = self._io.read_u4be()
            self.file_index = self._io.read_u4be()
            self.unknown5 = self._io.read_bytes(10)
            self.vin = (KaitaiStream.bytes_terminate(self._io.read_bytes(18), 0, False)).decode(u"UTF-8")
            self.unknown6 = self._io.read_bytes(3)
            self.unknown_time = self._io.read_u4be()
            self.unknown7 = self._io.read_bytes(26)
            self.block_size = self._io.read_u4be()
            self.unknown8 = self._io.read_u4be()
            self.unknown9 = self._io.read_u4be()
            self.padding = self._io.read_bytes((self._root.blocksize - self._io.pos()))


    class Header(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.version = self._io.read_u1()
            _on = self.version
            if _on == 5:
                self.header_body = HrlV5Parser.HeaderV5(self._io, self, self._root)
            else:
                self.header_body = HrlV5Parser.HeaderLtv5(self._io, self, self._root)


    class HeaderLtv5(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.git_hash = self._io.read_bytes(20)
            self.vin = (KaitaiStream.bytes_terminate(self._io.read_bytes(18), 0, False)).decode(u"UTF-8")
            self.unknown = self._io.read_u2be()
            self.start_timestamp = self._io.read_u4be()
            self.padding = self._io.read_bytes((self._root.blocksize - self._io.pos()))


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
            self.bus_id = KaitaiStream.resolve_enum(HrlV5Parser.CanFrame.Buses, self._io.read_bits_int_be(2))
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
            self.flags = KaitaiStream.resolve_enum(HrlV5Parser.Record.RecordType, self._io.read_bits_int_be(2))
            self.time_count = self._io.read_bits_int_be(6)
            self._io.align_to_byte()
            _on = self.flags
            if _on == HrlV5Parser.Record.RecordType.can:
                self.payload = HrlV5Parser.CanFrame(self._io, self, self._root)
            elif _on == HrlV5Parser.Record.RecordType.time:
                self.payload = HrlV5Parser.TimestampFrame(self._io, self, self._root)
            elif _on == HrlV5Parser.Record.RecordType.end:
                self.payload = HrlV5Parser.EmptyFrame(self._io, self, self._root)

        @property
        def end_of_block(self):
            if hasattr(self, '_m_end_of_block'):
                return self._m_end_of_block

            self._m_end_of_block = self.flags == HrlV5Parser.Record.RecordType.end
            return getattr(self, '_m_end_of_block', None)


    class TimestampFrame(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.time_ms_from_start = self._io.read_u4be()


    @property
    def record_size(self):
        if hasattr(self, '_m_record_size'):
            return self._m_record_size

        self._m_record_size = 11
        return getattr(self, '_m_record_size', None)

    @property
    def blocksize(self):
        if hasattr(self, '_m_blocksize'):
            return self._m_blocksize

        self._m_blocksize = (16384 if self.header.version <= 1 else 32768)
        return getattr(self, '_m_blocksize', None)


