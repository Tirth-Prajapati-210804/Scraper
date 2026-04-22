from __future__ import annotations

import pytest

from app.utils.airline_codes import normalize_airline


def test_normalize_full_name() -> None:
    assert normalize_airline("EMIRATES") == "EK"
    assert normalize_airline("LUFTHANSANA") == "LH"


def test_normalize_typos() -> None:
    assert normalize_airline("LUTHANSA") == "LH"
    assert normalize_airline("AIR CANADA") == "AC"


def test_normalize_short_code() -> None:
    assert normalize_airline("AC") == "AC"
    assert normalize_airline("KLM") == "KL"  # KL is the correct IATA code for KLM


def test_normalize_empty() -> None:
    assert normalize_airline("") == "-"
    assert normalize_airline("  ") == "-"


def test_normalize_spaced_codes() -> None:
    assert normalize_airline("J A") == "JL"
    assert normalize_airline("EVA A") == "BR"


def test_normalize_case_insensitive() -> None:
    assert normalize_airline("emirates") == "EK"
    assert normalize_airline("Delta") == "DL"


def test_normalize_first_word_match() -> None:
    assert normalize_airline("LUFTHANSA CARGO") == "LH"


def test_normalize_fallback_truncate() -> None:
    result = normalize_airline("UNKNOWN AIRLINE XYZ")
    assert result == "UNKNOWN AI"
    assert len(result) <= 10
