# Unit tests for load_tag_ids using the real tag_ids.json.

import json
import sys
from pathlib import Path

# main.py liegt im selben Ordner wie tests/ (~polyDetector~/services/poller/)
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent  # bis polyDetector
POLLER_DIR = Path(__file__).parent.parent  # Geht zu services/poller
sys.path.insert(0, str(POLLER_DIR))

import pytest
from utils import load_tag_ids

# Pfad zum echten tag_ids.json (relativ zum Projektroot)
TAG_IDS_PATH = PROJECT_ROOT / "tag_ids.json"

print(f"Looking for tag_ids.json at: {TAG_IDS_PATH}")  # Debug-Ausgabe
assert TAG_IDS_PATH.exists(), f"File not found at {TAG_IDS_PATH}"


def test_load_tag_ids_returns_list_of_ints():
    result = load_tag_ids(str(TAG_IDS_PATH))
    assert isinstance(result, list)
    assert len(result) > 0
    for item in result:
        assert isinstance(item, int), f"Expected int, got {type(item)}: {item}"


def test_load_tag_ids_contains_known_ids():
    result = load_tag_ids(str(TAG_IDS_PATH))
    # "acquire" hat id 103681, "Politics" hat id 2
    assert 103681 in result
    assert 2 in result


def test_load_tag_ids_no_duplicates():
    # Stellt sicher, dass doppelte Einträge entfernt werden
    result = load_tag_ids(str(TAG_IDS_PATH))
    assert len(result) == len(set(result)), f"Duplicate IDs found. Length: {len(result)}, Unique: {len(set(result))}"


def test_load_tag_ids_handles_raw_int_list(tmp_path):
    # Test mit einer Liste reiner Integers
    # Erstelle temporäre JSON-Datei mit Integer-Liste
    test_data = [1, 2, 3, 4, 5]
    test_file = tmp_path / "test_tags.json"

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    result = load_tag_ids(str(test_file))
    assert result == test_data


def test_load_tag_ids_handles_object_list(tmp_path):
    # Test mit einer Liste von Objekten
    test_data = [{"id": 1, "name": "Tag 1"}, {"id": 2, "name": "Tag 2"}, {"id": 3, "name": "Tag 3"}]
    test_file = tmp_path / "test_objects.json"

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    result = load_tag_ids(str(test_file))
    assert result == [1, 2, 3]


def test_load_tag_ids_removes_duplicates(tmp_path):
    # Testet die Entfernung von Duplikaten
    test_data = [1, 2, 2, 3, 3, 3, 4]
    test_file = tmp_path / "test_with_dups.json"

    with open(test_file, "w") as f:
        json.dump(test_data, f)

    result = load_tag_ids(str(test_file))
    assert result == [1, 2, 3, 4]


def test_load_tag_ids_empty_file(tmp_path):
    # Test mit leerer Liste
    test_file = tmp_path / "empty.json"

    with open(test_file, "w") as f:
        json.dump([], f)

    result = load_tag_ids(str(test_file))
    assert result == []


def test_load_tag_ids_file_not_found():
    # Test mit nicht existierender Datei
    with pytest.raises(FileNotFoundError):
        load_tag_ids("/path/to/nonexistent/file.json")


def test_load_tag_ids_empty_path():
    # Test mit leerem Pfad
    with pytest.raises(ValueError, match="Path cannot be empty"):
        load_tag_ids("")
