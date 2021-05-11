import re
import cv2
import convert_videos
import numpy as np
from tqdm import tqdm
from convert_videos import GAMMA, WIDTH, HEIGHT
from pathlib import Path
from argparse import ArgumentParser

REGISTER_BASE = 0x3000

def get_reg(regs, addr):
    start = addr - REGISTER_BASE
    return regs[start//2]

def reg_get_bits(regs, addr, startbit, bitlength):
    val = get_reg(regs, addr)
    mask = (1 << bitlength) - 1
    return (val >> startbit) & mask

def reg_get_flag(regs, addr, bit):
    val = get_reg(regs, addr)
    return 0 != (val & (1<<bit))

def decode_reg_field(data, leftcheck=0x5a, rightcheck=0x5a):
    assert data[0] == leftcheck and data[2] == rightcheck, 'Invalid register data'
    return data[1] << 8 | data[3]

def reg_decode_data(registers, raw, start, regsCount):
    data = raw[start:]
    start_addr = decode_reg_field(data[:4], leftcheck=0xaa, rightcheck=0xa5)
    reg_offset = (start_addr - REGISTER_BASE) // 2
    for i in range(regsCount):
        val = decode_reg_field(data[4+i*4: 8+i*4])
        registers[reg_offset + i] = val

def load_regs(raw, shift):
    data = np.frombuffer(raw, dtype=np.uint16)
    data = np.right_shift(data, 4 - shift)
    assert data[0] == 0xa, 'Invalid register data'
    registers = np.zeros(256, dtype=np.uint16)
    reg_decode_data(registers, data, 1, 152)
    reg_decode_data(registers, data, 1280 + 1, 69)
    reg_decode_data(registers, data, 1280 + 1 + 280, 24)
    return registers


def decompressImage(data, registers):
    assert data.shape == (HEIGHT, WIDTH), 'Wrong shape'
    pedestal = get_reg(registers, 0x301e)
    P1 = 1 << reg_get_bits(registers, 0x319a, 0, 5)
    P2 = 1 << reg_get_bits(registers, 0x319a, 8, 5)
    Pmax = 1 << reg_get_bits(registers, 0x319c, 0, 5)
    R1 = 4 << reg_get_bits(registers, 0x3082, 2, 2)
    R2 = 4 << reg_get_bits(registers, 0x3082, 4, 2)
    pointsInvalid = (pedestal < 0 or pedestal > 2048 or
                     P1 < 512 or P1 > 16384 or P1 <= pedestal or
                     P2 < 1024 or P2 > 1048576 or P2 <= P1 or
                     Pmax < 16384 or Pmax <= P2 or
                     R1 < 1 or R1 > 64 or
                     R2 < 1 or R2 > 64)
    assert not pointsInvalid, 'Invalid points'
    HDRCompand14bit = reg_get_flag(registers, 0x31d0, 1)

    # raw_data_shift = 0 if HDRCompand14bit else -2
    f = 1 if HDRCompand14bit else 4
    hdrMin = pedestal
    hdrK1 = P1
    hdrK2 = (P2 - P1) / (R1 * f) + hdrK1
    hdrK3 = (Pmax - P2) / (R1 * R2 * f) + hdrK2
    line_time = get_reg(registers, 0x300c)
    exposure_t1 = get_reg(registers, 0x30ac)
    exposure_t2 = get_reg(registers, 0x307c)
    exposure_t3 = get_reg(registers, 0x3080)
    t1to2Factor = exposure_t1 / exposure_t2
    t2to3Factor = exposure_t2 / ((exposure_t3 + 512) / line_time)

    k1Factor = 1.0 / (hdrK1 - hdrMin)
    k2Factor = 1.0 / (hdrK2 - hdrK1)
    k3Factor = 1.0 / (hdrK3 - hdrK2)
    f1 = 1.0
    f2 = f1 * t1to2Factor
    f3 = f2 * t2to3Factor
    fsum = f1 + f2 + f3
    f1 /= fsum
    f2 /= fsum
    f3 /= fsum

    # Actual decompression
    data = data.astype('float64')
    v1 = np.clip((data - hdrMin) * k1Factor, 0, 1.0)
    v2 = np.clip((data - hdrK1) * k2Factor, 0, 1.0)
    v3 = np.clip((data - hdrK2) * k3Factor, 0, 1.0)
    v = v1 * f1 + v2 * f2 + v3 * f3
    v = np.clip(v, 0, 1.0)
    return v


def auto_white_balance(frame, bits=10):
    green = (frame[::2, ::2] + frame[1::2, 1::2]) / 2
    red = frame[::2, 1::2]
    blue = frame[1::2, ::2]

    greenhist, _ = np.histogram(green.flatten(), 2**bits, [0, 2**bits])
    redhist, _ = np.histogram(red.flatten(), 2**bits, [0, 2**bits])
    bluehist, _ = np.histogram(blue.flatten(), 2**bits, [0, 2**bits])
    greencdf = convert_videos.calculate_cdf(greenhist)
    redcdf = convert_videos.calculate_cdf(redhist)
    bluecdf = convert_videos.calculate_cdf(bluehist)

    red_lookup = convert_videos.calculate_lookup(redcdf, greencdf, bits=bits)
    blue_lookup = convert_videos.calculate_lookup(bluecdf, greencdf, bits=bits)
    red_fixed = red_lookup[red.astype(np.uint16)]
    blue_fixed = blue_lookup[blue.astype(np.uint16)]
    frame[::2, 1::2] = red_fixed
    frame[1::2, ::2] = blue_fixed
    return frame


def convert_image(image_path, out_path):
    assert not out_path.exists(), f'File {out_path} already exists!'
    raw = np.fromfile(image_path, dtype=np.uint16)
    raw_frame = raw.reshape((HEIGHT + 4, WIDTH))
    registers = load_regs(raw_frame[:2, :].flatten(), -2)
    shifted_frame = np.right_shift(raw_frame[2:-2, :], 2)
    decompressed_frame = decompressImage(shifted_frame, registers)
    decompressed_frame = np.clip(decompressed_frame * 2**12, 0, 2**12).astype(np.uint16)
    range_min, range_max = convert_videos.findImageMinMax(decompressed_frame)
    balanced_frame = auto_white_balance(decompressed_frame, bits=12)
    demosaiced_frame = cv2.cvtColor(balanced_frame, cv2.COLOR_BAYER_GB2RGB)
    lut = convert_videos.calc_enhancement_LUT(range_min, range_max * 1.5, GAMMA)
    processed = lut[demosaiced_frame]
    cv2.imwrite(str(out_path), cv2.cvtColor(processed, cv2.COLOR_RGB2BGR))


def main(images_dir, out_dir):
    name_pat = re.compile('(\w+)-(\w+)\.*')
    images = list(images_dir.glob('*.img.data'))
    for child in tqdm(images, desc='Converting images'):
        timestamp, frame_no = re.search(name_pat, child.name).groups()
        timestamp = int(timestamp, 16)/1e9
        frame_no = int(frame_no, 16)
        convert_image(child, out_dir / (f'{timestamp:0.2f}-{frame_no}.bmp'))


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('images_dir', help='Path to camera images directory')
    args.add_argument('out_dir', help='Path to output dir. Will create it if the directory does not exist')
    args = args.parse_args()
    images_dir = Path(args.images_dir)
    out_dir = Path(args.out_dir)
    if not images_dir.exists() or not images_dir.is_dir():
        print('Invalid snapshot_dir, exiting.')
        exit(1)
    if not out_dir.exists():
        out_dir.mkdir()
    main(images_dir, out_dir)
