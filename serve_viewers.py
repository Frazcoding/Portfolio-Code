"""Serve generated viewers and their external 3D assets from the workspace root."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import sys
import webbrowser


ROOT = Path(__file__).resolve().parent
PROJECTS = {path.name for path in ROOT.iterdir() if path.is_dir() and (path / "viewer.html").exists()}


def main():
    project = sys.argv[1] if len(sys.argv) > 1 else None
    if project is not None and project not in PROJECTS:
        raise SystemExit(f"Unknown project: {project}")

    class Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ROOT), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    if project:
        url += f"{project}/viewer.html"
    else:
        url += "index.html"
    print(f"Serving {url} — keep this window open while viewing", flush=True)
    if "--no-browser" not in sys.argv[2:]:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
