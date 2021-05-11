# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

class ModelSxLog(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.log_entry = ModelSxLog.Record(self._io, self, self._root)

    class Record(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.delim = self._io.read_bytes(1)
            if not self.delim == b"\xAA":
                raise kaitaistruct.ValidationNotEqualError(b"\xAA", self.delim, self._io, u"/types/record/seq/0")
            self.tag = self._io.read_u1()
            self.length = self._io.read_u2be()
            self.body = self._io.read_bytes((self.length - 4))
            self.checksum = self._io.read_u1()

        @property
        def raw_bytes(self):
            if hasattr(self, '_m_raw_bytes'):
                return self._m_raw_bytes if hasattr(self, '_m_raw_bytes') else None

            _pos = self._io.pos()
            self._io.seek((self._io.pos() - (self.length + 1)))
            self._m_raw_bytes = self._io.read_bytes((self.length + 1))
            self._io.seek(_pos)
            return self._m_raw_bytes if hasattr(self, '_m_raw_bytes') else None



