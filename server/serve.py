"""
serve.py — Static file server for the GLEN LST Agent web app.

Serves the app/ web root over HTTP with:
  * HTTP Range support (required for PMTiles and Parquet streaming)
  * CORS headers (Access-Control-Allow-Origin: *) so cross-origin tile
    fetches and the browser MCP client work without a proxy
  * an optional basemap external-root mapping so the Tokyo OSM PMTiles can be
    served from its original location without copying the ~197 MB file.

Usage:
    python serve.py [port] [web_root] [basemap_external_dir]

Environment overrides:
    GLEN_SERVE_PORT       port (default 8000)
    GLEN_WEB_ROOT         web root (default <project>/app)
    GLEN_BASEMAP_EXT      external basemap dir checked when app/data/basemap
                          does not contain the file (default:
                          F:\\TokyoLSTAgent\\geo-app\\basemap)
"""

import os
import re
import socket
import sys
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WEB_ROOT = PROJECT_ROOT / "app"
DEFAULT_BASEMAP_EXT = Path(r"F:\TokyoLSTAgent\geo-app\basemap")

RANGE_RE = re.compile(r"bytes=(\d*)-(\d*)")


class RangeRequestHandler(SimpleHTTPRequestHandler):
    """SimpleHTTPRequestHandler with HTTP Range + CORS + external roots."""

    # ---- helpers -------------------------------------------------------

    def _resolve(self, url_path):
        """Resolve a URL path to a filesystem path, or None.

        Order: web root first, then extra roots (e.g. external basemap dir).
        """
        clean = url_path.split("?", 1)[0].split("#", 1)[0]
        try:
            Path(clean).relative_to("/")
        except ValueError:
            return None
        parts = [p for p in clean.split("/") if p]
        if not parts:
            parts = ["index.html"]
        rel = Path(*parts)
        candidate = Path(self.server.web_root) / rel
        if candidate.is_file():
            return candidate
        if candidate.is_dir():
            idx = candidate / "index.html"
            if idx.is_file():
                return idx
        for prefix, root in self.server.extra_roots:
            if clean == prefix or clean.startswith(prefix.rstrip("/") + "/"):
                rest = clean[len(prefix.rstrip("/")):].lstrip("/")
                cand = Path(root) / (rest if rest else "index.html")
                if cand.is_file():
                    return cand
        return None

    def send_cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, HEAD, OPTIONS")
        self.send_header(
            "Access-Control-Allow-Headers",
            "Range, Content-Type, Accept, Mcp-Session-Id, Mcp-Protocol-Version, X-Api-Key, Authorization",
        )

    def end_headers(self):
        self.send_cors()
        # Dev server: always revalidate so CSS/JS edits are picked up without a
        # hard refresh (browsers would otherwise heuristic-cache our unversioned
        # static assets and show a stale layout).
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        resolved = self._resolve(self.path)
        if resolved is None:
            self.send_error(404, "File not found")
            return None

        ctype = self.guess_type(str(resolved))
        try:
            f = open(resolved, "rb")
        except OSError:
            self.send_error(404, "File not found")
            return None

        size = resolved.stat().st_size
        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Last-Modified", self.date_time_string(resolved.stat().st_mtime))
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        return f

    def do_GET(self):
        resolved = self._resolve(self.path)
        if resolved is None:
            self.send_error(404, "File not found")
            return

        ctype = self.guess_type(str(resolved))
        size = resolved.stat().st_size

        range_header = self.headers.get("Range")
        if range_header:
            m = RANGE_RE.search(range_header)
            if m:
                start_s, end_s = m.group(1), m.group(2)
                start = int(start_s) if start_s else 0
                end = int(end_s) if end_s else size - 1
                if start >= size:
                    self.send_response(416)
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
                end = min(end, size - 1)
                length = end - start + 1
                self.send_response(206)
                self.send_header("Content-type", ctype)
                self.send_header("Content-Length", str(length))
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Last-Modified", self.date_time_string(resolved.stat().st_mtime))
                self.end_headers()
                with open(resolved, "rb") as f:
                    f.seek(start)
                    chunk = f.read(length)
                self.wfile.write(chunk)
                return

        self.send_response(200)
        self.send_header("Content-type", ctype)
        self.send_header("Content-Length", str(size))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Last-Modified", self.date_time_string(resolved.stat().st_mtime))
        self.end_headers()
        with open(resolved, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                self.wfile.write(chunk)

    def log_message(self, fmt, *args):
        sys.stderr.write("[serve] %s\n" % (fmt % args))


def main():
    port = int(os.environ.get("GLEN_SERVE_PORT", sys.argv[1] if len(sys.argv) > 1 else 8100))
    web_root = Path(os.environ.get("GLEN_WEB_ROOT", sys.argv[2] if len(sys.argv) > 2 else str(DEFAULT_WEB_ROOT)))
    basemap_ext = Path(os.environ.get("GLEN_BASEMAP_EXT", sys.argv[3] if len(sys.argv) > 3 else str(DEFAULT_BASEMAP_EXT)))

    if not web_root.is_dir():
        print(f"ERROR: web root not found: {web_root}")
        sys.exit(1)

    extra_roots = []
    # Option A: a local copy at app/data/basemap/ (or app/basemap/) wins.
    extra_roots.append(("/basemap", web_root / "data" / "basemap"))
    extra_roots.append(("/basemap", web_root / "basemap"))
    # Option C: serve the PMTiles from its original external location.
    if basemap_ext.is_dir():
        extra_roots.append(("/basemap", basemap_ext))
    # Analysis Result Store (generated parquet/json/metadata) served to the
    # frontend Result Layer Manager. Regenerable, never a source of truth.
    try:
        import result_store
        extra_roots.append(("/results", result_store.RESULT_DIR))
    except Exception:
        pass

    server = ThreadingHTTPServer(("0.0.0.0", port), RangeRequestHandler)
    server.web_root = web_root
    server.extra_roots = extra_roots

    # Silence default logging noise (custom log_message already writes).
    print(f"[serve] GLEN LST Agent web root: {web_root}")
    print(f"[serve] basemap external dir:   {basemap_ext}")
    print(f"[serve] serving at http://localhost:{port}/")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[serve] stopped")


if __name__ == "__main__":
    main()
