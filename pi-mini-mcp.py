#!/usr/bin/env python3
"""
Minimal Remote Command Server

A lightweight HTTP server for managing resource-constrained devices (like Raspberry Pi)
without maintaining heavy SSH sessions. Runs at ~5MB RAM idle.

Usage:
    python3 rpi-remote-server.py              # Runs on port 8222
    PORT=9000 python3 rpi-remote-server.py    # Custom port

Endpoints:
    GET  /        - Health check
    POST /cmd     - Execute command: {"cmd": "ls -la"}
    POST /read    - Read file: {"path": "/etc/hostname"}
    POST /write   - Write file: {"path": "/tmp/test.txt", "content": "hello"}
    POST /status  - System status (memory, CPU, disk)

Deploy as systemd service for persistence.
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import subprocess
import json
import os


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # Silence logging to save resources

    def do_POST(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(length)) if length else {}

            if self.path == '/cmd':
                result = subprocess.run(
                    data.get('cmd', 'echo "no command"'),
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                response = {
                    'stdout': result.stdout,
                    'stderr': result.stderr,
                    'code': result.returncode
                }

            elif self.path == '/read':
                path = data.get('path', '')
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        response = {'content': f.read(), 'ok': True}
                else:
                    response = {'error': 'File not found', 'ok': False}

            elif self.path == '/write':
                path = data.get('path', '')
                content = data.get('content', '')
                with open(path, 'w') as f:
                    f.write(content)
                response = {'ok': True}

            elif self.path == '/status':
                mem = subprocess.run(
                    "free -m | awk 'NR==2{print $3\"/\"$2\"MB\"}'",
                    shell=True, capture_output=True, text=True
                )
                cpu = subprocess.run(
                    "top -bn1 | head -3 | tail -1",
                    shell=True, capture_output=True, text=True
                )
                disk = subprocess.run(
                    "df -h / | tail -1 | awk '{print $3\"/\"$2}'",
                    shell=True, capture_output=True, text=True
                )
                response = {
                    'mem': mem.stdout.strip(),
                    'cpu': cpu.stdout.strip(),
                    'disk': disk.stdout.strip()
                }

            else:
                response = {'error': 'Unknown endpoint'}

            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({'error': str(e)}).encode())

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'rpi-remote ok')


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8222))
    print(f'Starting remote server on port {port}')
    HTTPServer(('0.0.0.0', port), Handler).serve_forever()

