import logging
import os

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
FILENAME = 'optimal_locations.pickle'


def visualize():
    app_file = os.path.join(PACKAGE_DIR, 'st_app.py')
    if os.path.exists(FILENAME):
        os.system(f"streamlit run {app_file}")
    else:
        logging.info(
            f"The file {FILENAME} does not exist in the current path {os.getcwd()}"
        )