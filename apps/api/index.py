"""Vercel entry point. Vercel's Python runtime looks for an ASGI object named
`app` in index.py at the project root (Root Directory: apps/api).

Locally and in Docker the same app is served with `uvicorn app.main:app`.
"""

from app.main import app

__all__ = ["app"]
