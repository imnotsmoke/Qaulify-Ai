"""
Flask application factory for QualifyAI.
"""
import logging
import sys

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler

from app.config import config_by_name
from app.models import db

# --- Logging setup -----------------------------------------------------------
def _init_logging(app: Flask) -> None:
    """Configure structured logging for the application."""
    log_level = logging.DEBUG if app.config.get("DEBUG") else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s in %(module)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)
    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)
    app.logger.info("QualifyAI starting up ...")


def _init_scheduler(app: Flask) -> BackgroundScheduler:
    """Initialise the APScheduler background scheduler."""
    scheduler = BackgroundScheduler()
    scheduler.start()
    app.logger.info("APScheduler started")
    return scheduler


def create_app(config_name: str = "default") -> Flask:
    """
    Application factory.

    Usage::

        app = create_app("development")
        app.run()

    Or via environment::

        FLASK_ENV=production python run.py
    """
    app = Flask(__name__)

    # Load configuration
    cfg = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg)

    # Logging
    _init_logging(app)

    # Database
    db.init_app(app)
    with app.app_context():
        db.create_all()
    app.logger.info("Database tables created / verified")

    # Scheduler
    app.scheduler = _init_scheduler(app)

    # Register blueprints
    from app.routes.whatsapp import whatsapp_bp
    from app.routes.calendly import calendly_bp
    from app.routes.agent import agent_bp

    app.register_blueprint(whatsapp_bp)
    app.register_blueprint(calendly_bp)
    app.register_blueprint(agent_bp)
    app.logger.info("Blueprints registered: whatsapp, calendly, agent")

    # Error handlers
    @app.errorhandler(400)
    def bad_request(error):
        app.logger.warning("400 Bad Request: %s", error)
        return {"error": "bad_request", "message": str(error)}, 400

    @app.errorhandler(404)
    def not_found(error):
        app.logger.warning("404 Not Found: %s", error)
        return {"error": "not_found", "message": "The requested resource was not found"}, 404

    @app.errorhandler(405)
    def method_not_allowed(error):
        app.logger.warning("405 Method Not Allowed: %s", error)
        return {"error": "method_not_allowed", "message": str(error)}, 405

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error("500 Internal Error: %s", error)
        return {"error": "internal_error", "message": "An unexpected error occurred"}, 500

    app.logger.info("QualifyAI initialised successfully")
    return app