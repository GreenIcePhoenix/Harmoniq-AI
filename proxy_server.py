"""
Harmoniq AI — Single-port proxy server.
Serves UI at / and proxies /api/* to ADK on port 9000.
/data/summary serves Firestore data directly for the dashboard.
"""
import http.server
import urllib.request
import urllib.error
import json
import os
import sys
import threading
import subprocess
import time

ADK_PORT   = 9000
UI_DIR     = os.environ.get('UI_DIR', '/app/ui')
PROXY_PORT = int(os.environ.get('PORT', 8080))
sys.path.insert(0, '/app/agents')


class HarmoniqHandler(http.server.SimpleHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=UI_DIR, **kwargs)

    def log_message(self, fmt, *args):
        path = args[0] if args else ''
        if isinstance(path, str) and ('/api/' in path or '/data/' in path):
            print(f"  {args[1]} {path[:80]}")

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_GET(self):
        # Anything API-like → forward to ADK
        if (
            self.path.startswith('/api/')
            or self.path.startswith('/run')
            or self.path.startswith('/list-apps')
            or self.path.startswith('/apps')
        ):
            self._proxy('GET', b'')

        elif self.path.startswith('/data/'):
            self._data_handler()

        else:
            p = self.path.split('?')[0]
            if p == '/':
                self.path = '/index.html'
            super().do_GET()

    def do_POST(self):
        if (
            self.path.startswith('/api/')
            or self.path.startswith('/run')
            or self.path.startswith('/apps')
        ):
            length = int(self.headers.get('Content-Length', 0))
            body   = self.rfile.read(length) if length else b'{}'
            self._proxy('POST', body)
        else:
            self.send_error(404)

    def _cors(self):
        self.send_header('Access-Control-Allow-Origin',  '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

    def _proxy(self, method, body):
        if self.path.startswith('/api/'):
            adk_path = self.path[4:]
        else:
            adk_path = self.path
        adk_url  = f'http://127.0.0.1:{ADK_PORT}{adk_path}'
        print(f"[PROXY] Forwarding {method} {self.path} → {adk_url}")
        try:
            req = urllib.request.Request(
                adk_url,
                data=body if method == 'POST' else None,
                method=method,
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=180) as resp:
                data         = resp.read()
                print(f"[PROXY] Response status: {status}")
                print(f"[PROXY] Raw response (first 500 chars): {data[:500]}")
                status       = resp.status
                content_type = resp.headers.get('Content-Type', 'application/json')
            try:
                self.send_response(status)
                self._cors()
                self.send_header('Content-Type',   content_type)
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        except urllib.error.HTTPError as e:
            try:
                data = e.read()
                self.send_response(e.code)
                self._cors()
                self.send_header('Content-Type',   'application/json')
                self.send_header('Content-Length', str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        except Exception as ex:
            try:
                msg = json.dumps({'error': str(ex)}).encode()
                self.send_response(502)
                self._cors()
                self.send_header('Content-Type',   'application/json')
                self.send_header('Content-Length', str(len(msg)))
                self.end_headers()
                self.wfile.write(msg)
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _data_handler(self):
        try:
            from google.cloud import firestore
            from datetime import datetime

            db            = firestore.Client()
            current_month = datetime.utcnow().strftime("%Y-%m")

            month_exp = [
                d.to_dict() for d in db.collection("expenses").stream()
                if d.to_dict().get("date", "").startswith(current_month)
            ]
            month_inc = [
                d.to_dict() for d in db.collection("income").stream()
                if d.to_dict().get("date", "").startswith(current_month)
            ]
            bud_doc = db.collection("settings").document("budget").get()
            budget  = (
                bud_doc.to_dict().get("monthly_limit", 10000)
                if bud_doc.exists else 10000
            )

            total_exp = sum(e.get("amount", 0) for e in month_exp)
            total_inc = sum(i.get("amount", 0) for i in month_inc)

            by_cat = {}
            for e in month_exp:
                cat        = e.get("category", "other")
                by_cat[cat] = by_cat.get(cat, 0) + e.get("amount", 0)

            daily = {}
            for e in month_exp:
                d        = e.get("date", "")
                daily[d] = daily.get(d, 0) + e.get("amount", 0)

            result = {
                "total_expense":   total_exp,
                "total_income":    total_inc,
                "net_balance":     total_inc - total_exp,
                "budget":          budget,
                "by_category":     by_cat,
                "daily_totals":    daily,
                "recent_expenses": sorted(
                    month_exp, key=lambda x: x.get("date", ""), reverse=True
                )[:20],
                "recent_income":   sorted(
                    month_inc, key=lambda x: x.get("date", ""), reverse=True
                )[:10],
                "month": current_month
            }

            data = json.dumps(result).encode()
            self.send_response(200)
            self._cors()
            self.send_header('Content-Type',   'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            self.wfile.flush()

        except Exception as ex:
            msg = json.dumps({'error': str(ex)}).encode()
            self.send_response(500)
            self._cors()
            self.send_header('Content-Type',   'application/json')
            self.send_header('Content-Length', str(len(msg)))
            self.end_headers()
            self.wfile.write(msg)
            self.wfile.flush()


def start_adk():
    print("[ADK] Starting ADK process...")
    adk_bin = '/usr/local/bin/adk'
    cmd = [
        adk_bin, 'web',
        '/app/agents',
        '--host', '127.0.0.1',
        '--port', str(ADK_PORT),
        '--allow_origins', '*'
    ]
    print(f"Starting ADK on internal port {ADK_PORT}...")
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for _ in range(30):
        time.sleep(1)
        try:
            urllib.request.urlopen(
                f'http://127.0.0.1:{ADK_PORT}/list-apps', timeout=2
            )
            print(f"✅ ADK ready on port {ADK_PORT}")
            return proc
        except:
            pass
    print("⚠️  ADK may still be starting...")
    return proc


if __name__ == '__main__':
    adk_proc = start_adk()

    import socketserver
    class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    server = ThreadedServer(('0.0.0.0', PROXY_PORT), HarmoniqHandler)
    print(f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌟 HARMONIQ AI — READY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  Listening on port {PROXY_PORT}
  Dashboard: /dashboard.html
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        adk_proc.terminate()
        server.shutdown()