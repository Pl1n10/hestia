"""Scaffolder helpers (the pure, side-effect-free parts)."""

from __future__ import annotations

import pytest

from scripts.new_module import _capitalize, _validate


def test_capitalize_handles_compound_keys():
    assert _capitalize("vehicles") == "Vehicles"
    assert _capitalize("car_parts") == "CarParts"


@pytest.mark.parametrize("bad", ["Vehicles", "1car", "a", "with-dash", "_template", "example"])
def test_validate_rejects_bad_keys(bad):
    with pytest.raises(SystemExit):
        _validate(bad)


def test_validate_rejects_existing_module():
    with pytest.raises(SystemExit):
        _validate("dogs")
