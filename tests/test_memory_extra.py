from unittest.mock import MagicMock

import pytest

from app.core.memory import MemoryService


def test_get_all_dict_results(monkeypatch: pytest.MonkeyPatch):
    mock_client = MagicMock()
    mock_client.get_all.return_value = {"results": [{"id": "1", "memory": "x"}]}
    monkeypatch.setattr(MemoryService, "_mem", lambda self: mock_client)
    m = MemoryService("k")
    rows = m.get_all("u")
    assert len(rows) == 1
    assert rows[0]["memory"] == "x"


def test_get_all_list(monkeypatch: pytest.MonkeyPatch):
    mock_client = MagicMock()
    mock_client.get_all.return_value = [{"id": "1"}]
    monkeypatch.setattr(MemoryService, "_mem", lambda self: mock_client)
    m = MemoryService("k")
    assert m.get_all("u") == [{"id": "1"}]


def test_delete_all_error(monkeypatch: pytest.MonkeyPatch):
    mock_client = MagicMock()
    mock_client.delete_all.side_effect = RuntimeError("nope")
    monkeypatch.setattr(MemoryService, "_mem", lambda self: mock_client)
    MemoryService("k").delete_all("u")


def test_memories_to_strings_variants():
    m = MemoryService("k")
    assert m._memories_to_strings(None) == []
    assert m._memories_to_strings({"results": [{"memory": "a"}, {"text": "b"}]}) == ["a", "b"]
