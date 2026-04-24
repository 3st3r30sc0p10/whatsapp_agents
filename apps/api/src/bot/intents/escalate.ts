import type { Conversation, Tenant } from "@autochat/shared";
import { sendStaffAlert } from "../../services/whatsapp.js";
import { updateConversationStatus } from "../../services/supabase.js";

function digitsOnly(phone: string): string {
  return phone.replace(/\D/g, "");
}

export async function handleEscalation(
  tenant: Tenant,
  conversation: Conversation,
  contactPhone: string,
  contactName: string | null
): Promise<string> {
  await updateConversationStatus(conversation.id, "escalated");
  const esc = digitsOnly(tenant.config.escalation_phone);
  if (esc) {
    const body = `🔔 *Atención requerida*
Cliente: ${contactName || contactPhone}
Número: ${contactPhone}
Negocio: ${tenant.business_name}
Revisa el dashboard para ver la conversación.`;
    const ok = await sendStaffAlert(tenant, esc, body);
    if (!ok) console.log(`[FAQ] escalation WA notify failed tenant:${tenant.slug}`);
  }
  return `Entendido, ya le avisé a nuestro equipo. 🙏
Alguien te contactará muy pronto.
Si es urgente, también puedes llamarnos directamente al ${tenant.config.phone}.`;
}
