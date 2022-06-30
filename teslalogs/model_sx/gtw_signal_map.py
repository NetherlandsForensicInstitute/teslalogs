import re
import struct
import json
import cantools
import pickle
import numpy as np
from argparse import ArgumentParser
from pathlib import Path
from collections import defaultdict, namedtuple
from teslalogs.utils import read_jsons


# Not the original but the ppc fork: https://github.com/simigo79/unicorn-ppc
# See installation instructions here: https://github.com/simigo79/unicorn-ppc/blob/master/bindings/python/README.TXT
from unicorn import *
from unicorn.ppc_const import *

# Bus IDS as they map to the CAN base objects in gtw firmware FlexCan interfaces A through F plus ETH
BUS_IDS = {0: 'OBDII',
           1: 'BDY',
           2: 'PT',
           3: 'BFT',
           4: 'TH',
           5: 'CH',
           6: 'ETH'}

# Fill these
OLD_FMT = True  # Determines can payload offset in struct
# 2.7.77.mcu1/models-GW_R4.bin
COPY_FLASH_START = 0x16e004
COPY_RAM_START = 0x40046cf0
COPY_RAM_END = 0x4005c27c
CAN_BASES = 0x3f6e8

# 2.30.61/models-GW_R4.bin
# COPY_FLASH_START = 0x111004
# COPY_RAM_START = 0x4004c4f0
# COPY_RAM_END = 0x400669e4
# CAN_BASES = 0x42fb8

# 2018.20.mcu2/2018.20_gtw_211_models-GW_R7.bin
# COPY_FLASH_START = 0x149004
# COPY_RAM_START = 0x4004c4f0
# COPY_RAM_END = 0x40067410
# CAN_BASES = 0x31120



# Leave these alone
COPY_LEN = COPY_RAM_END - COPY_RAM_START
GTW_BASE = 0x20000
mapped_sig = namedtuple('mapped_sig', 'bus message signal byte_order scale offset choices unit')


class Emulator:
    def __init__(self, code_flash, copy_flash_start, copy_ram_start, copy_ram_end):
        mu = Uc(UC_ARCH_PPC, UC_MODE_PPC32 | UC_MODE_BIG_ENDIAN)
        # map 2MB memory for this emulation
        mu.mem_map(GTW_BASE, 0x200000)
        mu.mem_map(0x40000000, 0x1000000)
        # write machine code to be emulated to memory
        mu.mem_write(GTW_BASE, code_flash)
        copy_len = copy_ram_end - copy_ram_start
        copied_data = bytes(mu.mem_read(copy_flash_start, copy_len))  # A bytearray is returned, but write needs bytes
        mu.mem_write(copy_ram_start, copied_data)
        self.mu = mu

    def emulate_fcn(self, payload_addr, payload, fcn_ptr):
        try:
            self.mu.mem_write(payload_addr, payload)
            code_start = fcn_ptr
            code = self.mu.mem_read(code_start, 10240)
            pat = re.compile(bytes.fromhex('4e 80 00 20'), re.MULTILINE)  # BLR
            hit = next(re.finditer(pat, code))
            code_end = hit.start() + code_start
            self.mu.emu_start(code_start, code_end)
            r3 = self.mu.reg_read(UC_PPC_REG_3)
            return r3
        except UcError as e:
            print("ERROR: %s" % e)



def read_dbcs(dbc_path):
    files = list(dbc_path.glob('generated_*.dbc'))
    dbcs = dict()
    print(f"Scanning generated dbc's")
    for bus_id, bus_name in BUS_IDS.items():
        for f in files:
            if f.stem.split('_')[1] == bus_name:
                print(f'Found: {bus_name}')
                dbcs[bus_id] = cantools.db.load_file(f)
    return dbcs

def find_log_ids_range(gtw_binary):
    pat = re.compile(b'\xd0...\x40', re.MULTILINE | re.DOTALL)
    hits = [hit.start() for hit in pat.finditer(gtw_binary)]
    start, end = None, None
    for i, h in enumerate(hits):
        if hits[i+1] - h == 20:
            start = hits[i]
            break
    for i, h in enumerate(hits[::-1]):
        if h - hits[len(hits) - 2 - i] == 20:
            end = hits[len(hits) - 1 - i] + 20
            break
    if start is None or end is None:
        raise ValueError('Did not find the log ID array!')
    return start, end


def ram2flash(ram_addr):
    return ram_addr - COPY_RAM_START + COPY_FLASH_START


def get_payload_addr(msg_lvl0_offset, flash_data):
    msg_lvl1_fmt = '>28xL' if OLD_FMT else '>24xL4x'
    msg_lvl0_flash_offset = ram2flash(msg_lvl0_offset)
    msg_lvl1_offset = struct.unpack('>L', flash_data[msg_lvl0_flash_offset: msg_lvl0_flash_offset + 4])[0]
    can_payload_addr = struct.unpack(msg_lvl1_fmt,
                                     flash_data[msg_lvl1_offset: msg_lvl1_offset + struct.calcsize(msg_lvl1_fmt)])[0]
    return can_payload_addr


