from flask import Blueprint, request, jsonify
import os

# Create a blueprint for user routes
user_bp = Blueprint('user', __name__)

@user_bp.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({'status': 'ok'})
