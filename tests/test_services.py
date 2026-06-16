import os
import sys
import pandas as pd
import pytest

# ensure project root is on sys.path so tests can import application modules
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from services import compare_data


def test_compare_basic_match():
    initial = pd.DataFrame([{"Account": "A1", "Value": "100"}])
    new = pd.DataFrame([{"Account": "A1", "Value": "100"}])
    results = compare_data(initial, new)
    assert len(results) == 1
    assert results[0]["status"] == "ok"
    assert results[0]["mismatches"] == []


def test_missing_in_initial():
    initial = pd.DataFrame([{"Account": "A1", "Value": "100"}])
    new = pd.DataFrame([{"Account": "B2", "Value": "200"}])
    results = compare_data(initial, new)
    assert len(results) == 1
    assert results[0]["status"] == "missing_in_initial"


def test_mismatch_columns():
    initial = pd.DataFrame([{"Account": "A1", "Value": "100", "Name": "John"}])
    new = pd.DataFrame([{"Account": "A1", "Value": "200", "Name": "John"}])
    results = compare_data(initial, new)
    assert results[0]["status"] == "mismatch"
    # ensure mismatch details include the Value column
    mismatches = results[0]["mismatches"]
    assert any(m["column"] == "Value" and m["initial"] == "100" and m["new"] == "200" for m in mismatches)


def test_duplicate_initial_rows_take_first():
    initial = pd.DataFrame([
        {"Account": "A1", "Value": "100"},
        {"Account": "A1", "Value": "999"},
    ])
    new = pd.DataFrame([{"Account": "A1", "Value": "100"}])
    results = compare_data(initial, new)
    # print(results)
    assert results[0]["status"] == "ok"


def test_duplicate_initial_mismatch_when_first_different():
    initial = pd.DataFrame([
        {"Account": "A1", "Value": "777"},
        {"Account": "A1", "Value": "999"},
    ])
    new = pd.DataFrame([{"Account": "A1", "Value": "100"}])
    results = compare_data(initial, new)
    print(results)
    assert results[0]["status"] == "mismatch"
    assert results[0]["mismatches"][0]["initial"] == "777"


def test_missing_key_column_raises():
    initial = pd.DataFrame([{"id": "A1", "Value": "100"}])
    new = pd.DataFrame([{"id": "A1", "Value": "100"}])
    with pytest.raises(ValueError):
        compare_data(initial, new)


def test_strip_and_stringify_key_matching():
    initial = pd.DataFrame([{"Account": " 00123 ", "Value": "10"}])
    new = pd.DataFrame([{"Account": "00123", "Value": "10"}])
    results = compare_data(initial, new)
    assert results[0]["status"] == "ok"
