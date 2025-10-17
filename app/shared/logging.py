"""
logging.py

This module sets up logging for different environments based on whether
the application is executed as a standalone program or as a Flask app. 
"""
from shared.common import os, sys
import logging

logger = logging.getLogger("TWE_LOGGER")

def setup_logging(is_executable, uploadfolder):
    """
    Set up conditional logging based on type

    Args:
        is_executable: True if Flask app is run, False otherwise
        uploadfolder (str): The directory where log files should be saved. 
                    If not provided, logs will be saved in a 'temp' 
                    directory adjacent to this module.
    """

    # Set up logging for Flask app
    log_directory = os.path.join(uploadfolder or os.path.dirname(__file__), 'temp')
    os.makedirs(log_directory, exist_ok=True)
    log_file = os.path.join(log_directory, 'log_file.log')

    # Prevent the logger from propagating log messages to the root logger
    logger.propagate = False

    # Create a custom logger
    logger.setLevel(logging.DEBUG)

    # Check if logging should go to console or file
    if is_executable:
        # Log to console
        handler = logging.StreamHandler(sys.stdout)
    else:
        # Log to file
        handler = logging.FileHandler(log_file)

    # Set the formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)

    # Add the handler to the logger
    logger.addHandler(handler)

def stepLog(message):
    """
    Log a message that includes an incremental step counter in a main script

    Parameters:
        message: message text to

    Returns:
        Log message containing incremental step count
    """
    # Initialize the counter if it hasn't been set yet
    if not hasattr(stepLog, 'counter'):
        stepLog.counter = 1

    # Construct the full message
    log_message = f" STEP {stepLog.counter}: {message}..."

    # Print message and increment counter
    logger.info(log_message)
    stepLog.counter += 1

    # Return message (for Dash app)
    return message