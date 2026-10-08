# webshot

Take a screenshot of a webpage

Build the image:
```
docker build --platform=linux/amd64 -t ste-haus/webshot .
```

Take a screenshot:
```
docker run --rm \
  -v `pwd`/gitlab.png:/output/webshot.png \
  ste-haus/webshot \
  --url https://gitlab.com \
  --crop_width 500 \
  --crop_height 500
```

`--scale 2` renders the page with two device pixels per CSS pixel, as a HiDPI screen would: the same layout and crop, twice the pixels in each direction, so it stays sharp when shown larger than its CSS size. The crop flags stay in CSS pixels.
