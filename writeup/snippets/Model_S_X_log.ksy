meta:
  id: model_sx_log
  title: Model S & X gateway log
  file-extension: log
  endian: be

# Only used as the starting structure, we'll parse the log entries manually from the stream for more control and error handling
seq:
  - id: log_entry
    type: record

types:
  record:
    seq:
      - id: delim
        contents: [0xaa]
      - id: tag
        type: u1
      - id: length
        type: u2
      - id: body
        size: length - 4
      - id: checksum
        type: u1
    instances:
      raw_bytes:
        pos: _io.pos - (length + 1)  # Rewind stream back to start
        size: length + 1  # Consume up to the next one
