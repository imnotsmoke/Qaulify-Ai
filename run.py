#!/usr/bin/env python3
"""
Development entry point.

Usage::

    python run.py

Starts the Flask development server on 0.0.0.0:5000.
"""
import os
from dotenv import load_dotenv

load_dotenv()

from app import create_app

config_name = os.getenv("FLASK_ENV", "development")
app = create_app(config_name)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.logger.info("Starting development server on 0.0.0.0:%d", port)
    app.run(host="0.0.0.0", port=port, debug=(config_name == "development"))