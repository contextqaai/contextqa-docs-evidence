"""Expose only SoFa's public demo pages and linked assets on a local test port."""
import argparse
from html.parser import HTMLParser
from http.client import HTTPConnection
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

PAGES = {"/product-guide.html", "/demo-player.html"}
DESIGNS = {"demo-hub", "player", "mobile-player", "lead-form"}


class LinkedAssets(HTMLParser):
    def __init__(self):
        super().__init__()
        self.paths = set()

    def handle_starttag(self, tag, attrs):
        for attr, value in attrs:
            if attr in {"src", "href"} and value and value.startswith("/assets/"):
                name = value.removeprefix("/assets/")
                if name and "/" not in name and Path(name).suffix in {".css", ".js", ".png", ".jpg"}:
                    self.paths.add(value)


def public_paths(dist):
    paths = set(PAGES)
    assets = LinkedAssets()
    for page in PAGES:
        assets.feed((dist / page[1:]).read_text())
    paths.update(assets.paths)
    paths.add("/examples/demo-design/tokens.css")
    for name in DESIGNS:
        for suffix in (".html", ".css", ".js"):
            path = "/examples/demo-design/" + name + suffix
            if (dist / path[1:]).is_file():
                paths.add(path)
    return paths


def serve(dist, portal_port, listen_port):
    allowed = public_paths(dist)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urlsplit(self.path).path
            if path not in allowed:
                self.send_error(404)
                return
            upstream = HTTPConnection("127.0.0.1", portal_port, timeout=10)
            try:
                upstream.request("GET", path)
                response = upstream.getresponse()
                content = response.read()
                if response.getheader("Content-Security-Policy") is None:
                    self.send_error(502, "Missing portal security policy")
                    return
                if response.status == 200 and content != (dist / path[1:]).read_bytes():
                    self.send_error(409, "Portal and selected build differ")
                    return
                self.send_response(response.status)
                for header in ("Content-Type", "Content-Security-Policy", "X-Content-Type-Options",
                               "Referrer-Policy", "Cache-Control"):
                    value = response.getheader(header)
                    if value:
                        self.send_header(header, value)
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            except OSError:
                self.send_error(502, "Preview unavailable")
            finally:
                upstream.close()

        def log_message(self, *args):
            pass

    with ThreadingHTTPServer(("127.0.0.1", listen_port), Handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, default=Path("apps/web/dist"))
    parser.add_argument("--portal-port", type=int, default=8082)
    parser.add_argument("--listen-port", type=int, default=18571)
    args = parser.parse_args()
    serve(args.dist, args.portal_port, args.listen_port)
