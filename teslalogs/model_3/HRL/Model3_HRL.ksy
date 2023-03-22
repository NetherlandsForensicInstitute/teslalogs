meta:
  id: model_3_hrl
  title: Model3 High Resolution Log
  file-extension: hrl
  endian: be

seq:
  - id: header
    type: first_block
  - id: blocks
    type: block
    size: header.blocksize
    repeat: eos

types:
  first_block:
    seq:
      - id: version
        type: u1
      - id: git_hash
        size: 20
      - id: vin
        type: str
        terminator: 0
        encoding: UTF-8
        size: 18
      - id: unknown
        type: u2
      - id: start_timestamp
        type: u4
      - id: padding  # On version 3 there's actually something here, but I don't yet know what
        size: blocksize - _io.pos
    instances:
      blocksize:
        value: 'version <= 1 ? 0x4000 : 0x8000'  # Ugly, but I did not find a good lookup table in Kaitai
  block:
    seq:
      - id: records
        type: record
        size: _root.recordsize
        repeat: until
        repeat-until: _index == (_root.header.blocksize / _root.recordsize - 1)
    instances:
      crc:
        type: u4
        pos: _root.header.blocksize - (_root.header.blocksize % _root.recordsize)
      raw_records:
        pos: 0
        size: _root.header.blocksize - (_root.header.blocksize % _root.recordsize)

  record:
    seq:
      - id: flags
        type: b2
        enum: record_flags
      - id: counter
        type: b6
      - id: payload
        type:
          switch-on: flags
          cases:
            'record_flags::can_frame': can_frame
            'record_flags::timestamp_frame': timestamp_frame
            'record_flags::end_of_block': unknown_frame
    enums:
      record_flags:
        0: can_frame
        1: timestamp_frame
        3: end_of_block
    instances:
      raw_record:
        pos: 0
        size: _root.recordsize
      end_of_records:
        value: flags == record_flags::end_of_block

  can_frame:
    seq:
      - id: bus_id
        type: b2
        enum: buses
      - id: dlc_field
        type: b3
      - id: arb_id
        type: b11
      - id: data
        size: 8
    instances:
      dlc:
        value: dlc_field + 1
    enums:
      buses:
        0: veh
        1: party
        2: ch
        3: eth  # ETH seems to not be present in HRL, it is in the regular logs
  timestamp_frame:
    seq:
      - id: milliseconds_from_start
        type: u4
  unknown_frame:
    seq:
      - id: payload
        size: _root.recordsize - 1

instances:
  recordsize:
    value: 11
