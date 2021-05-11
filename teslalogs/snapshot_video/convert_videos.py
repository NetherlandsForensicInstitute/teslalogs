import time
import json
import tempfile
import re
import ffmpeg
import cv2
import numpy as np
import pandas as pd
from pathlib import Path
from tqdm import tqdm
from argparse import ArgumentParser

WIDTH = 1280
HEIGHT = 960
GAMMA = 0.5
SYNC_FRAMERATE = 36
AUTORANGELOWDROPOUT = 0.0035
AUTORANGEHIGHDROPOUT = 0.007


def merge_quadrants(frame):
    assert frame.shape == (HEIGHT, WIDTH), 'Invalid frame shape'
    top, bottom = np.split(frame, 2, axis=0)
    TL, TR = np.split(top, 2, axis=1)
    BL, BR = np.split(bottom, 2, axis=1)
    new_frame = np.zeros_like(frame)
    new_frame[0::2, 0::2] = TL
    new_frame[0::2, 1::2] = TR
    new_frame[1::2, 0::2] = BL
    new_frame[1::2, 1::2] = BR
    return new_frame


def convertImageForDisplay(frame, minRange, maxRange, gamma):
    frame = frame.astype(np.float64)
    factor = 1.0 / (maxRange - minRange)
    new_frame = (frame - minRange) * factor
    new_frame = np.power(new_frame, gamma)
    return np.clip(new_frame * 255, 0, 255).astype('uint8')


def calculate_cdf(histogram):
    cdf = histogram.cumsum()
    normalized_cdf = cdf / float(cdf.max())

    return normalized_cdf


def calculate_lookup(src_cdf, ref_cdf, bits=10):
    lookup_table = np.zeros(2**bits)
    lookup_val = 0
    for src_pixel_val in range(len(src_cdf)):
        for ref_pixel_val in range(len(ref_cdf)):
            if ref_cdf[ref_pixel_val] >= src_cdf[src_pixel_val]:
                lookup_val = ref_pixel_val
                break
        lookup_table[src_pixel_val] = lookup_val
    return lookup_table


def findImageMinMax(frame, darkDropoutFactor=AUTORANGELOWDROPOUT, brightDropoutFactor=AUTORANGEHIGHDROPOUT):
    hMargin = WIDTH // 16
    topMargin = HEIGHT // 10
    bottomMargin = HEIGHT // 4
    histsize = 0x8000

    region = frame[topMargin: HEIGHT - bottomMargin, hMargin: WIDTH - hMargin]
    region_min = region.min()
    region_max = region.max()

    hist, bins = np.histogram(frame, histsize)
    cdf_normalized = calculate_cdf(hist)
    max_idx = len(cdf_normalized[cdf_normalized <= (1 - brightDropoutFactor)])
    min_idx = len(cdf_normalized[cdf_normalized <= (darkDropoutFactor)])
    factor = (region_max - region_min) / histsize
    return region_min + min_idx * factor, region_min + max_idx * factor


def read_h265(in_file):
    out, err = (ffmpeg
                .input(in_file.name)
                .output('pipe:', format='rawvideo', pix_fmt='yuv420p10le')
                .global_args('-loglevel', 'fatal')
                .run(capture_stdout=True))
    # The quarter frame sized U and V planes are empty
    video = np.frombuffer(out, np.uint16).reshape([-1, int(HEIGHT * 1.5), WIDTH])[:, :HEIGHT, :]
    return video


def first_pass(video):
    num_frames = video.shape[0]
    merged_vid = np.zeros((num_frames, HEIGHT, WIDTH), dtype=np.uint16)
    rolling_min = np.zeros(num_frames)
    rolling_max = np.zeros(num_frames)

    for frame_idx in tqdm(range(num_frames), desc='Processing frames'):
        merged_frame = merge_quadrants(video[frame_idx, :, :])
        range_min, range_max = findImageMinMax(merged_frame.astype(np.float64),
                                               darkDropoutFactor=0, brightDropoutFactor=0.01)
        merged_vid[frame_idx, :, :] = merged_frame
        rolling_min[frame_idx] = range_min
        rolling_max[frame_idx] = range_max
    range_min = np.median(rolling_min)
    range_max = np.median(rolling_max)
    return merged_vid, range_min, range_max


