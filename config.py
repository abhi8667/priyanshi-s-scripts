import os
from pathlib import Path

# Application Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Data and Storage Paths
DATA_DIR = BASE_DIR / "data"
BACKUP_DIR = DATA_DIR / "backups"
LOGS_DIR = BASE_DIR / "logs"
EXPORTS_DIR = BASE_DIR / "exports"

for directory in [DATA_DIR, BACKUP_DIR, LOGS_DIR, EXPORTS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Database URI
DB_PATH = DATA_DIR / "induction_system.db"
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DB_PATH.as_posix()}")

# Application Info
APP_NAME = "NexusAllocate Pro - College Induction Allocation System"
APP_VERSION = "1.0.0"
ORGANIZATION_NAME = "Higher Education Enterprise Solutions"

# Optimization Settings
DEFAULT_GROUPS = ["Group A", "Group B"]
FUZZY_MATCH_THRESHOLD = 80.0  # Threshold for Excel column matching
NEAR_DUPLICATE_THRESHOLD = 88.0  # Threshold for student name comparison

# Theme
DEFAULT_THEME = "dark"
