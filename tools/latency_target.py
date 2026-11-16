"""Temporary LAN-only Android browser target for visible-response measurements.

Run explicitly on a lab host; this is not part of the application service.
No directory listing, uploads or device credentials. Stop it after measuring.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import argparse

PAGE = b'''<!doctype html><meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<style>html,body{margin:0;width:100%;height:100%;overflow:hidden;touch-action:none;background:#c02020;color:white;font:24px sans-serif}body{display:grid;place-items:center}span{pointer-events:none}</style>
<span>DeviceDeck latency target</span><script>
let n=0;function paint(e){e.preventDefault();n++;document.body.style.background=n%2?'#20c020':'#c02020';document.querySelector('span').textContent='DeviceDeck '+n;}
document.body.addEventListener('pointerdown',paint);
document.body.addEventListener('pointermove',e=>{if(e.buttons)paint(e)});
</script>'''


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != '/target':
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bind', required=True)
    parser.add_argument('--port', type=int, default=18186)
    args = parser.parse_args()
    HTTPServer((args.bind, args.port), Handler).serve_forever()
