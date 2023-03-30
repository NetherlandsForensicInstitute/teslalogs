meta:
  id: hrl_parser
  file-extension: hrl
  endian: be
  
seq:
  - id: version
    type: u1
  - id: header
    type: 
      switch-on: version
      cases:
        5: header_v5
        _: header_v0
  - id: padding  # On version 3 there's actually something here, but I don't know what
    size: _root.blocksize - _io.pos
  - id: blocks
    type: block
    size: blocksize
    repeat: eos
instances:
  record_size:
    value: 11
  blocksize:
    value: 'version <= 1 ? 0x4000 : 0x8000'
  data_size: 
    value: '_root.version >= 5 ? _root.blocksize - 0x20 : _root.blocksize'
  num_records:
    value: (data_size - 4) / _root.record_size
  records_size:
    value: num_records * _root.record_size

types:
  header_v5:
    seq:
      - id: unknown_0
        type: u2
      - id: vehicle_type
        type: strz
        encoding: UTF-8
        size: 10
      - id: git_hash
        size: 20
      - id: unknown1
        type: u2
      - id: start_timestamp
        type: u4
      - id: end_timestamp
        type: u4
      - id: start_obj_idx
        type: u4
      - id: end_obj_idx  # check if the last is included
        type: u4
      - id: file_index
        type: u4
      - id: unknown5
        size: 10
      - id: vin
        type: strz
        encoding: UTF-8
        size: 18
      - id: unknown6
        size: 3
      - id: unknown_time
        type: u4
      - id: unknown7
        size: 26
      - id: block_size  # ignored
        type: u4
      - id: unknown8
        type: u4
      - id: unknown9
        type: u4

  header_v0:
    seq:
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
      
  block:
    seq: 
      - id: metadata  # not using data size given in metadata
        type: block_metadata
        if: '_root.version >= 5 and valid'
      - id: records
        type: record
        size: _root.record_size
        repeat: expr
        repeat-expr: _root.num_records
      - id: crc
        type: u4
    instances:
      as_raw_records:
        pos: '_root.version >= 5 ? 0x20 : 0'
        size: _root.records_size
      magic:
        pos: 0
        size: 4
      valid:
        value: '_root.version < 5 or magic == [0xba, 0xdd, 0xca, 0xfe]'
    
  block_metadata:
    seq:
      - id: block_magic
        contents: [0xba, 0xdd, 0xca, 0xfe]
      - id: zero0
        contents: [0x00, 0x00, 0x00]
      - id: data_size  # ignored
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
      - id: zero1
        contents: [0x00]
        
  record:
    seq:
      - id: flags
        type: b2
        enum: record_type
      - id: time_count
        type: b6
      - id: payload
        type:
          switch-on: flags
          cases:
            'record_type::can': can_frame
            'record_type::time': timestamp_frame
            'record_type::end': empty_frame
    enums:
      record_type:
        0: can
        1: time
        3: end
    instances:
      end_of_block:
        value: 'flags == record_type::end'

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
        3: eth  # ETH does not seem to be present in HRL
        
  timestamp_frame:
    seq:
      - id: time_ms_from_start
        type: u4
        
  empty_frame: {}

