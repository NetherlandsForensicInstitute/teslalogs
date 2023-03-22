meta:
  id: model_3_clb
  title: Model3 CLB
  endian: be
  imports:
    - vlq_base128_le

seq:
  - id: obj
    type: log_object
    repeat: eos

types:
  log_object:
    seq:
      - id: number
        type: u1
      - id: len
        type: u2
      - id: crc
        type: u4
      - id: body
        type: body
        size: len
    instances:
      raw_body:
        pos: _io.pos - len  # Rewind stream back to start
        size: len  # Consume up to the next one
  body:
    seq:
      - id: varints
        type: vlq_base128_le
        repeat: eos
