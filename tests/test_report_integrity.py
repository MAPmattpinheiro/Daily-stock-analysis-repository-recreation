"""Tests for report integrity validation."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from report_integrity import _parse_json, _missing_fields, REQUIRED_FIELDS

def test_parse_valid_json():
    raw = '{"signal": "BUY", "score": 75}'
    result = _parse_json(raw)
    assert result is not None
    assert result["signal"] == "BUY"

def test_parse_json_with_fences():
    raw = '```json\n{"signal": "SELL", "score": 30}\n```'
    result = _parse_json(raw)
    assert result is not None
    assert result["score"] == 30

def test_parse_invalid_json():
    result = _parse_json("This is not JSON at all.")
    assert result is None

def test_missing_fields_all():
    missing = _missing_fields({})
    assert set(missing) == set(REQUIRED_FIELDS)

def test_missing_fields_none():
    complete = {f: "x" for f in REQUIRED_FIELDS}
    assert _missing_fields(complete) == []

def test_missing_fields_partial():
    partial = {"signal": "BUY", "score": 50}
    missing = _missing_fields(partial)
    assert "signal" not in missing
    assert "conclusion" in missing
