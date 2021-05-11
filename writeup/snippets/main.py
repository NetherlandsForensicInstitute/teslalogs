import struct
import pandas as pd
import matplotlib.pyplot as plt
from model_sx_log import ModelSxLog
from kaitaistruct import KaitaiStream, BytesIO

stream = open('/mnt/test/log/1.log', 'rb').read()

def read_entries(data, max_num=1000):
    # Inspired by: https://stackoverflow.com/questions/49699820/parsing-binary-messages-with-kaitai-struct-python
    stream = KaitaiStream(BytesIO(data))
    # print(f'{stream.pos():08x} ', end='')
    start = ModelSxLog(stream)  # Initialize the parser on the root stream
    log_entry = start.log_entry
    yield log_entry
    num_entries = 1
    while not stream.is_eof():
        try:
            # print(f'{stream.pos():08x} ', end='')
            log_entry = ModelSxLog.Record(stream, _root=start._root)
            if sum(log_entry.raw_bytes) % 256 != 0:
                print(f'Checksum error at {stream.pos()}, seeking to the next entry...')
                stream.read_bytes_term(0xaa, include_term=False, consume_term=False, eos_error=True)
            else:
                yield log_entry
        except:
            # Unfortunately kaitaistruct does not specify the exception, assuming it's a wrong delimiter
            print(f'Encountered an error at {stream.pos()}, probably a corrupt entry, seeking to next one...')
            stream.read_bytes_term(0xaa, include_term=False, consume_term=False, eos_error=True)
            pass
        num_entries += 1
        if num_entries > max_num:
            break
    stream.close()

def process_log(stream, max_num=1000):
    rollingtime = 0
    for entry in read_entries(stream, max_num=max_num):
        # print(record.raw_bytes.hex()[:60])
        payload = entry.raw_bytes
        print(' '.join([payload[1:2].hex(), payload[6:-1].hex()])[:60])
        tag = payload[1]
        counter = struct.unpack('>H', payload[4:6])[0]
        # if tag == b'\x00' and counter == 0:
        if tag == 0:
            sigid = struct.unpack('>I', payload[6:10])[0]
            if sigid in (0xd00007dd, 0xd00007de):
                tstamp = struct.unpack('>I', payload[10:14])[0]
                rollingtime = tstamp
        yield (counter, rollingtime)

data = pd.DataFrame(process_log(stream, max_num=10000), columns=['counter', 'timestamp'])
data['timestamp'] = data['timestamp'].diff()
# print(data)
fig = plt.figure()
ax = data['counter'].plot()
ax.set_ylabel('Counter')
ax = data['timestamp'].plot(secondary_y=True)
ax.set_ylabel('Timestamp diff')
plt.show()
# plt.savefig('/tmp/counter_timestamp_diff.png')


