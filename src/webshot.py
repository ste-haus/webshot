#!/usr/bin/env python3

import argparse, base64, io, math, os, sys, time
from PIL import Image
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait

DEFAULT_OUTPUT = '/output/webshot.png'
PAGE_LOAD_TIMEOUT_SECONDS = 60
MILLISECONDS_PER_SECOND = 1000

FRAMES_OFF = -1
DURATION_OFF = -1
GIF_EXTENSION = '.gif'
# GIF stores each frame's delay in hundredths of a second
GIF_DELAY_STEP_MS = 10
PALETTE_COLORS = 256
PALETTE_SAMPLE_FRAMES = 4

# A DevTools screenshot clipped to the crop, in CSS pixels at one CSS pixel per CSS pixel, which
# comes back in device pixels as a full-window screenshot does
SCREENSHOT_COMMAND = 'Page.captureScreenshot'
SCREENSHOT_FORMAT = 'png'
CLIP_SCALE = 1

# A page that can be captured frame by frame exposes window.webshotCapture: `ready`, a promise of
# {status, error?}; `durationMs`, its loop's length; and `setTime(ms)`, which resolves once that
# moment is painted. A status other than ready means the page gave up waiting on something and is
# showing what it has.
CAPTURE_STATUS_READY = 'ready'
CAPTURE_INTERFACE_SCRIPT = 'return Boolean(window.webshotCapture)'
AWAIT_CAPTURE_SCRIPT = '''
const done = arguments[arguments.length - 1];
window.webshotCapture.ready.then(
    readiness => done({ok: true, durationMs: window.webshotCapture.durationMs, readiness}),
    error => done({ok: false, error: String(error)})
);
'''
SEEK_CAPTURE_SCRIPT = '''
const timeMs = arguments[0];
const done = arguments[arguments.length - 1];
window.webshotCapture.setTime(timeMs).then(
    () => done({ok: true}),
    error => done({ok: false, error: String(error)})
);
'''

# URL patterns every page's requests to fail immediately, comma separated, with * as a wildcard.
# A request that never answers (a tracker on a blackholed host) otherwise holds the page's load
# event open until the page load times out.
BLOCKED_URLS_VARIABLE = 'BLOCKED_URLS'
BLOCKED_URLS_SEPARATOR = ','
BLOCKED_URLS = [pattern.strip() for pattern in os.environ.get(BLOCKED_URLS_VARIABLE, '').split(BLOCKED_URLS_SEPARATOR) if pattern.strip()]

# The capture settings shared by the CLI flags and the API's JSON body: name, type, default, help
PARAMETERS = [
    ('crop_x', int, 0, 'start cropping at this X coordinate'),
    ('crop_y', int, 0, 'start cropping at this Y coordinate'),
    ('crop_width', int, 500, 'crop to X+width'),
    ('crop_height', int, 500, 'crop to Y+height'),
    ('browser_width', int, 1920, 'the width of the browser window'),
    ('browser_height', int, 1080, 'the height of the browser window'),
    ('load_delay', int, 10, 'wait this many seconds for the URL to load'),
    ('duration', int, -1, 'capture a gif for this many seconds'),
    ('framerate', int, -1, 'if duration is set, cpture a frame on this interval'),
    ('frames', int, FRAMES_OFF, "capture this many frames of the page's webshotCapture loop as a gif"),
    ('scale', float, 1, 'device pixels per CSS pixel: 2 renders the same page twice as sharp, at twice the size'),
]

