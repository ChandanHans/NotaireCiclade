import os
import re
import sys


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    base_path = getattr(sys, "_MEIPASS", os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    return os.path.join(base_path, relative_path)


def remove_extra_spaces(text):
    # Use regular expression to replace multiple spaces with a single space
    return re.sub(r"\s+", " ", text)
