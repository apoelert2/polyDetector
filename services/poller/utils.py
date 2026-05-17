# /var/home/Adrian/Dokumente/Projekte/Deepseek/polyDetector/services/poller/utils.py
import json
from pathlib import Path
from typing import List, Union


def load_tag_ids(path: str) -> List[int]:
    # Lädt Tag-IDs aus einer JSON-Datei.
    # Entfernt automatisch Duplikate.
    
    # Unterstützt zwei Formate:
    # 1. Direkte Integer-Liste: [1, 2, 3]
    # 2. Objekt-Liste: [{"id": 1, "name": "..."}, ...]
    if not path:
        raise ValueError("Path cannot be empty")
    
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extrahiere IDs aus verschiedenen Formaten
    ids = []
    
    if isinstance(data, list):
        if not data:
            return []
        
        # Prüfe das erste Element um das Format zu erkennen
        if isinstance(data[0], int):
            # Format: [1, 2, 3]
            ids = data
        elif isinstance(data[0], dict) and 'id' in data[0]:
            # Format: [{"id": 1, "name": "..."}, ...]
            ids = [int(item['id']) for item in data if 'id' in item]
        else:
            raise ValueError(f"Unsupported data format: {type(data[0])}")
    
    # Entferne Duplikate (erhalte die ursprüngliche Reihenfolge)
    unique_ids = []
    seen = set()
    for id_value in ids:
        if id_value not in seen:
            seen.add(id_value)
            unique_ids.append(id_value)
    
    return unique_ids