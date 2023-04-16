#!/usr/bin/env python3

import argparse, glob, os, sys, time, uuid
from PIL import Image
from selenium import webdriver 

def get_browser(width, height):
    print(f"Setting up {width}x{height} browser... ", end = '', flush=True)
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

    print('done.', flush=True)

    return browser

def get_page(browser, delay, url, filename):
    print(f"Loading '{url}'... ", end = '', flush=True)
    browser.get(url)
    time.sleep(delay)
    browser.save_screenshot(filename)
    browser.quit()
    print('done.', flush=True)

def crop(x, y, width, height, filename):
    if width != None and height != None:
        print(f"Cropping ({x}, {y}), ({x+width}, {y+height})... ", flush=True)
        crop = (x, y, width, height)
        img = Image.open(filename)
        area = img.crop(crop)
        area.save(filename, 'png')
        print('done.', flush=True)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', required=True, help='the url to capture')
    parser.add_argument('--output', default='/output/webshot.png', help='output the webshot at this path')
    parser.add_argument('--crop_x', type=int, default=0, help='start cropping at this X coordinate')
    parser.add_argument('--crop_y', type=int, default=0, help='start cropping at this Y coordinate')
    parser.add_argument('--crop_width', type=int, help='crop to X+width')
    parser.add_argument('--crop_height', type=int, help='crop to Y+height')
    parser.add_argument('--browser_width', default=1920, type=int, help='the width of the browser window')
    parser.add_argument('--browser_height', default=1080, type=int, help='the height of the browser window')
    parser.add_argument('--load_delay', default=10, type=int, help='wait this many seconds for the URL to load')

    return parser.parse_args()

args = get_args()
browser = get_browser(args.browser_width, args.browser_height)
get_page(browser, args.load_delay, args.url, args.output)
crop(args.crop_x, args.crop_y, args.crop_width, args.crop_height, args.output)

print(f"Webshot available at '{args.output}'", flush=True)

