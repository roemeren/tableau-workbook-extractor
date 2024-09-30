"""
cli_main.py

Main module for the CLI version of the application to prompt the user 
to select a Tableau Workbook file (.twb) and process it using the `process_twb` 
function.

Its `main` function uses `easygui` to open a file dialog allowing the user to select
a Tableau Workbook file (.twb or .twbx). Once a file is selected, it logs the
file path and attempts to process the file by calling the `process_twb` function.
If an error occurs during processing, an error message is logged, and the user
is prompted to press Enter to exit the program.

If no file is selected, a warning is logged, and the user is also prompted to 
press Enter to exit the program.

Returns:
    str: The path of the selected file, or None if no file is selected.
"""
#from shared.common import logging
from shared.logging import setup_logging, stepLog, logger
from shared.processing import process_twb
import easygui

def main():
    
    # Initialize logging for Flask app
    setup_logging(True, None)

    # Ask the user to select a .twb file using easygui
    stepLog("Prompt for input Tableau workbook...")
    inpFilePath = easygui.fileopenbox(
        title = "Select a Tableau Workbook",
        default = "*.twb*"
    )

    # Check if a file was selected
    if inpFilePath:
        logger.info(f"\tSelected file: {inpFilePath}")
        try:
            # Call the process_twb function to process the file
            process_twb(filepath=inpFilePath)
            logger.info("Processing completed successfully.")
        except Exception as e:
            logger.error(f"An error occurred during processing: {e}")
            input("An error occurred. Press Enter to exit...")
    else:
        logger.warning("No file selected.")
        input("No file selected. Press Enter to exit...")

    return inpFilePath

if __name__ == "__main__":
    main()