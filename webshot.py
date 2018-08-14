#!/usr/bin/env python3

import glob, os, sys, time, uuid
from PIL import Image
from selenium import webdriver 

target = 'webshot.png'
source = sys.argv[1]

crop = None
if len(sys.argv) == 4:
    crop = (0, 0, int(sys.argv[2]), int(sys.argv[3]))
elif len(sys.argv) == 6:
    crop = (int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]))

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument("start-maximized");
options.add_argument("disable-infobars");
options.add_argument("--disable-extensions");
options.add_argument("--disable-dev-shm-usage"); # overcome limited resource problems
options.add_argument("--no-sandbox");

# open in webpage
driver = webdriver.Chrome(chrome_options=options)
driver.get(source)

time.sleep(3)

driver.save_screenshot(target)
driver.quit()

# crop as required
if crop != None:
    img = Image.open(target)
    area = img.crop(crop)
    area.save(target, 'png')
