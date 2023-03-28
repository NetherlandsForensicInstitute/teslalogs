meta:
  id: hrl_v5_parser
  file-extension: hrl
  endian: be
  
seq:
  - id: header
    type: header
  - id: blocks
    type: block
    size: header.blocksize
    # repeat: expr
    # repeat-expr: 3
    repeat: eos

types:
  header:
    seq:
      - id: version
        type: u1
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
      - id: start_time
        type: u4
      - id: end_time
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
      - id: block_size
        type: u4
      - id: unknown8
        type: u4
      - id: unknown9
        type: u4
      - id: padding 
        size: blocksize - _io.pos
    instances:
      blocksize:
        value: 'block_size == 0 ? 0x8000 : block_size'
      
  block:
    seq: 
      - id: metadata
        type: block_meta_data
      - id: records
        type: record
        size: 11
        repeat: expr
        repeat-expr: metadata.data_size / 11 - 1
        # repeat-until: '_index == (metadata.data_size / 11 - 1)' # different behaviour in IDE than local
      - id: crc
        type: u4   
    instances:
      raw_data:
          pos: 0x20
          size: metadata.data_size - 11
    
  block_meta_data:
    seq:
      - id: block_magic
        contents: [0xba, 0xdd, 0xca, 0xfe]
      - id: zero0
        contents: [0x00, 0x00, 0x00]
      - id: data_size
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
        3: eth
        
  timestamp_frame:
    seq:
      - id: time_ms_from_start
        type: u4
        
  empty_frame: {}


  
