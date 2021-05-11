meta:
  id: model_sx_log
  title: ModelS gateway log
  file-extension: log
  endian: be

# Only used to hint at parent structure, we'll parse the log entries manually from the stream for more control
seq:
  - id: log_entry
    type: entry

types:
  entry:
    seq:
      - id: delim
        contents: [0xaa]
      - id: tag
        type: u1
      - id: length
        type: u2
      - id: counter
        type: u2
      - id: body
        size: length - 6  # Number of bytes between delimiters
        type:
          switch-on: tag
          cases:
            0: on_change
            1: periodic
      - id: checksum
        type: u1
    instances:
      raw_bytes:
        pos: _io.pos - (length + 1)  # Rewind stream back to start
        size: length + 1  # Consume up to the next one
      is_on_change:
        value: tag == 0
  on_change:
    seq:
      - id: sig_id
        type: u4
      - id: value
        size-eos: true
  periodic:
    seq:
      - id: aggregate_id
        type: u1
      - id: aggregate_body
        size-eos: true
        type:
          switch-on: aggregate_id
          cases:
            0: agg_descriptors
            _: agg_records
    instances:
      is_descriptor:
        value: aggregate_id == 0
  agg_descriptors:
    seq:
      - id: aggregate_id
        type: u1
      - id: num_descriptors
        type: u1
      - id: descriptors
        type: agg_descriptor
        repeat: expr
        repeat-expr: num_descriptors
  agg_descriptor:
    seq:
      - id: sig_id
        type: u4
      - id: unknown
        type: u1
      - id: size
        type: u1
  agg_records:
    seq:
      - id: values
        size-eos: true
