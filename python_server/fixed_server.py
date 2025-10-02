#!/usr/bin/env python3

"""
FIXED SERVER - Direct Enhanced Medication Parser Integration
This server bypasses all the confusion and directly uses the working Enhanced Medication Parser
"""

import sys
import os
import base64
import json
import logging
import argparse
from flask import Flask, request, jsonify
from flask_cors import CORS

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the Enhanced Medication Parser directly
from enhanced_medication_parser import EnhancedMedicationParser

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Initialize the Enhanced Medication Parser
parser = EnhancedMedicationParser()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'Enhanced Medication Parser Server',
        'version': '1.0.0'
    }), 200

@app.route('/parse-document', methods=['POST'])
def parse_document():
    """
    Parse medication documents using Enhanced Medication Parser ONLY
    Expects: JSON with base64 encoded image and mode
    Returns: Structured medication data
    """
    try:
        logger.info("=== FIXED SERVER: Received parse-document request ===")
        data = request.get_json()

        if not data:
            logger.error("No JSON data received")
            return jsonify({'error': 'No JSON data provided'}), 400

        if 'image_base64' not in data:
            logger.error("No image_base64 in request")
            return jsonify({'error': 'image_base64 required'}), 400

        # Decode the base64 image
        try:
            image_data = base64.b64decode(data['image_base64'])
            logger.info(f"Decoded image data: {len(image_data)} bytes")
        except Exception as e:
            logger.error(f"Failed to decode base64 image: {e}")
            return jsonify({'error': 'Invalid base64 image data'}), 400

        mode = data.get('mode', 'cart_fill')
        logger.info(f"Mode: {mode}")

        # Use Enhanced Medication Parser directly
        logger.info("Using Enhanced Medication Parser for parsing...")
        result = parser.parse_medication_label(image_data, mode)

        logger.info(f"Parser result: {result}")

        # Return the result in the expected format
        response = {
            'success': result.get('success', False),
            'medications': result.get('medications', []),
            'raw_text': result.get('raw_text', ''),
            'method': 'enhanced_medication_parser'
        }

        logger.info(f"Returning response: {response}")
        return jsonify(response)

    except Exception as e:
        logger.error(f"Error processing document: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    parser_arg = argparse.ArgumentParser(description='Enhanced Medication Parser Server')
    parser_arg.add_argument('--port', type=int, default=5001, help='Port to run the server on')
    parser_arg.add_argument('--host', type=str, default='0.0.0.0', help='Host to run the server on')
    args = parser_arg.parse_args()

    logger.info(f"Starting Enhanced Medication Parser Server on {args.host}:{args.port}")
    logger.info("This server uses ONLY the Enhanced Medication Parser (Google Cloud Vision)")

    app.run(host=args.host, port=args.port, debug=True)