def demosaic_vid(merged_vid):
    num_frames = merged_vid.shape[0]
    demosaiced_vid = np.zeros((num_frames, HEIGHT, WIDTH, 3), dtype=np.uint16)

    for frame_idx in tqdm(range(num_frames), desc='Demosaicing frames'):
        merged_frame = merged_vid[frame_idx, :, :]
        demosaiced_frame = cv2.cvtColor(merged_frame, cv2.COLOR_BAYER_GB2RGB)
        demosaiced_vid[frame_idx, :, :, :] = demosaiced_frame
    return demosaiced_vid


def write_vid(processed_vid, out_file):
    num_frames = processed_vid.shape[0]
    process = (ffmpeg
               .input('pipe:', format='rawvideo', pix_fmt='rgb24', s='{}x{}'.format(WIDTH, HEIGHT), r=SYNC_FRAMERATE)
               .drawtext(text=Path(out_file).stem, fontcolor='white', fontsize=20, box=1, boxcolor='black@0.5',
                         boxborderw=5, x='(w-text_w)/2', y='(text_h)/2')
               .output(str(out_file), pix_fmt='yuv420p')
               .global_args('-loglevel', 'fatal')
               .overwrite_output()
               .run_async(pipe_stdin=True))

    for frame in tqdm(range(num_frames), desc=f'Writing to: {out_file}'):
        out_frame = processed_vid[frame, :, :, :]
        process.stdin.write(out_frame.tobytes())
    process.stdin.close()


def auto_white_balance(merged_vid, bits=10):
    print('Auto white-balancing...')
    greenvid = (merged_vid[:, ::2, ::2] + merged_vid[:, 1::2, 1::2]) / 2
    redvid = merged_vid[:, ::2, 1::2]
    bluevid = merged_vid[:, 1::2, ::2]

    greenhist, _ = np.histogram(greenvid.flatten(), 2**bits, [0, 2**bits])
    redhist, _ = np.histogram(redvid.flatten(), 2**bits, [0, 2**bits])
    bluehist, _ = np.histogram(bluevid.flatten(), 2**bits, [0, 2**bits])
    greencdf = calculate_cdf(greenhist)
    redcdf = calculate_cdf(redhist)
    bluecdf = calculate_cdf(bluehist)

    red_lookup = calculate_lookup(redcdf, greencdf, bits=bits)
    blue_lookup = calculate_lookup(bluecdf, greencdf, bits=bits)
    red_fixed = red_lookup[redvid.astype(np.uint16)]
    blue_fixed = blue_lookup[bluevid.astype(np.uint16)]
    merged_vid[:, ::2, 1::2] = red_fixed
    merged_vid[:, 1::2, ::2] = blue_fixed
    return merged_vid


def build_index_from_file(index_path, has_metalines=True):
    index_fmt = np.dtype([('seconds', '<u2'),
                          ('pad1', 'V6'),
                          ('nanoseconds', '<u4'),
                          ('pad2', 'V4'),
                          ('offset', '<u4'),
                          ('pad3', 'V4'),
                          ('length', '<u4'),
                          ('pad4', 'V4')])
    indices = pd.DataFrame(np.fromfile(index_path, dtype=index_fmt))
    data_path = Path(index_path).parent / 'data.img'
    if not data_path.exists():
        data_path = Path(index_path).parent / 'data.h265'
    if not data_path.exists():
        print('Did not find video data, exiting.')
        exit(1)
    indices['frame_path'] = data_path
    indices['timestamp'] = indices['seconds'] + indices['nanoseconds'] / 1e9

    metalines_size = WIDTH * 2 * 4  # 4 rows of 16bit register values
    if not has_metalines:
        metalines_size = 0

    indices['frame_offset'] = indices['offset'] + metalines_size
    indices['frame_length'] = indices['length'] - metalines_size
    indices['metalines_path'] = data_path
    indices['metalines_offset'] = indices['offset']
    indices['metalines_length'] = metalines_size
    return indices[['timestamp', 'frame_path', 'frame_offset', 'frame_length',
                    'metalines_path', 'metalines_offset', 'metalines_length']]


def gen_replay_rows(replay_dir):
    name_pat = re.compile(r'(\w+)-(\w+)\.*')
    replay_dir = Path(replay_dir)
    for frame in sorted(replay_dir.glob('*.h265')):
        metalines = frame.parent / (frame.name.split('.')[0] + '.img.metalines')
        assert metalines.exists(), 'Did not find matching metalines file'
        hit = re.search(name_pat, frame.name)
        timestamp = int(hit.group(1), 16) / 1e9
        yield {'timestamp': timestamp,
               'frame_path': frame,
               'frame_offset': 0,
               'frame_length': frame.stat().st_size,
               'metalines_path': metalines,
               'metalines_offset': 0,
               'metalines_length': metalines.stat().st_size}


