from unittest.mock import MagicMock

import pytest

from app.core.memory import MemoryService


def test_format_for_prompt_empty():
    assert MemoryService.format_for_prompt([]) == ""


def test_format_for_prompt_bullets():
    s = MemoryService.format_for_prompt(["le gusta el café", "vegetariano"])
    assert "Lo que sé de este cliente" in s
    assert "café" in s


def test_search_handles_errors(monkeypatch: pytest.MonkeyPatch):
    mock_client = MagicMock()
    mock_client.search.side_effect = RuntimeError("down")
    monkeypatch.setattr(MemoryService, "_mem", lambda self: mock_client)
    m = MemoryService(api_key="x")
    assert m.search("q", "u1") == []


def test_add_handles_errors(monkeypatch: pytest.MonkeyPatch):
    mock_client = MagicMock()
    mock_client.add.side_effect = RuntimeError("down")
    monkeypatch.setattr(MemoryService, "_mem", lambda self: mock_client)
    m = MemoryService(api_key="x")
    m.add("u", "a", "uid")