def get_browser(width, height, scale):
    print(f"Setting up {width}x{height} browser at {scale}x... ", flush=True)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('start-maximized')
    options.add_argument('disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-shm-usage') # overcome limited resource problems
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu --use-gl=swiftshader')
    options.add_argument(f'--window-size={width},{height}')
    # Draws the page with `scale` device pixels per CSS pixel: the same layout, more detail
    options.add_argument(f'--force-device-scale-factor={scale}')

    browser = webdriver.Chrome(options=options)
    browser.set_page_load_timeout(PAGE_LOAD_TIMEOUT_SECONDS)

    if BLOCKED_URLS:
        print(f"Blocking {', '.join(BLOCKED_URLS)}...", flush=True)
        browser.execute_cdp_cmd('Network.enable', {})
        browser.execute_cdp_cmd('Network.setBlockedURLs', {'urls': BLOCKED_URLS})

    return browser

def check(filename, duration, frames):
    if frames == FRAMES_OFF:
        return

    if frames < 1:
        raise ValueError('frames must be a positive number of frames')

    if duration != DURATION_OFF:
        raise ValueError('frames and duration are exclusive')

    if os.path.splitext(filename)[1].lower() != GIF_EXTENSION:
        raise ValueError(f'frames are saved as a gif, so output must end in {GIF_EXTENSION}')

def screenshot(browser, clip, fast=False):
    # Clipped by the browser, so only the crop is read back and encoded rather than the whole
    # window, most of which would be thrown away. `fast` trades size for speed, for frames that
    # are only held until the gif is encoded.
    if clip is None:
        return browser.get_screenshot_as_png()

    params = {'format': SCREENSHOT_FORMAT, 'clip': clip}
    if fast:
        params['optimizeForSpeed'] = True

    return base64.b64decode(browser.execute_cdp_cmd(SCREENSHOT_COMMAND, params)['data'])

def get_page(browser, delay, url, filename, clip=None, duration=-1, framerate=-1, frames=FRAMES_OFF):
    print(f"Loading '{url}'... ", flush=True)
    browser.get(url)

    if frames != FRAMES_OFF:
        return capture_loop(browser, delay, filename, clip, frames)

    if delay:
        print(f'Waiting {delay} seconds for page to load...', flush=True)
        time.sleep(delay)

    if duration > -1:
        frames = []
        interval_seconds = 1 / framerate
        total_frames = math.ceil(framerate * duration)
        print(f'Capturing {total_frames} frames in {duration} seconds ≈ {interval_seconds}s per frame...', flush=True)

        start_time = time.time()

        for i in range(total_frames):
            frames.append(screenshot(browser, clip, fast=True))

            next_frame_time = start_time + (i + 1) * interval_seconds
            sleep_time = next_frame_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

        elapsed = time.time() - start_time
        print(f"Capture completed in {elapsed:.2f} seconds", flush=True)

        save_frames(frames, interval_seconds * MILLISECONDS_PER_SECOND, filename)

    else:
        with open(filename, 'wb') as image:
            image.write(screenshot(browser, clip))


def capture_loop(browser, delay, filename, clip, frame_count):
    # The page decides when it's ready and what each frame shows, so load_delay only bounds how
    # long it may take to offer the interface
    print(f'Waiting up to {delay} seconds for the page to offer webshotCapture...', flush=True)
    try:
        WebDriverWait(browser, delay).until(lambda page: page.execute_script(CAPTURE_INTERFACE_SCRIPT))
    except TimeoutException:
        raise RuntimeError(f'the page offered no webshotCapture within {delay} seconds')

    browser.set_script_timeout(PAGE_LOAD_TIMEOUT_SECONDS)
    capture = browser.execute_async_script(AWAIT_CAPTURE_SCRIPT)
    if not capture['ok']:
        raise RuntimeError(f'the page failed to get ready: {capture["error"]}')

    readiness = capture['readiness']
    if readiness['status'] != CAPTURE_STATUS_READY:
        print(f"The page is {readiness['status']} ({readiness.get('error', 'no error given')}), capturing what it has...", flush=True)

    duration_ms = capture['durationMs']
    interval_ms = duration_ms / frame_count
    if interval_ms % GIF_DELAY_STEP_MS:
        print(f'{interval_ms:g} ms frames will play at {gif_delay(interval_ms)} ms, the nearest a gif can store', flush=True)

    # One loop over [0, duration): a frame at the duration would repeat the first at the seam
    print(f'Capturing {frame_count} frames over its {duration_ms:g} ms loop...', flush=True)
    start_time = time.time()
    # Kept as the PNGs they arrive as until the gif is encoded: decoded, each is several megabytes,
    # and a few hundred of them would exhaust the container's memory
    frames = []
    for index in range(frame_count):
        seek = browser.execute_async_script(SEEK_CAPTURE_SCRIPT, duration_ms * index / frame_count)
        if not seek['ok']:
            raise RuntimeError(f'the page failed to show frame {index}: {seek["error"]}')

        frames.append(screenshot(browser, clip, fast=True))

    print(f'Capture completed in {time.time() - start_time:.2f} seconds', flush=True)

    save_frames(frames, interval_ms, filename)

