meta:
  id: hrl5
  file-extension: hrl5
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
      - id: clh
        type: clh_header
      - id: vin
        type: str
        terminator: 0
        encoding: UTF-8
        size: 18
      - id: unknown
        size: 3
      - id: start_timestamp
        type: u4
      - id: unknown1
        size: 2
      - id: zeros
        size: 36
      - id: padding  # On version 3 there's actually something here, but I don't yet know what
        size: blocksize - _io.pos
    instances:
      blocksize:
        value: 'version <= 1 ? 0x4000 : 0x8000'  # Ugly, but I did not find a good lookup table in Kaitai
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
      - id: last_timestamp
        type: u4
      - id: first_obj_idx
        type: u4
      - id: last_obj_idx
        type: u4
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
        type: u4
        # contents: [0xba, 0xdd, 0xca, 0xfe]
      - id: zero_0
        size: 3
        # contents: [0x00, 0x00, 0x00]
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
        size: 1
        # contents: [0x00]
    instances:
      is_valid:
        value: signature == 0xbaddcafe  # And zero's ?
  block:
    seq:
      - id: header
        type: object_metadata
      - id: records
        type: record
        size: _root.recordsize
        repeat: expr
        repeat-expr: (0x7fe0 / _root.recordsize - 1)
      - id: crc
        type: u4
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

