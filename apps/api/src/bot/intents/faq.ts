import type { Tenant, TenantConfigData } from "@autochat/shared";
import { completeHaiku } from "../../services/llm.js";

export function handleGreeting(tenant: Tenant, contactName: string | null): string {
  const c = tenant.config;
  const name = contactName ? ` ${contactName}` : "";
  const v = c.booking_verb.charAt(0).toUpperCase() + c.booking_verb.slice(1);
  return `¡Hola${name}! 👋 Bienvenido/a a *${tenant.business_name}*.
Soy el asistente virtual. Puedo ayudarte con:
- Información sobre nuestros servicios y precios
- Nuestro horario y ubicación
- ${v} una ${c.booking_noun}
¿En qué te puedo ayudar?`;
}

export function handlePrice(config: TenantConfigData): string {
  const lines = config.services.map(
    (s) =>
      `• ${s.name}: ${s.price.toLocaleString("es-CO")} ${config.currency_label}`
  );
  return `Nuestros servicios y precios:
${lines.join("\n")}

¿Te gustaría ${config.booking_verb} una ${config.booking_noun}?`;
}

export function handleHours(config: TenantConfigData): string {
  return `Nuestro horario de atención:
📅 ${config.hours}
📍 ${config.address}
¿Quieres ${config.booking_verb} una ${config.booking_noun}?`;
}

export function handleLocation(config: TenantConfigData): string {
  return `Nos encuentras aquí:
📍 ${config.address}
📅 Horario: ${config.hours}
📞 ${config.phone}
¿Necesitas ${config.booking_verb} una ${config.booking_noun}?`;
}

export function handleServices(tenant: Tenant, config: TenantConfigData): string {
  const lines = config.services.map((s) => `• ${s.name}`);
  return `En ${tenant.business_name} ofrecemos:
${lines.join("\n")}
¿Quieres saber el precio de algún servicio en particular, o prefieres ${config.booking_verb} una ${config.booking_noun}?`;
}

export async function matchCustomFaqAnswer(
  messageText: string,
  config: TenantConfigData
): Promise<string | null> {
  if (!config.custom_faq.length) return null;
  const prompt = `Given these FAQ pairs: ${JSON.stringify(config.custom_faq)}
Which answer best responds to: ${JSON.stringify(messageText)}?
Reply with ONLY the answer text, nothing else.
If no FAQ matches well, reply with exactly: NO_MATCH`;
  const raw = await completeHaiku(prompt, 150);
  const t = raw.trim();
  if (t === "NO_MATCH" || !t) return null;
  return t;
}