def brute_force_signals(emulator, fcn_ptr, dbc_message, payload_addr):
    for signal in dbc_message.signals:
        test_msg = {sig.name: 0 for sig in dbc_message.signals}
        val = 2**signal.length - 1 if not signal.is_signed else -1  # set all signal bits to 1
        test_msg.update({signal.name: val})
        payload = dbc_message.encode(test_msg, scaling=False, strict=False)
        ret = emulator.emulate_fcn(payload_addr=payload_addr, payload=payload, fcn_ptr=fcn_ptr)

        if ret == 2**signal.length - 1:
            return signal


def main(dbcs, gtw_bin_path, out_path):
    gtw = b'\xff' * GTW_BASE + gtw_bin_path.read_bytes()  # Pad start to allow for indexing without worrying about base address
    can_base_fmt = '>16xLLH18x'
    log_id_fmt = '>LLLLL'

    log_ids_start, log_ids_end = find_log_ids_range(gtw)
    print(hex(log_ids_start), hex(log_ids_end))
    log_id_table = [struct.unpack(log_id_fmt, gtw[i:i+0x14]) for i in range(log_ids_start, log_ids_end, 0x14)]
    msg_states = defaultdict(list)

    for bus_id in range(7):
        can_base_size = struct.calcsize(can_base_fmt)
        can_base = gtw[CAN_BASES + bus_id * can_base_size: CAN_BASES + (bus_id + 1) * can_base_size]
        arbid2internal_ptr, msg_lvl0_ptr, num_ids = struct.unpack(can_base_fmt, can_base)
        arbid2internal = np.frombuffer(gtw[arbid2internal_ptr: arbid2internal_ptr + 2*0x800], dtype='>u2')
        bus_lookup = {arb_id: idx & 0x7fff for arb_id, idx in enumerate(arbid2internal) if (idx & 0x7fff) != 0}
        for arb_id, idx in bus_lookup.items():
            msg_lvl0_size = 24 if OLD_FMT else 16
            msg_lvl0_offset = msg_lvl0_ptr + idx * msg_lvl0_size
            msg_states[msg_lvl0_offset].append((bus_id, arb_id, idx))

    emulator = Emulator(code_flash=gtw_bin_path.read_bytes(),
                        copy_flash_start=COPY_FLASH_START,
                        copy_ram_start=COPY_RAM_START,
                        copy_ram_end=COPY_RAM_END)

    matches = dict()
    for entry in log_id_table:
        log_id, msg_lvl0_offset, _, fcn1, fcn2 = entry
        if msg_lvl0_offset in msg_states:
            hit = msg_states[msg_lvl0_offset][0]
            bus_id, arb_id, idx = hit
            if bus_id in dbcs:
                dbc = dbcs[bus_id]
                try:
                    msg = dbc.get_message_by_frame_id(arb_id)  # Throws KeyError if not found
                    can_payload_addr = get_payload_addr(msg_lvl0_offset, gtw)
                    if msg.is_multiplexed():
                        # TODO maybe suggest candidate signals
                        continue
                    signal = brute_force_signals(emulator, fcn1, msg, can_payload_addr)
                    if signal is not None:
                        match = mapped_sig(BUS_IDS[bus_id],
                                           msg.name,
                                           signal.name,
                                           signal.byte_order,
                                           signal.scale,
                                           signal.offset,
                                           signal.choices,
                                           signal.unit)
                        matches[hex(log_id)] = match
                        print(hex(log_id), match)
                except KeyError:
                    # Arbitration_id not in dbc
                    pass
            else:
                # No dbc for this bus
                pass

    with open(out_path, 'wb') as f:
        pickle.dump(matches, f)


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('gtw_bin_path', help='Path to a matching gtw firmware binary (not hex). Can be found on SD: /release.tgz or squashfs: /deploy/seed_artifacts_v2/gtw ')
    args.add_argument('out_path', help='Path to store output pickle file')
    group = args.add_mutually_exclusive_group(required=True)
    group.add_argument('-dej', help='Path to a squashfs image dej directory: /opt/odin/data/ModelS/dej')
    group.add_argument('-dbc', help="Path to directory of generated dbc's")
    args = args.parse_args()

    if args.dej:
        dej_path = Path(args.dej)
        if not dej_path.exists() or not dej_path.is_dir():
            print(f'Path to dej directory: {dej_path} not found, exiting!')
            exit(1)
        dbcs = read_jsons(dej_path)
    else:
        dbc_path = Path(args.dbc)
        if not dbc_path.exists() or not dbc_path.is_dir():
            print(f'Path to dbc directory: {dbc_path} not found, exiting!')
            exit(1)
        dbcs = read_dbcs(dbc_path)

    gtw_bin_path = Path(args.gtw_bin_path)
    out_path = Path(args.out_path)
    if not gtw_bin_path.exists() or not gtw_bin_path.is_file():
        print(f'Path to gtw binary: {gtw_bin_path} not found, exiting!')
        exit(1)
    main(dbcs, gtw_bin_path, out_path)
