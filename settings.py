import os

# Application paths and settings
ALLOWED_EXTENSIONS = {"xls", "xlsx", "csv"}
UPLOAD_DIR = "data"
INITIAL_SUBDIR = "initial"
INITIAL_DIR = os.path.join(UPLOAD_DIR, INITIAL_SUBDIR)
