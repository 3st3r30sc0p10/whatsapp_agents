import logging
from typing import Any

from mem0 import MemoryClient

logger = logging.getLogger(__name__)


class MemoryService:
    def __init__(self, api_key: str, max_results: int = 5) -> None:
        self._api_key = api_key
        self.max_results = max_results
        self._client: MemoryClient | None = None

    def _mem(self) -> MemoryClient:
        if self._client is None:
            self._client = MemoryClient(api_key=self._api_key)
        return self._client

    def search(self, query: str, user_id: str) -> list[str]:
        try:
            raw = self._mem().search(query, filters={"user_id": user_id}, limit=self.max_results)
        except Exception as exc:
            logger.warning("mem0_search_failed", extra={"error": str(exc), "user_id": user_id})
            return []
        return self._memories_to_strings(raw)

    def add(self, user_message: str, assistant_message: str, user_id: str) -> None:
        try:
            self._mem().add(
                [
                    {"role": "user", "content": user_message},
                    {"role": "assistant", "content": assistant_message},
                ],
                user_id=user_id,
            )
        except Exception as exc:
            logger.warning("mem0_add_failed", extra={"error": str(exc), "user_id": user_id})

    def get_all(self, user_id: str) -> list[dict[str, Any]]:
        try:
            raw = self._mem().get_all(filters={"user_id": user_id})
        except Exception as exc:
            logger.warning("mem0_get_all_failed", extra={"error": str(exc), "user_id": user_id})
            return []
        if isinstance(raw, dict) and "results" in raw:
            inner = raw["results"]
            return list(inner) if isinstance(inner, list) else []
        if isinstance(raw, list):
            return list(raw)
        return []

    def delete_all(self, user_id: str) -> None:
        try:
            self._mem().delete_all(user_id=user_id)
        except Exception as exc:
            logger.warning("mem0_delete_all_failed", extra={"error": str(exc), "user_id": user_id})

    @staticmethod
    def format_for_prompt(memories: list[str]) -> str:
        if not memories:
            return ""
        lines = "\n".join(f"- {m}" for m in memories)
        return f"Lo que sé de este cliente:\n{lines}\n"

    def _memories_to_strings(self, raw: Any) -> list[str]:
        if raw is None:
            return []
        items: list[Any]
        if isinstance(raw, dict):
            if "results" in raw and isinstance(raw["results"], list):
                items = raw["results"]
            elif "memories" in raw and isinstance(raw["memories"], list):
                items = raw["memories"]
            else:
                items = [raw]
        elif isinstance(raw, list):
            items = raw
        else:
            return []
        out: list[str] = []
        for it in items:
            if isinstance(it, str):
                out.append(it)
            elif isinstance(it, dict):
                t = it.get("memory") or it.get("text") or it.get("content")
                if isinstance(t, str):
                    out.append(t)
        return out[: self.max_results]
