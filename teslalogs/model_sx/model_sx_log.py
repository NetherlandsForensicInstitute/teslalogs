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
        self.log_entry = ModelSxLog.Entry(self._io, self, self._root)

    class Entry(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.delim = self._io.read_bytes(1)
            if not self.delim == b"\xAA":
                raise kaitaistruct.ValidationNotEqualError(b"\xAA", self.delim, self._io, u"/types/entry/seq/0")
            self.tag = self._io.read_u1()
            self.length = self._io.read_u2be()
            self.counter = self._io.read_u2be()
            _on = self.tag
            if _on == 0:
                self._raw_body = self._io.read_bytes((self.length - 6))
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = ModelSxLog.OnChange(_io__raw_body, self, self._root)
            elif _on == 1:
                self._raw_body = self._io.read_bytes((self.length - 6))
                _io__raw_body = KaitaiStream(BytesIO(self._raw_body))
                self.body = ModelSxLog.Periodic(_io__raw_body, self, self._root)
            else:
                self.body = self._io.read_bytes((self.length - 6))
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

        @property
        def is_on_change(self):
            if hasattr(self, '_m_is_on_change'):
                return self._m_is_on_change if hasattr(self, '_m_is_on_change') else None

            self._m_is_on_change = self.tag == 0
            return self._m_is_on_change if hasattr(self, '_m_is_on_change') else None


    class Periodic(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.aggregate_id = self._io.read_u1()
            _on = self.aggregate_id
            if _on == 0:
                self._raw_aggregate_body = self._io.read_bytes_full()
                _io__raw_aggregate_body = KaitaiStream(BytesIO(self._raw_aggregate_body))
                self.aggregate_body = ModelSxLog.AggDescriptors(_io__raw_aggregate_body, self, self._root)
            else:
                self._raw_aggregate_body = self._io.read_bytes_full()
                _io__raw_aggregate_body = KaitaiStream(BytesIO(self._raw_aggregate_body))
                self.aggregate_body = ModelSxLog.AggRecords(_io__raw_aggregate_body, self, self._root)

        @property
        def is_descriptor(self):
            if hasattr(self, '_m_is_descriptor'):
                return self._m_is_descriptor if hasattr(self, '_m_is_descriptor') else None

            self._m_is_descriptor = self.aggregate_id == 0
            return self._m_is_descriptor if hasattr(self, '_m_is_descriptor') else None


    class OnChange(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.sig_id = self._io.read_u4be()
            self.value = self._io.read_bytes_full()


    class AggDescriptors(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.aggregate_id = self._io.read_u1()
            self.num_descriptors = self._io.read_u1()
            self.descriptors = [None] * (self.num_descriptors)
            for i in range(self.num_descriptors):
                self.descriptors[i] = ModelSxLog.AggDescriptor(self._io, self, self._root)



    class AggRecords(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.values = self._io.read_bytes_full()


    class AggDescriptor(KaitaiStruct):
        def __init__(self, _io, _parent=None, _root=None):
            self._io = _io
            self._parent = _parent
            self._root = _root if _root else self
            self._read()

        def _read(self):
            self.sig_id = self._io.read_u4be()
            self.unknown = self._io.read_u1()
            self.size = self._io.read_u1()