def decode_frame(png):
    return Image.open(io.BytesIO(png)).convert('RGB')

def gif_delay(interval_ms):
    return round(interval_ms / GIF_DELAY_STEP_MS) * GIF_DELAY_STEP_MS

def save_frames(frames, interval_ms, filename):
    print(f'Saving {len(frames)} frames...', flush=True)

    # One palette, drawn from frames across the capture, for every frame: a pixel that doesn't
    # change then keeps its index, and the gif stores only what moved. A palette per frame differs
    # everywhere and is tens of times the size.
    step = max(1, len(frames) // PALETTE_SAMPLE_FRAMES)
    samples = [decode_frame(png) for png in frames[::step][:PALETTE_SAMPLE_FRAMES]]
    width, height = samples[0].size
    sheet = Image.new('RGB', (width, height * len(samples)))
    for index, sample in enumerate(samples):
        sheet.paste(sample, (0, height * index))
    palette = sheet.quantize(colors=PALETTE_COLORS, method=Image.Quantize.MEDIANCUT)

    # A generator, so each frame is decoded only as the encoder reaches it; the encoder keeps its own
    # copy of every frame, and a list here would hold them all a second time
    indexed = (decode_frame(png).quantize(palette=palette, dither=Image.Dither.NONE) for png in frames)
    next(indexed).save(
        filename,
        save_all=True,
        append_images=indexed,
        duration=gif_delay(interval_ms),
        loop=0,
        optimize=False
    )

def make_clip(x, y, width, height):
    # The crop is given in CSS pixels, as DevTools takes it
    if width <= 0 or height <= 0:
        return None

    print(f'Cropping to {width}x{height} at ({x}, {y})...', flush=True)
    return {'x': x, 'y': y, 'width': width, 'height': height, 'scale': CLIP_SCALE}

def capture(url, filename, crop_x, crop_y, crop_width, crop_height, browser_width, browser_height, load_delay, duration, framerate, frames, scale):
    clip = make_clip(crop_x, crop_y, crop_width, crop_height)
    browser = get_browser(browser_width, browser_height, scale)

    try:
        get_page(browser, load_delay, url, filename, clip, duration, framerate, frames)
    finally:
        browser.quit()

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='the url to capture')
    parser.add_argument('--output', default=DEFAULT_OUTPUT, help='output the webshot at this path')

    for name, kind, default, description in PARAMETERS:
        parser.add_argument(f'--{name}', type=kind, default=default, help=description)

    return parser.parse_args()

def main():
    args = get_args()
    options = {name: getattr(args, name) for name, _, _, _ in PARAMETERS}

    try:
        check(args.output, options['duration'], options['frames'])
    except ValueError as e:
        sys.exit(f'webshot: {e}')

    capture(args.url, args.output, **options)

    print(f"Webshot available at '{args.output}'", flush=True)

if __name__ == '__main__':
    # Flags take one webshot and exit; no flags at all serves the capture API
    if len(sys.argv) > 1:
        main()
    else:
        import server
        server.serve()

