"""Cloudflare Workers entry point. index.html and /static/* are served as static assets, so only the API reaches Flask."""

from workers import wsgi

from app import app

Default = wsgi.entrypoint(app)
