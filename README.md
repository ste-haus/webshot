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
