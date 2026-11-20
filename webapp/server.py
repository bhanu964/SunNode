#!/usr/bin/env python3
"""
webapp/server.py
Lightweight HTTP server for SunNode Decision Support System (DSS) web application.
Serves webapp/ as root and routes /outputs/ to repository deliverables.
"""

import os
import sys
import socket
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8000
WEBAPP_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.dirname(WEBAPP_DIR)
OUTPUTS_DIR = os.path.join(REPO_DIR, "outputs")

class SunNodeHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEBAPP_DIR, **kwargs)

    def translate_path(self, path):
        # Clean path
        clean_path = path.split('?', 1)[0].split('#', 1)[0]
        if clean_path.startswith('/outputs/'):
            rel_file = clean_path[len('/outputs/'):]
            return os.path.join(OUTPUTS_DIR, rel_file)
        return super().translate_path(path)

    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        super().end_headers()

# Alias for backwards compatibility
SuryaGridHandler = SunNodeHandler

def get_free_port(preferred_port=8000, max_attempts=50):
    for port in range(preferred_port, preferred_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('', port))
                return port
            except OSError:
                continue
    return preferred_port

def run_server(port=PORT):
    actual_port = get_free_port(port)
    if actual_port != port:
        print(f"⚠️  Port {port} in use. Automatically switched to port {actual_port}.")
    server_address = ('', actual_port)
    httpd = HTTPServer(server_address, SunNodeHandler)
    print("=" * 70)
    print(f"☀️  SunNode DSS Server Running at http://localhost:{actual_port}")
    print(f"📁 Serving WebApp from: {WEBAPP_DIR}")
    print(f"📦 Serving Deliverables from: {OUTPUTS_DIR}")
    print("=" * 70)
    print("Press Ctrl+C to stop the server.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SunNode server.")
        httpd.server_close()

if __name__ == "__main__":
    p = int(sys.argv[1]) if len(sys.argv) > 1 else PORT
    run_server(p)
