# /var/home/Adrian/Dokumente/Projekte/Deepseek/polyDetector/config.py
from pathlib import Path

# Projektroot automatisch erkennen
PROJECT_ROOT = Path(__file__).parent

# Pfade zu wichtigen Dateien
TAG_IDS_PATH = PROJECT_ROOT / "tag_ids.json"
LOG_PATH = PROJECT_ROOT / "logs"
DATA_PATH = PROJECT_ROOT / "data"

# Andere Konfigurationen
POLLING_INTERVAL = 60  # Sekunden
API_TIMEOUT = 30