"""Health check route for Railway deployment."""
from flask import Blueprint, jsonify

health_bp = Blueprint("health", __name__)


@health_bp.route("/")
def health_check():
    """Root health check for Railway and other platforms."""
    return jsonify({"status": "ok", "service": "QualifyAI"})