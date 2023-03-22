meta:
  id: model_3_clh
  title: Model3 CLH
  endian: be

seq:
  - id: header
    type: clh_header
  - id: objects
    type: object_metadata
    repeat: eos

types:
  clh_header:
    seq:
      - id: unknown_0
        type: u2
      - id: vehicle_type
        type: str
        size: 6
        encoding: UTF-8
      - id: unknown_1
        type: u4
      - id: git_hash
        size: 20
      - id: unknown_2
        type: u2
      - id: first_timestamp
        type: u4
      - id: unknown_3
        contents: [0xff, 0xff, 0xff, 0xff]
      - id: first_obj_idx
        type: u4
      - id: unknown_4
        contents: [0xff, 0xff, 0xff, 0xff]
      - id: file_number
        type: u4
      - id: unknown_5
        size: 4
        #contents: [0x00, 0x00, 0x00, 0x00]
      - id: unknown_6
        size: 6
  object_metadata:
    seq:
      - id: signature
        contents: [0xba, 0xdd, 0xca, 0xfe]
      - id: zero_0
        contents: [0x00, 0x00, 0x00]
      - id: size
        type: u4
      - id: tstart
        type: u4
      - id: tend
        type: u4
      - id: obj_idx
        type: u4
      - id: startoffset
        type: u4
      - id: endoffset
        type: u4
      - id: zero_1
        contents: [0x00]
    instances:
      clb_file:
        value: _root.header.file_number
