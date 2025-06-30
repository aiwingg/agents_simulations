import os
import sys

# DON'T CHANGE THIS !!!
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from flask import Flask, jsonify
from flask_cors import CORS
from src.config import Config
from src.routes.batch_routes import batch_bp
from src.routes.prompt_spec_routes import prompt_spec_bp

# Create Flask app
app = Flask(__name__)
app.config["SECRET_KEY"] = Config.SECRET_KEY

# Enable CORS for all origins (required for frontend-backend interaction)
CORS(app, origins="*")

# Register blueprints
app.register_blueprint(batch_bp, url_prefix="/api")
app.register_blueprint(prompt_spec_bp, url_prefix="/api")


@app.route("/")
def index():
    """Root endpoint with service information"""
    return jsonify(
        {
            "service": "LLM Simulation & Evaluation Service",
            "version": "1.0.0",
            "description": "Service for simulating and evaluating LLM conversations",
            "endpoints": {
                "health": "/api/health",
                "launch_batch": "POST /api/batches",
                "get_batch_status": "GET /api/batches/{batch_id}",
                "get_batch_results": "GET /api/batches/{batch_id}/results",
                "get_batch_summary": "GET /api/batches/{batch_id}/summary",
                "get_batch_cost": "GET /api/batches/{batch_id}/cost",
                "list_batches": "GET /api/batches",
                "list_prompt_specs": "GET /api/prompt-specs",
                "get_prompt_spec": "GET /api/prompt-specs/{spec_name}",
                "create_prompt_spec": "POST /api/prompt-specs/{spec_name}",
                "update_prompt_spec": "PUT /api/prompt-specs/{spec_name}",
                "delete_prompt_spec": "DELETE /api/prompt-specs/{spec_name}",
                "validate_prompt_spec": "POST /api/prompt-specs/{spec_name}/validate",
                "duplicate_prompt_spec": "POST /api/prompt-specs/{spec_name}/duplicate",
            },
            "documentation": "See README.md for detailed API documentation",
        }
    )


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


@app.errorhandler(400)
def bad_request(error):
    """Handle 400 errors"""
    return jsonify({"error": "Bad request"}), 400


if __name__ == "__main__":
    # Ensure required directories exist
    Config.ensure_directories()

    # Validate configuration
    try:
        Config.validate()
        print("✓ Configuration validated successfully")
    except ValueError as e:
        print(f"✗ Configuration error: {e}")
        print("Please set the OPENAI_API_KEY environment variable")
        sys.exit(1)

    print(f"Starting LLM Simulation Service on {Config.HOST}:{Config.PORT}")
    print(f"Debug mode: {Config.DEBUG}")
    print(f"OpenAI Model: {Config.OPENAI_MODEL}")
    print(f"Concurrency: {Config.CONCURRENCY}")

    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
