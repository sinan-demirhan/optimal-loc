import logging
import os

from optimal_loc.app_constants import FILENAME

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))


def visualize():
    app_file = os.path.join(PACKAGE_DIR, 'st_app.py')
    if os.path.exists(FILENAME):
        os.system(f"streamlit run {app_file}")
    else:
        logging.info(
            f"The file {FILENAME} does not exist in the current path {os.getcwd()}"
        )
