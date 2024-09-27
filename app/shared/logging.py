"""
logging.py

This module sets up logging for different environments based on whether
the application is executed as a standalone program or as a Flask app. 

It provides two main functions: 
1. `setup_logging(is_executable, uploadfolder)`: Configures logging settings 
    based on the execution context.
2. `stepLog(message, *args, **kwargs)`: Logs messages with an incremental
   step counter to track progress in the main script.

Functions:
- setup_logging(is_executable):
    Set up conditional logging based on the execution type.

- stepLog(message, *args, **kwargs):
    Log a message that includes an incremental step counter in a main script.

Dependencies:
- os: For path manipulation.
- sys: For standard I/O.
- logging: For configuring and writing log messages.
"""
from shared.common import os, sys, logging

logger = logging.getLogger("my_logger")

def setup_logging(is_executable, uploadfolder):
    """
    Set up conditional logging based on type

    Args:
        is_executable: True if Flask app is run, False otherwise 
    """

    # Set up logging for Flask app
    log_directory = os.path.join(uploadfolder or os.path.dirname(__file__), 'temp')
    os.makedirs(log_directory, exist_ok=True)
    log_file = os.path.join(log_directory, 'log_file.log')

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

def stepLog(message, *args, **kwargs):
    """
    Log a message that includes an incremental step counter in a main script

    Parameters:
        message: message text to

    Returns:
        Log message containing incremental step count
    """
    logger.info(" STEP %d: " % stepLog.counter + message, *args, **kwargs)
    stepLog.counter += 1