#!/usr/bin/env python3

import argparse, glob, io, math, os, sys, time, uuid
from PIL import Image
from selenium import webdriver 

def get_browser(width, height):
    print(f"Setting up {width}x{height} browser... ", flush=True)
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('start-maximized')
    options.add_argument('disable-infobars')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-dev-shm-usage') # overcome limited resource problems
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-gpu --use-gl=swiftshader')
    options.add_argument(f'--window-size={width},{height}')

    browser = webdriver.Chrome(options=options)

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

    browser.quit()


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

def make_cropbox(x, y, width, height):
    cropbox = None
    if width > 0 and height > 0:
        left = x
        upper = y
        right = x + width
        lower = y + height
        cropbox = (left, upper, right, lower)
        print(f'Cropping to {cropbox}...', flush=True)

    return cropbox

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='the url to capture')
    parser.add_argument('--output', default='/output/webshot.png', help='output the webshot at this path')
    parser.add_argument('--crop_x', type=int, default=0, help='start cropping at this X coordinate')
    parser.add_argument('--crop_y', type=int, default=0, help='start cropping at this Y coordinate')
    parser.add_argument('--crop_width', type=int, default=500, help='crop to X+width')
    parser.add_argument('--crop_height', type=int, default=500, help='crop to Y+height')
    parser.add_argument('--browser_width', default=1920, type=int, help='the width of the browser window')
    parser.add_argument('--browser_height', default=1080, type=int, help='the height of the browser window')
    parser.add_argument('--load_delay', default=10, type=int, help='wait this many seconds for the URL to load')
    parser.add_argument('--duration', default=-1, type=int, help='capture a gif for this many seconds')
    parser.add_argument('--framerate', default=-1, type=int, help='if duration is set, cpture a frame on this interval')

    return parser.parse_args()

args = get_args()

cropbox = make_cropbox(args.crop_x, args.crop_y, args.crop_width, args.crop_height)
browser = get_browser(args.browser_width, args.browser_height)
get_page(browser, args.load_delay, args.url, args.output, cropbox, args.duration, args.framerate)

print(f"Webshot available at '{args.output}'", flush=True)

