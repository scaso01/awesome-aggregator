"""Centralized configuration loading for Awesome Aggregator."""

import logging
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# Load config.yaml. AGGREGATOR_CONFIG points somewhere else, which is how CI
# runs against local fixture feeds instead of the live internet, and how you
# would run two instances from one checkout.
_config_path = Path(os.getenv("AGGREGATOR_CONFIG") or BASE_DIR / "config.yaml")
if _config_path.exists():
    with open(_config_path, "r") as f:
        CONFIG = yaml.safe_load(f) or {}
else:
    CONFIG = {}

# Server config
SERVER_HOST = os.getenv("HOST", CONFIG.get("server", {}).get("host", "0.0.0.0"))
SERVER_PORT = int(os.getenv("PORT", CONFIG.get("server", {}).get("port", 8000)))
DEBUG = CONFIG.get("server", {}).get("debug", False)

# Database config
DB_PATH = BASE_DIR / CONFIG.get("database", {}).get("path", "aggregator.db")

# Scheduler config
SCHEDULER_CONFIG = CONFIG.get("scheduler", {})
DEFAULT_INTERVAL = SCHEDULER_CONFIG.get("default_interval_seconds", 300)
SOURCE_INTERVALS = SCHEDULER_CONFIG.get("intervals", {})

# Cache config
CACHE_TTL = CONFIG.get("cache", {}).get("ttl_seconds", 600)
CACHE_MAX_ITEMS = CONFIG.get("cache", {}).get("max_items", 10000)

# Source config
SOURCE_CONFIG = CONFIG.get("sources", {})
MAX_ITEMS_PER_SOURCE = SOURCE_CONFIG.get("max_items_per_source", 50)
REQUEST_TIMEOUT = SOURCE_CONFIG.get("request_timeout_seconds", 30)
MAX_CONCURRENT = SOURCE_CONFIG.get("max_concurrent_fetches", 10)

# Display config
DISPLAY_CONFIG = CONFIG.get("display", {})
DEFAULT_THEME = DISPLAY_CONFIG.get("default_theme", "dark")
GRID_COLUMNS = DISPLAY_CONFIG.get("default_columns", 12)
ROW_HEIGHT = DISPLAY_CONFIG.get("default_row_height", 150)

# RSSHub config
RSSHUB_URL = os.getenv("RSSHUB_URL", CONFIG.get("rsshub", {}).get("url", "http://localhost:1200"))

# Default sources
DEFAULT_SOURCES = CONFIG.get("default_sources", [])

# Logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("aggregator")
