# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO
from enum import Enum


if getattr(kaitaistruct, 'API_VERSION', (0, 9)) < (0, 9):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class HrlParser(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.version = self._io.read_u1()
        _on = self.version
        if _on == 5:
            self.header = HrlParser.HeaderV5(self._io, self, self._root)
        else:
            self.header = HrlParser.HeaderV0(self._io, self, self._root)
        self.padding = self._io.read_bytes((self._root.blocksize - self._io.pos()))
        self._raw_blocks = []
        self.blocks = []
        i = 0
        while not self._io.is_eof():
            self._raw_blocks.append(self._io.read_bytes(self.blocksize))
            _io__raw_blocks = KaitaiStream(BytesIO(self._raw_blocks[-1]))
            self.blocks.append(HrlParser.Block(_io__raw_blocks, self, self._root))
            i += 1


    class BlockMetadata(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.block_magic = self._io.read_bytes(4)
            if not self.block_magic == b"\xBA\xDD\xCA\xFE":
                raise kaitaistruct.ValidationNotEqualError(b"\xBA\xDD\xCA\xFE", self.block_magic, self._io, u"/types/block_metadata/seq/0")
            self.zero0 = self._io.read_bytes(3)
            if not self.zero0 == b"\x00\x00\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x00", self.zero0, self._io, u"/types/block_metadata/seq/1")
            self.data_size = self._io.read_u4be()
            self.tstart = self._io.read_u4be()
            self.tend = self._io.read_u4be()
            self.obj_idx = self._io.read_u4be()
            self.startoffset = self._io.read_u4be()
            self.endoffset = self._io.read_u4be()
            self.zero1 = self._io.read_bytes(1)
            if not self.zero1 == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.zero1, self._io, u"/types/block_metadata/seq/8")


    class HeaderV0(KaitaiStruct):
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


    class Block(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            if  ((self._root.version >= 5) and (self.valid)) :
                self.metadata = HrlParser.BlockMetadata(self._io, self, self._root)

            self._raw_records = []
            self.records = []
            for i in range(self._root.num_records):
                self._raw_records.append(self._io.read_bytes(self._root.record_size))
                _io__raw_records = KaitaiStream(BytesIO(self._raw_records[i]))
                self.records.append(HrlParser.Record(_io__raw_records, self, self._root))

            self.crc = self._io.read_u4be()

        @property
        def as_raw_records(self):
            if hasattr(self, '_m_as_raw_records'):
                return self._m_as_raw_records

            _pos = self._io.pos()
            self._io.seek((32 if self._root.version >= 5 else 0))
            self._m_as_raw_records = self._io.read_bytes(self._root.records_size)
            self._io.seek(_pos)
            return getattr(self, '_m_as_raw_records', None)

        @property
        def magic(self):
            if hasattr(self, '_m_magic'):
                return self._m_magic

            _pos = self._io.pos()
            self._io.seek(0)
            self._m_magic = self._io.read_bytes(4)
            self._io.seek(_pos)
            return getattr(self, '_m_magic', None)

        @property
        def valid(self):
            if hasattr(self, '_m_valid'):
                return self._m_valid

            self._m_valid =  ((self._root.version < 5) or (self.magic == b"\xBA\xDD\xCA\xFE")) 
            return getattr(self, '_m_valid', None)


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
            self.start_timestamp = self._io.read_u4be()
            self.end_timestamp = self._io.read_u4be()
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
            self.bus_id = KaitaiStream.resolve_enum(HrlParser.CanFrame.Buses, self._io.read_bits_int_be(2))
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
            self.flags = KaitaiStream.resolve_enum(HrlParser.Record.RecordType, self._io.read_bits_int_be(2))
            self.time_count = self._io.read_bits_int_be(6)
            self._io.align_to_byte()
            _on = self.flags
            if _on == HrlParser.Record.RecordType.can:
                self.payload = HrlParser.CanFrame(self._io, self, self._root)
            elif _on == HrlParser.Record.RecordType.time:
                self.payload = HrlParser.TimestampFrame(self._io, self, self._root)
            elif _on == HrlParser.Record.RecordType.end:
                self.payload = HrlParser.EmptyFrame(self._io, self, self._root)

        @property
        def end_of_block(self):
            if hasattr(self, '_m_end_of_block'):
                return self._m_end_of_block

            self._m_end_of_block = self.flags == HrlParser.Record.RecordType.end
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
    def records_size(self):
        if hasattr(self, '_m_records_size'):
            return self._m_records_size

        self._m_records_size = (self.num_records * self._root.record_size)
        return getattr(self, '_m_records_size', None)

    @property
    def data_size(self):
        if hasattr(self, '_m_data_size'):
            return self._m_data_size

        self._m_data_size = ((self._root.blocksize - 32) if self._root.version >= 5 else self._root.blocksize)
        return getattr(self, '_m_data_size', None)

    @property
    def num_records(self):
        if hasattr(self, '_m_num_records'):
            return self._m_num_records

        self._m_num_records = (self.data_size - 4) // self._root.record_size
        return getattr(self, '_m_num_records', None)

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

        self._m_blocksize = (16384 if self.version <= 1 else 32768)
        return getattr(self, '_m_blocksize', None)


