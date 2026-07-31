import os
import logging
from app import app

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Start the Flask application
    logger.info("Starting Trading Web Application...")
    app.run(host="0.0.0.0", port=5000, debug=True)
