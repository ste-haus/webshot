import json, os, queue, threading, time, uuid
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from webshot import PARAMETERS, capture, check

PORT = int(os.environ.get('PORT', '8080'))
OUTPUT_DIRECTORY = os.environ.get('OUTPUT_DIRECTORY', '/output')
# How long a request waits for its capture, queue included, before answering 504; the capture carries on
REQUEST_TIMEOUT_SECONDS = int(os.environ.get('REQUEST_TIMEOUT_SECONDS', '300'))

CAPTURE_PATH = '/capture'
HEALTH_PATH = '/health'
HIDDEN_PREFIX = '.'

class Capture:
    def __init__(self, url, filename, options):
        self.url = url
        self.filename = filename
        self.options = options
        self.done = threading.Event()
        self.error = None
        self.seconds = None

# One capture at a time, each its own Chromium. A request for a filename that's already waiting
# joins that capture rather than queueing another.
_queue = queue.Queue()
_waiting = {}
_lock = threading.Lock()

def submit(url, filename, options):
    with _lock:
        pending = _waiting.get(filename)
        if pending:
            print(f"Joining the queued capture of '{filename}'", flush=True)
            return pending

        job = Capture(url, filename, options)
        _waiting[filename] = job
        _queue.put(job)

        return job

def work():
    while True:
        job = _queue.get()
        with _lock:
            del _waiting[job.filename]

        started = time.monotonic()
        try:
            write_atomically(job)
        except Exception as e:
            # Selenium's messages carry a stacktrace after the first line
            lines = str(e).strip().splitlines()
            job.error = f'{type(e).__name__}: {lines[0] if lines else ""}'
            print(f"Capturing '{job.filename}' failed: {job.error}", flush=True)

        job.seconds = time.monotonic() - started
        job.done.set()

def write_atomically(job):
    # Written beside the target and renamed over it, so a reader never sees half an image. The
    # temporary keeps the extension, which picks the image format.
    stem, extension = os.path.splitext(job.filename)
    temporary = os.path.join(OUTPUT_DIRECTORY, f'{HIDDEN_PREFIX}{stem}.{uuid.uuid4().hex}{extension}')

    try:
        capture(job.url, temporary, **job.options)
        os.replace(temporary, os.path.join(OUTPUT_DIRECTORY, job.filename))
        print(f"Webshot available at '{job.filename}'", flush=True)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)

def parse(body):
    if not isinstance(body, dict):
        raise ValueError('the body must be a JSON object')

    url = body.get('url')
    if not isinstance(url, str) or not url:
        raise ValueError('url is required')

    filename = body.get('output')
    if not isinstance(filename, str) or os.path.basename(filename) != filename or filename.startswith(HIDDEN_PREFIX):
        raise ValueError('output must be a plain filename, with no directory and no leading dot')

    known = {'url', 'output'} | {name for name, _, _, _ in PARAMETERS}
    unknown = sorted(set(body) - known)
    if unknown:
        raise ValueError(f'unknown parameters: {", ".join(unknown)}')

    options = {}
    for name, kind, default, _ in PARAMETERS:
        value = body.get(name, default)
        # bool is an int in Python, but true is no crop width
        if isinstance(value, bool) or not isinstance(value, (int, float)) or (kind is int and not float(value).is_integer()):
            raise ValueError(f'{name} must be {"an integer" if kind is int else "a number"}')

        options[name] = kind(value)

    check(filename, options['duration'], options['frames'])

    return url, filename, options

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != HEALTH_PATH:
            return self.respond(HTTPStatus.NOT_FOUND, {'error': f'no such path: {self.path}'})

        self.respond(HTTPStatus.OK, {'status': 'ok'})

    def do_POST(self):
        if self.path != CAPTURE_PATH:
            return self.respond(HTTPStatus.NOT_FOUND, {'error': f'no such path: {self.path}'})

        try:
            length = int(self.headers.get('Content-Length', 0))
            url, filename, options = parse(json.loads(self.rfile.read(length)))
        except ValueError as e:
            return self.respond(HTTPStatus.BAD_REQUEST, {'error': str(e)})

        job = submit(url, filename, options)

        if not job.done.wait(REQUEST_TIMEOUT_SECONDS):
            return self.respond(HTTPStatus.GATEWAY_TIMEOUT, {'output': filename, 'error': f'not captured within {REQUEST_TIMEOUT_SECONDS} seconds'})

        if job.error:
            return self.respond(HTTPStatus.INTERNAL_SERVER_ERROR, {'output': filename, 'error': job.error})

        self.respond(HTTPStatus.OK, {'output': filename, 'seconds': round(job.seconds, 1)})

    def respond(self, status, body):
        payload = json.dumps(body).encode()

        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

def serve():
    threading.Thread(target=work, daemon=True).start()

    print(f"Serving captures into '{OUTPUT_DIRECTORY}' on port {PORT}...", flush=True)
    ThreadingHTTPServer(('', PORT), Handler).serve_forever()
