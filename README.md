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

## Animated pages

`--duration` and `--framerate` record a gif in real time: screenshots on a timer, so frame timing drifts with how fast the browser keeps up.

`--frames N` instead captures one loop of a page that offers `window.webshotCapture`, a frame at a time, so every frame lands exactly where it should however long each screenshot takes:

| Member | |
|---|---|
| `ready` | A promise of `{status: 'ready' \| 'timeout' \| 'error', error?}`, resolved once the page has loaded what it needs, or given up waiting and drawn what it has |
| `durationMs` | The length of the page's loop |
| `setTime(ms)` | Shows that moment of the loop, resolving once it's painted |

webshot waits up to `--load_delay` seconds for the interface, then for `ready`, and seeks `N` evenly spaced moments over `[0, durationMs)`, leaving out the end so the gif doesn't repeat its first frame at the seam. Each frame plays for `durationMs / N`, to the nearest 10 ms, the step a gif stores. A status other than `ready` is logged and captured anyway; a page that never offers the interface fails the capture, so the last good image stays in place. `--frames` needs a `.gif` output and can't be combined with `--duration`.
```
docker run --rm \
  -v `pwd`/captures:/output \
  ste-haus/webshot \
  --url 'https://example.com/map/?capture' \
  --output /output/map.gif \
  --frames 180
```

Both kinds of gif share one palette across their frames, so a pixel that doesn't change keeps its value and only what moves is stored.

## Blocking requests

`BLOCKED_URLS` is a comma-separated list of URL patterns, with `*` as a wildcard, whose requests fail immediately in every page captured, in both the CLI and the API:
```
docker run --rm \
  -e BLOCKED_URLS='*google-analytics.com*,*googletagmanager.com*' \
  ...
```

A page's load event waits for every script it adds while loading, including async trackers. Where DNS points a blocked tracker at an address that never answers, the page never finishes loading and the capture times out; blocking the tracker here lets it fail at once. Unset, nothing is blocked.

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