def build_index_from_replay_dir(replay_dir):
    return pd.DataFrame(gen_replay_rows(replay_dir))


def sync_vid(video, timestamps, t_start, t_end, sync_framerate):
    if len(timestamps) > video.shape[0]:
        timestamps = timestamps[:video.shape[0]]
    sync_time = np.arange(0, np.ceil(t_end - t_start) * sync_framerate) / sync_framerate + t_start
    synced_vid = np.zeros((len(sync_time), video.shape[1], video.shape[2], 3), dtype=np.uint8)
    for i, t in tqdm(enumerate(sync_time), desc='Synchronizing frames'):
        frame_idx = abs(timestamps - t).argmin()
        if frame_idx != 0:  # nearest is first frame, show black (Already initialized to zeros)
            synced_vid[i, :, :, :] = video[frame_idx, :, :, :]
    return synced_vid


def process_new_backup(in_file, out_file):
    print('Converting backup with ffmpeg...')
    out, err = (ffmpeg
                .input(in_file, r=30)
                .filter('scale', size=f'{WIDTH}:{HEIGHT}', force_original_aspect_ratio=f'decrease')
                .filter('pad', width=WIDTH, height=HEIGHT, x='(ow-iw)/2', y='(oh-ih)/2')
                .output(str(out_file), pix_fmt='yuv420p')
                .overwrite_output()
                .global_args('-loglevel', 'fatal')
                .run())
    print(f'Loading {out_file}...')
    out, err = (ffmpeg
                .input(out_file)
                .output('pipe:', format='rawvideo', pix_fmt='rgb24')
                .run(capture_stdout=True))
    video = np.frombuffer(out, np.uint8).reshape([-1, HEIGHT, WIDTH, 3])
    return video


def calc_enhancement_LUT(range_min, range_max, gamma):
    x = np.arange(0, 2 ** 16, dtype=np.uint16).astype(np.float64)
    factor = 1 / (range_max - range_min)
    y = np.clip((x - range_min) * factor, 0, 1)
    lut = np.clip(np.power(y, gamma) * 255, 0, 255).astype(np.uint8)
    return lut


def process_vid(in_file):
    video = read_h265(in_file)
    merged_vid, range_min, range_max = first_pass(video)
    merged_vid = auto_white_balance(merged_vid)
    demosaiced_vid = demosaic_vid(merged_vid)
    return demosaiced_vid, range_min, range_max


