#!/usr/bin/env python3

import argparse, io, math, os, sys, time
from PIL import Image
from selenium import webdriver

DEFAULT_OUTPUT = '/output/webshot.png'
PAGE_LOAD_TIMEOUT_SECONDS = 60

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

def get_page(browser, delay, url, filename, cropbox=None, duration=-1, framerate=-1):
    print(f"Loading '{url}'... ", flush=True)
    browser.get(url)

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
            frames.append(browser.get_screenshot_as_png())

            next_frame_time = start_time + (i + 1) * interval_seconds
            sleep_time = next_frame_time - time.time()
            if sleep_time > 0:
                time.sleep(sleep_time)

        elapsed = time.time() - start_time
        print(f"Capture completed in {elapsed:.2f} seconds", flush=True)

        frames = convert_png_to_pil(frames)

        if cropbox:
            frames = crop_frames(frames, cropbox)

        save_frames(frames, interval_seconds, filename)

    else:
        browser.save_screenshot(filename)
        if cropbox:
            img = Image.open(filename)
            img = img.crop(cropbox)
            img.save(filename, 'png')


def crop_frames(frames, cropbox):
    """
    Crop all frames to the given cropbox.
    """
    print(f'Cropping {len(frames)} frames...', flush=True)
    return [frame.crop(cropbox) for frame in frames]


def convert_png_to_pil(png_frames):
    frames = []
    for png in png_frames:
        img = Image.open(io.BytesIO(png))
        frames.append(img)

    return frames

def save_frames(frames, interval_seconds, filename):
    print(f'Saving {len(frames)} frames...', flush=True)
    # Convert frames to GIF-compatible palette
    frames = [frame.convert("P", palette=Image.ADAPTIVE, colors=256) for frame in frames]
    frames[0].save(
        filename,
        save_all=True,
        append_images=frames[1:],
        duration=int(interval_seconds * 1000),
        loop=0,
        optimize=False
    )

def make_cropbox(x, y, width, height, scale):
    # The crop is given in CSS pixels; the screenshot is in device pixels
    cropbox = None
    if width > 0 and height > 0:
        left = round(x * scale)
        upper = round(y * scale)
        right = round((x + width) * scale)
        lower = round((y + height) * scale)
        cropbox = (left, upper, right, lower)
        print(f'Cropping to {cropbox}...', flush=True)

    return cropbox

def capture(url, filename, crop_x, crop_y, crop_width, crop_height, browser_width, browser_height, load_delay, duration, framerate, scale):
    cropbox = make_cropbox(crop_x, crop_y, crop_width, crop_height, scale)
    browser = get_browser(browser_width, browser_height, scale)

    try:
        get_page(browser, load_delay, url, filename, cropbox, duration, framerate)
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

    capture(args.url, args.output, **options)

    print(f"Webshot available at '{args.output}'", flush=True)

if __name__ == '__main__':
    # Flags take one webshot and exit; no flags at all serves the capture API
    if len(sys.argv) > 1:
        main()
    else:
        import server
        server.serve()

