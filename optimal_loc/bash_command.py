import logging
import os

FILENAME = 'optimal_locations.pickle'


def visualize():
    if os.path.exists(FILENAME):
        os.system("streamlit run st_app.py")
    else:
        logging.info(
            f"The file {FILENAME} does not exist in the current path {os.getcwd()}"
        )