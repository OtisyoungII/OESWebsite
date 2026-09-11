"""Vendor-neutral Linux beta profile; one worker keeps process limits meaningful."""
import os

bind = os.environ.get('HOST', '127.0.0.1') + ':' + os.environ.get('PORT', '8000')
workers = 1
worker_class = 'gthread'
threads = 8
timeout = 360
graceful_timeout = 30
keepalive = 5
accesslog = None
errorlog = '-'
loglevel = 'warning'
# Trust forwarded scheme only through the explicitly configured WSGI ProxyFix.
forwarded_allow_ips = ''
