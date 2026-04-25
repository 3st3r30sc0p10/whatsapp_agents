import type { IntentType, Tenant } from "@autochat/shared";
import { detect } from "./intent.js";
import {
  handleGreeting,
  handleHours,
  handleLocation,
  handlePrice,
  handleServices,
  matchCustomFaqAnswer,
} from "./intents/faq.js";
import { processBookingMessage, startBooking } from "./intents/booking.js";
import { handleEscalation } from "./intents/escalate.js";
import { handleFallback } from "./intents/fallback.js";
import {
  getRecentMessages,
  markProcessed,
  saveMessage,
  setBookingState,
  updateConversationStatus,
  upsertConversation,
} from "../services/supabase.js";
import { sendMessage } from "../services/whatsapp.js";

function last4(phone: string): string {
  return phone.replace(/\D/g, "").slice(-4);
}

export async function handleMessage(input: {
  tenant: Tenant;
  contactPhone: string;
  contactName: string | null;
  messageText: string;
  wamid: string;
  userMessageAt: Date;
}): Promise<void> {
  const { tenant, contactPhone, contactName, messageText, wamid, userMessageAt } =
    input;
  let intent: IntentType = "fallback";
  let statusSent: "sent" | "skipped" = "skipped";
  try {
    const conversation = await upsertConversation({
      tenantId: tenant.id,
      phone: contactPhone,
      name: contactName,
      lastUserMessageAt: userMessageAt,
    });

    try {
      await saveMessage({
        conversationId: conversation.id,
        wamid,
        role: "user",
        content: messageText,
      });
    } catch (e: unknown) {
      const err = e as { code?: string; message?: string };
      if (err.code === "23505" || err.message?.toLowerCase().includes("duplicate")) {
        console.log(`[HANDLER] duplicate message insert wamid:${wamid}`);
        return;
      }
      throw e;
    }

    await markProcessed(wamid);

    const recent = await getRecentMessages(conversation.id, 5);
    let responseText = "";

    if (conversation.booking_state?.step) {
      console.log(`[BOOKING] resume step:${conversation.booking_state.step}`);
      const out = await processBookingMessage({
        tenant,
        conversationId: conversation.id,
        contactPhone,
        contactName,
        messageText,
        state: conversation.booking_state,
      });
      responseText = out.responseText;
      intent = "booking_request";
    } else {
      intent = await detect(messageText, recent, tenant.config);
      console.log(`[INTENT] tenant:${tenant.slug} phone:${last4(contactPhone)} -> ${intent}`);

      if (intent === "booking_request") {
        const { text, state } = startBooking(tenant);
        responseText = text;
        await setBookingState(conversation.id, state);
      } else if (intent === "greeting") {
        responseText = handleGreeting(tenant, contactName);
      } else if (intent === "faq_price") {
        responseText = handlePrice(tenant.config);
      } else if (intent === "faq_hours") {
        responseText = handleHours(tenant.config);
      } else if (intent === "faq_location") {
        responseText = handleLocation(tenant.config);
      } else if (intent === "faq_services") {
        responseText = handleServices(tenant, tenant.config);
      } else if (intent === "faq_custom") {
        const ans = await matchCustomFaqAnswer(messageText, tenant.config);
        if (ans) {
          responseText = ans;
          console.log(`[FAQ] custom match tenant:${tenant.slug}`);
        } else {
          responseText = await handleFallback(tenant, recent, messageText);
          intent = "fallback";
        }
      } else if (intent === "escalate") {
        responseText = await handleEscalation(
          tenant,
          conversation,
          contactPhone,
          contactName
        );
      } else {
        responseText = await handleFallback(tenant, recent, messageText);
      }
    }

    const ok = await sendMessage(contactPhone, responseText);
    if (!ok) {
      await updateConversationStatus(conversation.id, "window_expired");
      statusSent = "skipped";
      console.log(
        `[HANDLER] tenant:${tenant.slug} phone:${last4(contactPhone)} intent:${intent} status:skipped`
      );
      return;
    }
    statusSent = "sent";
    await saveMessage({
      conversationId: conversation.id,
      wamid: null,
      role: "assistant",
      content: responseText,
    });
    console.log(
      `[HANDLER] tenant:${tenant.slug} phone:${last4(contactPhone)} intent:${intent} status:${statusSent}`
    );
  } catch (err) {
    console.error(`[HANDLER] error tenant:${tenant.slug}`, err);
    try {
      const conversation = await upsertConversation({
        tenantId: tenant.id,
        phone: contactPhone,
        name: contactName,
        lastUserMessageAt: userMessageAt,
      });
      const fb = `Disculpa, tuve un problema técnico. Por favor escríbenos de nuevo o llámanos al ${tenant.config.phone}. 🙏`;
      const ok = await sendMessage(contactPhone, fb);
      if (ok) {
        await saveMessage({
          conversationId: conversation.id,
          wamid: null,
          role: "assistant",
          content: fb,
        });
      }
    } catch (e2) {
      console.error(`[HANDLER] fallback failed tenant:${tenant.slug}`, e2);
    }
  }
}
