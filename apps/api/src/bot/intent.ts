import type { IntentType, Message, TenantConfigData } from "@autochat/shared";
import { completeHaiku } from "../services/llm.js";

const VALID: IntentType[] = [
  "greeting",
  "faq_price",
  "faq_hours",
  "faq_location",
  "faq_services",
  "faq_custom",
  "booking_request",
  "escalate",
  "fallback",
];

export function parseIntentToken(raw: string): IntentType {
  const line = (raw.trim().split("\n")[0] ?? "").trim().toLowerCase();
  const token = line.replace(/\.$/, "").split(/\s+/)[0] ?? "fallback";
  if (VALID.includes(token as IntentType)) return token as IntentType;
  const exact = line.replace(/\.$/, "");
  if (VALID.includes(exact as IntentType)) return exact as IntentType;
  return "fallback";
}

export async function detect(
  messageText: string,
  recentMessages: Message[],
  config: TenantConfigData
): Promise<IntentType> {
  const ctx = recentMessages.slice(-2).map((m) => ({
    role: m.role,
    content: m.content.slice(0, 200),
  }));
  const prompt = `Eres un clasificador de mensajes de WhatsApp para un negocio colombiano.
Negocio: ${config.vertical}. Palabra para cita/reserva: '${config.booking_noun}'.

Clasifica el mensaje. Responde SOLO con una de estas palabras exactas:
greeting | faq_price | faq_hours | faq_location | faq_services | faq_custom |
booking_request | escalate | fallback

Contexto (últimos 2 mensajes): ${JSON.stringify(ctx)}
Mensaje: ${JSON.stringify(messageText)}

Reglas:
- greeting: hola, buenas, buenos días/tardes/noches, primera interacción
- faq_price: precio, costo, valor, cuánto vale, cuánto cobran, tarifas
- faq_hours: horario, qué días, cuándo atienden, están abiertos
- faq_location: dónde quedan, dirección, cómo llegar, ubicación
- faq_services: qué hacen, servicios, qué ofrecen, qué tratan
- faq_custom: pregunta específica que puede estar en las FAQ personalizadas del negocio
- booking_request: quiero ${config.booking_noun}, ${config.booking_verb} una ${config.booking_noun},
  disponibilidad, cuándo tienen, turno, reservar
- escalate: hablar con alguien, queja, urgencia, emergencia, persona real, humano
- fallback: cualquier otra cosa`;
  const raw = await completeHaiku(prompt, 15);
  console.log(`[INTENT] raw=${raw.slice(0, 80)}`);
  return parseIntentToken(raw);
}