def convert_vids(snapshot_dir, out_dir):
    assert (snapshot_dir / 'archive_info.json').exists(), 'Did not find archive_info.json!'
    archive_info = json.loads((snapshot_dir / 'archive_info.json').read_text())
    camera_indices = dict()
    camera_ranges = dict()
    sync_framerate = 36
    set_min_range, set_max_range = 0, 0
    shown_cams = ['main', 'rightpillar', 'leftpillar', 'rightrepeater', 'backup', 'leftrepeater']

    # the snapshot layout and structure varies over SW versions, so we check the ones we know of:
    # Step 1, build an index of the video data
    if 'tclip' in (child.name for child in snapshot_dir.iterdir()):
        assert (snapshot_dir / 'tclip/img').exists(), 'Did not find tclip/img directory'
        for cam_path in (snapshot_dir / 'tclip/img').iterdir():
            cam = cam_path.name.split('_')[0]
            if cam in shown_cams:
                has_metalines = True
                if cam == 'backup':  # The backup cam can be different than the other 7
                    has_metalines = int(archive_info['cameras']['backup']['width']) == WIDTH
                index = build_index_from_file(cam_path / 'index', has_metalines=has_metalines)
                camera_indices[cam] = index
    elif 'img' in (child.name for child in snapshot_dir.iterdir()):
        for cam_path in filter(lambda x: x.name.endswith('_replay'), (snapshot_dir / 'img').iterdir()):
            cam = cam_path.name.split('_')[0]
            if cam in shown_cams:
                index = build_index_from_replay_dir(cam_path)
                camera_indices[cam] = index

    t_start = min([df['timestamp'].min() for df in camera_indices.values()])  # Show all footage
    # t_start = max([df['timestamp'].min() for df in camera_timestamps.values()])  # Start when all cams have footage
    t_end = max([df['timestamp'].max() for df in camera_indices.values()])
    sync_time = np.arange(0, np.ceil(t_end - t_start) * sync_framerate) / sync_framerate + t_start
    (out_dir / 'time_info.txt').write_text(','.join(str(t) for t in sync_time))  # Needed for further analysis

    # Step 2, process each video
    for cam in shown_cams:
        index = camera_indices[cam]
        with tempfile.NamedTemporaryFile('wb') as temp_file:
            for _, (frame_path, frame_offset, frame_length) in \
                    index[['frame_path', 'frame_offset', 'frame_length']].iterrows():
                with open(frame_path, 'rb') as frame_file:
                    frame_file.seek(frame_offset, 0)
                    data = frame_file.read(frame_length)
                    temp_file.write(data)

            if not (out_dir / f'{cam}.mp4').exists():
                vid_framerate = round(1 / index['timestamp'].diff().median())
                if cam == 'backup' and ffmpeg.probe(temp_file.name)['streams'][0]['width'] != WIDTH:
                    assert vid_framerate == 30, 'Not encountered this framerate before'
                    processed = process_new_backup(temp_file.name, out_dir / f'{cam}.mp4')
                else:
                    assert vid_framerate == sync_framerate, 'Not encountered this framerate before'
                    print(f'Loading {cam}...')
                    demosaiced_vid, range_min, range_max = process_vid(temp_file)
                    camera_ranges[cam] = (range_min, range_max)

                    if cam == 'main':  # Match intensity range of all cams to main
                        set_min_range, set_max_range = range_min, range_max
                    range_min = set_min_range if set_min_range else range_min
                    range_max = set_max_range if set_max_range else range_max

                    print('Enhancing video for display...')
                    lut = calc_enhancement_LUT(range_min, range_max * 1.5, GAMMA)
                    processed = lut[demosaiced_vid]
                synced_vid = sync_vid(processed, index['timestamp'], t_start, t_end, sync_framerate)
                write_vid(synced_vid, out_dir / f'{cam}.mp4')
                print(f'Finished {cam}\n')


def create_overview(out_dir):
    print('Creating overview vid...')
    frontvids = ['leftpillar', 'main', 'rightpillar']
    rearvids = ['leftrepeater', 'backup', 'rightrepeater']
    front = ffmpeg.filter([ffmpeg.input(Path(out_dir) / f'{f}.mp4') for f in frontvids], 'hstack', inputs=3)
    rear = ffmpeg.filter([ffmpeg.input(Path(out_dir) / f'{r}.mp4') for r in rearvids], 'hstack', inputs=3)
    out = (ffmpeg
           .filter([front, rear], 'vstack', inputs=2)
           .output(str(out_dir / 'overview.mp4'))
           .global_args('-loglevel', 'fatal')
           .overwrite_output()
           .run())
    print('Done')


def downscale_overview(out_dir):
    in_file = out_dir / 'overview.mp4'
    probe = ffmpeg.probe(str(in_file))
    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    width = int(video_stream['width'])
    height = int(video_stream['height'])
    print('Creating downscaled overview...')

    # Downscale pixels and insert more keyframes for responsive seeking in visualisations
    out, err = (ffmpeg
                .input(out_dir / 'overview.mp4')
                .filter('scale', size=f'{width//2}:{height//2}', force_original_aspect_ratio=f'decrease')
                .output(str(out_dir / 'overview_downscaled.mp4'), pix_fmt='yuv420p', x264opts='keyint=10')
                .overwrite_output()
                .global_args('-loglevel', 'fatal')
                .run())
    print('Done')


def main(snapshot_dir, out_dir):
    convert_vids(snapshot_dir, out_dir)
    time.sleep(1)  # Some race condition with files not finished up?
    create_overview(out_dir)
    time.sleep(1)  # Some race condition with files not finished up?
    downscale_overview(out_dir)


if __name__ == '__main__':
    args = ArgumentParser()
    args.add_argument('snapshot_dir', help='Path to snapshot')
    args.add_argument('out_dir', help='Path to output dir. Will create it if the directory does not exist')
    args = args.parse_args()
    snapshot_dir = Path(args.snapshot_dir)
    out_dir = Path(args.out_dir)
    if not snapshot_dir.exists() or not snapshot_dir.is_dir():
        print('Invalid snapshot_dir, exiting.')
        exit(1)
    if not out_dir.exists():
        out_dir.mkdir()
    main(snapshot_dir, out_dir)
