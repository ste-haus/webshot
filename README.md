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

## Capture API

Run it with no flags and it serves an HTTP API instead, taking one capture at a time:
```
docker run -d \
  -p 8080:8080 \
  -v `pwd`/captures:/output \
  ste-haus/webshot
```

`POST /capture` takes a JSON object of the same settings as the flags, without the dashes, plus `output`, a filename the capture is written to inside `/output`:
```
curl -X POST localhost:8080/capture \
  -d '{"url": "https://gitlab.com", "output": "gitlab.png", "crop_width": 500, "crop_height": 500}'
```

The request returns once the image is written: `200` with `{"output": ..., "seconds": ...}`, `400` for a bad request, `500` with `{"output": ..., "error": ...}` when the capture fails, or `504` when it hasn't finished within `REQUEST_TIMEOUT_SECONDS` (the capture carries on). The image is written beside its target and renamed over it, so a reader never sees half an image. A request for a filename that's already queued joins that capture instead of queueing another. `GET /health` answers `200` while the server is up.

| Variable | Default | |
|----------|---------|---|
| `PORT` | `8080` | The port the API listens on |
| `OUTPUT_DIRECTORY` | `/output` | Where `output` filenames are written |
| `REQUEST_TIMEOUT_SECONDS` | `300` | How long a request waits for its capture, queue included |

The API has no authentication, so publish it only where its callers are.
