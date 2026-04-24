import logging
from typing import Optional

import anthropic
from anthropic import AsyncAnthropic

from app.config import Settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Eres el asistente virtual de WhatsApp de {business_name}.

ROL: Atender clientes colombianos de manera cálida, útil y eficiente.

REGLAS OBLIGATORIAS:
1. Responde SIEMPRE en español colombiano natural (usa "usted" si el cliente lo usa, "tú" si el cliente lo usa)
2. Sé CONCISO: máximo 3-4 oraciones. Esto es WhatsApp, no un correo.
3. Usa el nombre del cliente si lo conoces.
4. Si el cliente dice "quiero hablar con una persona", "necesito un asesor" o similar, responde EXACTAMENTE: "Entendido [nombre si lo tienes], te conecto con un asesor de inmediato 🤝 [ESCALATE]" — no agregues nada más.
5. NUNCA inventes precios, productos, horarios o disponibilidad. Si no tienes la info, di: "Esa información la verifica un asesor en breve."
6. Para saludos iniciales, preséntate: "¡Hola! Soy el asistente virtual de {business_name}. ¿En qué te puedo ayudar?"
7. Termina los mensajes con una pregunta cuando sea apropiado, para mantener la conversación.

INFORMACIÓN DEL NEGOCIO:
{business_context}
"""


class AgentService:
    def __init__(self, anthropic_client: AsyncAnthropic, settings: Settings) -> None:
        self._client = anthropic_client
        self._settings = settings

    async def create_agent_and_environment(
        self, business_name: str, business_context: str
    ) -> tuple[str, str]:
        system = SYSTEM_PROMPT_TEMPLATE.format(
            business_name=business_name,
            business_context=business_context,
        )
        agent = await self._client.beta.agents.create(
            model=self._settings.agent_model,
            name=f"WhatsApp — {business_name}"[:256],
            system=system,
            tools=[{"type": "agent_toolset_20260401"}],
        )
        env = await self._client.beta.environments.create(
            name=f"Env — {business_name}"[:256],
            config={"type": "cloud"},
        )
        return agent.id, env.id

    async def get_or_create_session(
        self,
        client_phone: str,
        agent_id: str,
        environment_id: str,
        db_session_id: Optional[str],
    ) -> str:
        if db_session_id:
            try:
                await self._client.beta.sessions.retrieve(db_session_id)
                return db_session_id
            except anthropic.APIStatusError as exc:
                if exc.status_code != 404:
                    logger.warning(
                        "session_retrieve_failed",
                        extra={"session_id": db_session_id, "status": exc.status_code},
                    )
            except Exception as exc:
                logger.warning("session_retrieve_failed", extra={"error": str(exc)})

        session = await self._client.beta.sessions.create(
            agent=agent_id,
            environment_id=environment_id,
            title=f"wa:{client_phone}"[:512],
        )
        return session.id

    async def send_message(self, session_id: str, prompt: str) -> str:
        await self._client.beta.sessions.events.send(
            session_id,
            events=[
                {
                    "type": "user.message",
                    "content": [{"type": "text", "text": prompt}],
                }
            ],
        )
        parts: list[str] = []
        stream = await self._client.beta.sessions.events.stream(session_id)
        async with stream:
            async for event in stream:
                et = getattr(event, "type", None)
                if et == "agent.message":
                    for block in getattr(event, "content", []) or []:
                        if getattr(block, "type", None) == "text":
                            parts.append(block.text)
                elif et == "session.error":
                    msg = str(getattr(event, "error", "session error"))
                    raise RuntimeError(msg)
        text = "".join(parts).strip()
        if not text:
            raise RuntimeError("empty_agent_response")
        return text
