#!/usr/bin/env python3
"""
Simple HTTP server for SPA development.
Serves index.html for routes that don't match actual files.
"""
import http.server
import socketserver
import os
import urllib.parse
import subprocess
from pathlib import Path

class SPAHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def do_GET(self):
        parsed_path = urllib.parse.urlparse(self.path)
        path = parsed_path.path
        
        # Handle root path
        if path == '/' or path == '':
            self.path = '/index.html'
            super().do_GET()
            return
        
        # Remove leading slash for file system operations
        fs_path = path[1:] if path.startswith('/') else path
        
        # Check if it's an actual file
        if os.path.exists(fs_path) and os.path.isfile(fs_path):
            super().do_GET()
            return
        
        # Check if it's a directory with index.html
        if os.path.isdir(fs_path) and os.path.exists(os.path.join(fs_path, 'index.html')):
            self.path = path.rstrip('/') + '/index.html'
            super().do_GET()
            return
        
        # Check if it's a file extension (likely an asset)
        if '.' in os.path.basename(fs_path):
            # Let it 404 naturally if it doesn't exist
            super().do_GET()
            return
        
        # For SPA routes without file extensions, serve index.html
        # This handles routes like /album, /articles, /utilities, etc.
        self.path = '/index.html'
        super().do_GET()

def run_build():
    """Execute the static site build so SSR outputs stay fresh."""
    repo_root = Path(__file__).resolve().parent
    build_script = repo_root / 'scripts' / 'python' / 'convert_markdown_to_html.py'

    if not build_script.exists():
        print("Build script not found; skipping pre-build step.")
        return

    print("Running static build...")
    try:
        subprocess.run(
            ['python3', str(build_script)],
            cwd=repo_root,
            check=True,
            capture_output=False
        )
        print("Static build complete.")
    except subprocess.CalledProcessError as exc:
        print("Static build failed; serving existing files.")
        print(f"Return code: {exc.returncode}")


if __name__ == '__main__':
    HOST = os.environ.get('HOST', '127.0.0.1')
    PORT = int(os.environ.get('PORT', '8100'))
    
    run_build()

    with socketserver.TCPServer((HOST, PORT), SPAHTTPRequestHandler) as httpd:
        print(f"Server running at http://{HOST}:{PORT}/")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nShutting down server...")
            httpd.shutdown()
