from __future__ import annotations

from pathlib import Path

import pytest

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "help"


@pytest.fixture
def help_text():
    def _load(name: str) -> str:
        return (FIXTURE_DIR / f"{name}.txt").read_text(encoding="utf-8")

    return _load
