import type { Message, Tenant } from "@autochat/shared";
import type { MessageParam } from "@anthropic-ai/sdk/resources/messages";
import { completeSonnet } from "../../services/llm.js";

export async function handleFallback(
  tenant: Tenant,
  recentMessages: Message[],
  messageText: string
): Promise<string> {
  const c = tenant.config;
  const serviceNames = c.services.map((s) => s.name);
  const system = `Eres el asistente de WhatsApp de ${tenant.business_name}, un ${c.vertical} colombiano.
Tu tono es ${c.tone}.
Responde SIEMPRE en español colombiano natural. Tutea al cliente.
Sé breve: máximo 2-3 oraciones. Solo texto plano, sin markdown, sin asteriscos.
Si no sabes algo, di que lo consulten al ${c.phone}.
No inventes precios ni servicios.

Servicios que ofrecemos: ${serviceNames.join(", ")}
Horario: ${c.hours}
Dirección: ${c.address}`;
  const msgs: MessageParam[] = [
    ...recentMessages.map((m) => ({
      role: m.role,
      content: m.content,
    })),
    { role: "user", content: messageText },
  ];
  const text = await completeSonnet({
    system,
    messages: msgs,
    maxTokens: 200,
  });
  console.log(`[FAQ] fallback sonnet tenant:${tenant.slug}`);
  return text.trim() || `Para más detalle escríbenos o llámanos al ${c.phone}.`;
}
