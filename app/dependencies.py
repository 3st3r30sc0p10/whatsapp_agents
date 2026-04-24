from functools import lru_cache

from anthropic import AsyncAnthropic

from app.config import Settings, get_settings
from app.core.agent import AgentService
from app.core.memory import MemoryService
from app.core.orchestrator import MessageOrchestrator
from app.db.queries import DatabaseService


@lru_cache
def _anthropic() -> AsyncAnthropic:
    s = get_settings()
    return AsyncAnthropic(api_key=s.anthropic_api_key)


@lru_cache
def _memory_service() -> MemoryService:
    s = get_settings()
    return MemoryService(api_key=s.mem0_api_key, max_results=s.max_memory_results)


@lru_cache
def _agent_service() -> AgentService:
    return AgentService(_anthropic(), get_settings())


@lru_cache
def _database_service() -> DatabaseService:
    return DatabaseService()


def get_orchestrator() -> MessageOrchestrator:
    return MessageOrchestrator(
        settings=get_settings(),
        memory=_memory_service(),
        agent=_agent_service(),
        db=_database_service(),
    )
