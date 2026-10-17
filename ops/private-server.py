#!/usr/bin/env python3
"""Loopback-only authentication and private static content service."""
import collections
import hashlib
import hmac
import http.cookies
import http.server
import json
import mimetypes
import os
from pathlib import Path
import re
import secrets
import threading
import time
import urllib.parse

CONFIG = Path(os.environ.get('PRIVATE_CONFIG', '/etc/jingkang-blog/auth'))
ROOT = Path(os.environ.get('PRIVATE_ROOT', '/var/lib/jingkang-blog/site')).resolve()
SESSION_KEY = (CONFIG / 'session.key').read_bytes()
COOKIE = '__Secure-thoughts'
TTL = 12 * 3600
failures = collections.defaultdict(collections.deque)
lock = threading.Lock()
# Also bound aggregate attempts so changing IPs does not remove all limits.
global_failures = collections.deque()

def normalize_day(value):
    if not re.fullmatch(r'(?:0?[1-9]|[12][0-9]|30)', value):
        return None
    return str(int(value))

def valid_cookie(raw):
    try:
        cookie = http.cookies.SimpleCookie(raw)
        value = cookie[COOKIE].value
        expiry, nonce, signature = value.split('.')
        message = f'{expiry}.{nonce}'
        return (time.time() < int(expiry) <= time.time() + TTL + 60 and
                hmac.compare_digest(signature, hmac.new(SESSION_KEY, message.encode(), hashlib.sha256).hexdigest()))
    except (KeyError, ValueError, http.cookies.CookieError):
        return False

def make_cookie():
    message = f'{int(time.time()) + TTL}.{secrets.token_hex(24)}'
    return message + '.' + hmac.new(SESSION_KEY, message.encode(), hashlib.sha256).hexdigest()

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # Never log request bodies or birthdays.

    def headers_for(self, status, content_type='text/plain; charset=utf-8', length=0, extra=None):
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(length))
        self.send_header('Cache-Control', 'private, no-store')
        self.send_header('X-Robots-Tag', 'noindex, nofollow, noarchive')
        self.send_header('X-Content-Type-Options', 'nosniff')
        for key, value in (extra or {}).items():
            self.send_header(key, value)
        self.end_headers()

    def respond(self, status, body='', extra=None):
        data = body.encode()
        self.headers_for(status, length=len(data), extra=extra)
        if self.command != 'HEAD':
            self.wfile.write(data)

    def do_HEAD(self):
        self.do_GET()

    def do_GET(self):
        path = urllib.parse.urlsplit(self.path).path
        authenticated = valid_cookie(self.headers.get('Cookie', ''))
        if path == '/_private/status':
            return self.respond(200 if authenticated else 401)
        if not path.startswith('/thoughts/'):
            return self.respond(404)
        if not authenticated:
            next_path = urllib.parse.quote(path, safe='')
            return self.respond(303, extra={'Location': '/categories/personal-thoughts/?next=' + next_path})
        target = (ROOT / urllib.parse.unquote(path).lstrip('/')).resolve()
        if not target.is_relative_to(ROOT / 'thoughts'):
            return self.respond(404)
        if target.is_dir():
            target = target / 'index.html'
        if not target.is_file() or target.suffix.lower() not in {'.html', '.webp', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf', '.mp4', '.mp3'}:
            return self.respond(404)
        data = target.read_bytes()
        kind = mimetypes.guess_type(target)[0] or 'application/octet-stream'
        self.headers_for(200, kind, len(data))
        if self.command != 'HEAD':
            self.wfile.write(data)

    def do_POST(self):
        origin = self.headers.get('Origin')
        expected = 'https://' + self.headers.get('Host', '')
        if origin != expected:
            return self.respond(403, '请求来源无效。')
        path = urllib.parse.urlsplit(self.path).path
        if path == '/_private/logout':
            return self.respond(303, extra={'Location': '/categories/personal-thoughts/', 'Set-Cookie': COOKIE + '=; Max-Age=0; Path=/; Secure; HttpOnly; SameSite=Lax'})
        if path != '/_private/login':
            return self.respond(404)
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            return self.respond(400)
        if length < 1 or length > 1024:
            return self.respond(400)
        ip = self.headers.get('X-Real-IP', self.client_address[0])
        now = time.time()
        with lock:
            # Keep the failure map bounded.
            for key in list(failures):
                while failures[key] and failures[key][0] < now - 900:
                    failures[key].popleft()
                if not failures[key]:
                    del failures[key]
            while global_failures and global_failures[0] < now - 900:
                global_failures.popleft()
            if len(failures[ip]) >= 5 or len(global_failures) >= 15:
                self.rfile.read(length)
                return self.respond(303, extra={'Location': '/categories/personal-thoughts/?error=limited'})
            # Reserve an attempt before the slow password comparison, preventing concurrent bypasses.
            failures[ip].append(now)
            global_failures.append(now)
        try:
            form = urllib.parse.parse_qs(self.rfile.read(length).decode(), strict_parsing=True)
            day = normalize_day(form.get('birthday', [''])[0])
            secret = json.loads((CONFIG / 'birthday.json').read_text())
            digest = hashlib.pbkdf2_hmac('sha256', (day or '').encode(), bytes.fromhex(secret['salt']), secret['iterations']).hex()
            correct = day is not None and hmac.compare_digest(digest, secret['digest'])
        except FileNotFoundError:
            return self.respond(503, '作者尚未设置解锁日数，请稍后再试。')
        except (ValueError, KeyError, UnicodeDecodeError):
            return self.respond(400)
        if not correct:
            return self.respond(303, extra={'Location': '/categories/personal-thoughts/?error=incorrect'})
        with lock:
            if now in failures[ip]:
                failures[ip].remove(now)
            if now in global_failures:
                global_failures.remove(now)
        next_path = form.get('next', ['/thoughts/'])[0]
        if not re.fullmatch(r'/thoughts/(?:[a-zA-Z0-9_-]+/)?', next_path):
            next_path = '/thoughts/'
        return self.respond(303, extra={'Location': next_path, 'Set-Cookie': COOKIE + '=' + make_cookie() + '; Max-Age=' + str(TTL) + '; Path=/; Secure; HttpOnly; SameSite=Lax'})

if __name__ == '__main__':
    http.server.ThreadingHTTPServer(('127.0.0.1', int(os.environ.get('PRIVATE_PORT', '8766'))), Handler).serve_forever()
