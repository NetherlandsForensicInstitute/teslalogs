# This is a generated file! Please edit source .ksy file and use kaitai-struct-compiler to rebuild

from pkg_resources import parse_version
import kaitaistruct
from kaitaistruct import KaitaiStruct, KaitaiStream, BytesIO


if parse_version(kaitaistruct.__version__) < parse_version('0.9'):
    raise Exception("Incompatible Kaitai Struct Python API: 0.9 or later is required, but you have %s" % (kaitaistruct.__version__))

from .vlq_base128_le import VlqBase128Le
class Model3Clb(KaitaiStruct):
    def __init__(self, _io, _parent=None, _root=None):
        self._io = _io
        self._parent = _parent
        self._root = _root if _root else self
        self._read()

    def _read(self):
        self.obj = []
        i = 0
        while not self._io.is_eof():
            self.obj.append(Model3Clb.LogObject(self._io, self, self._root))
            i += 1


    class LogObject(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.number = self._io.read_u1()
            self.len = self._io.read_u2be()
            self.crc = self._io.read_u4be()
            self._raw_body = self._io.read_bytes(self.len)
            _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
            self.body = Model3Clb.Body(_io__raw_body, self, self._root)

        @property
        def raw_body(self):
            if hasattr(self, '_m_raw_body'):
                return self._m_raw_body if hasattr(self, '_m_raw_body') else None

            _pos = self._io.pos()
            self._io.seek((self._io.pos() - self.len))
            self._m_raw_body = self._io.read_bytes(self.len)
            self._io.seek(_pos)
            return self._m_raw_body if hasattr(self, '_m_raw_body') else None


    class Body(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.varints = []
            i = 0
            while not self._io.is_eof():
                self.varints.append(VlqBase128Le(self._io))
                i += 1




