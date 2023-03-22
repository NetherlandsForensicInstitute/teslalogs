# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class Model3Clh(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.header = Model3Clh.ClhHeader(self._io, self, self._root)
        self.objects = []
        i = 0
        while not self._io.is_eof():
            self.objects.append(Model3Clh.ObjectMetadata(self._io, self, self._root))
            i += 1


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
            self.unknown_3 = self._io.read_bytes(4)
            if not self.unknown_3 == b"\xFF\xFF\xFF\xFF":
                raise kaitaistruct.ValidationNotEqualError(b"\xFF\xFF\xFF\xFF", self.unknown_3, self._io, u"/types/clh_header/seq/6")
            self.first_obj_idx = self._io.read_u4be()
            self.unknown_4 = self._io.read_bytes(4)
            if not self.unknown_4 == b"\xFF\xFF\xFF\xFF":
                raise kaitaistruct.ValidationNotEqualError(b"\xFF\xFF\xFF\xFF", self.unknown_4, self._io, u"/types/clh_header/seq/8")
            self.file_number = self._io.read_u4be()
            self.unknown_5 = self._io.read_bytes(4)
            self.unknown_6 = self._io.read_bytes(6)


    class ObjectMetadata(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.signature = self._io.read_bytes(4)
            if not self.signature == b"\xBA\xDD\xCA\xFE":
                raise kaitaistruct.ValidationNotEqualError(b"\xBA\xDD\xCA\xFE", self.signature, self._io, u"/types/object_metadata/seq/0")
            self.zero_0 = self._io.read_bytes(3)
            if not self.zero_0 == b"\x00\x00\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00\x00\x00", self.zero_0, self._io, u"/types/object_metadata/seq/1")
            self.size = self._io.read_u4be()
            self.tstart = self._io.read_u4be()
            self.tend = self._io.read_u4be()
            self.obj_idx = self._io.read_u4be()
            self.startoffset = self._io.read_u4be()
            self.endoffset = self._io.read_u4be()
            self.zero_1 = self._io.read_bytes(1)
            if not self.zero_1 == b"\x00":
                raise kaitaistruct.ValidationNotEqualError(b"\x00", self.zero_1, self._io, u"/types/object_metadata/seq/8")

        @property
        def clb_file(self):
            if hasattr(self, '_m_clb_file'):
                return self._m_clb_file if hasattr(self, '_m_clb_file') else None

            self._m_clb_file = self._root.header.file_number
            return self._m_clb_file if hasattr(self, '_m_clb_file') else None



