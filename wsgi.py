#!/usr/bin/env python3
"""
Production WSGI entry point.

Usage::

    gunicorn wsgi:app --bind 0.0.0.0:8000 --workers 4

or with the provided gunicorn config::

    gunicorn wsgi:app
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

config_name = os.getenv("FLASK_ENV", "production")
app = create_app(config_name)