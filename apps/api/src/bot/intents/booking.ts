import type { BookingState, Tenant } from "@autochat/shared";
import { completeHaiku } from "../../services/llm.js";
import {
  createBooking,
  getAvailableSlotsForDate,
  isSlotAvailable,
  setBookingState,
} from "../../services/supabase.js";
import { formatDateES, formatTime12h } from "../../services/whatsapp.js";

function todayDateStr(): string {
  return new Date().toLocaleDateString("en-CA", {
    timeZone: "America/Bogota",
  });
}

function todayFormattedEs(): string {
  return new Date().toLocaleDateString("es-CO", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "America/Bogota",
  });
}

function dayOfWeekEn(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    timeZone: "America/Bogota",
  });
}

export function startBooking(tenant: Tenant): { text: string; state: BookingState } {
  const c = tenant.config;
  const currency = c.currency_label;
  const lines = c.services.map(
    (s, i) =>
      `${i + 1}. ${s.name} — ${s.price.toLocaleString("es-CO")} ${currency}`
  );
  const text = `¡Claro! ¿Para cuál de nuestros servicios quieres la ${c.booking_noun}?

${lines.join("\n")}

Responde con el número o el nombre del servicio.`;
  const state: BookingState = {
    step: "ask_service",
    selected_service: null,
    selected_date: null,
    selected_time: null,
  };
  console.log(`[BOOKING] start tenant:${tenant.slug}`);
  return { text, state };
}

async function extractServiceName(
  messageText: string,
  serviceNames: string[]
): Promise<string> {
  const prompt = `Services list: ${JSON.stringify(serviceNames)}
User message: ${JSON.stringify(messageText)}
Which service did the user choose? Reply with the exact service name from the list,
or NO_MATCH if unclear. Nothing else.`;
  const raw = await completeHaiku(prompt, 60);
  return raw.trim();
}

async function extractDateYmd(messageText: string): Promise<string> {
  const prompt = `Today is ${todayFormattedEs()} (${dayOfWeekEn()}).
User said: ${JSON.stringify(messageText)}
Extract the intended date and return it as YYYY-MM-DD. Nothing else.
If you cannot determine a clear date, return NO_DATE.`;
  const raw = await completeHaiku(prompt, 15);
  return raw.trim();
}

async function extractTimeHm(
  messageText: string,
  availableSlots: string[]
): Promise<string> {
  const prompt = `Available times: ${JSON.stringify(availableSlots)}
User said: ${JSON.stringify(messageText)}
Which time did they choose? Return HH:MM format. If unclear, return NO_TIME.`;
  const raw = await completeHaiku(prompt, 10);
  return raw.trim();
}

async function haikuYesNo(text: string): Promise<"yes" | "no"> {
  const prompt = `Does this message confirm a booking? ${JSON.stringify(text)}
Reply with exactly yes or no.`;
  const raw = (await completeHaiku(prompt, 5)).toLowerCase().trim();
  return raw.startsWith("y") ? "yes" : "no";
}

function isPositive(text: string): boolean {
  const x = text
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "");
  const hits = [
    "sí",
    " si",
    "si ",
    "si,",
    "yes",
    "claro",
    "dale",
    "confirmo",
    "ok",
    "perfecto",
    "listo",
    " va",
    "va ",
  ];
  return hits.some((h) => x.includes(h.trim() === "va" ? " va " : h) || x === "va");
}

function isNegative(text: string): boolean {
  const x = text
    .toLowerCase()
    .normalize("NFD")
    .replace(/\p{M}/gu, "");
  if (/\bcancelar\b/.test(x) || /\bnope\b/.test(x)) return true;
  if (/\bno\b/.test(x)) return true;
  return false;
}

export async function processBookingMessage(input: {
  tenant: Tenant;
  conversationId: string;
  contactPhone: string;
  contactName: string | null;
  messageText: string;
  state: BookingState;
}): Promise<{ responseText: string; newState: BookingState | null }> {
  const { tenant, conversationId, contactPhone, contactName, messageText, state } =
    input;
  const c = tenant.config;
  const svcNames = c.services.map((s) => s.name);

  if (state.step === "ask_service") {
    const raw = await extractServiceName(messageText, svcNames);
    const matched =
      raw !== "NO_MATCH" && svcNames.includes(raw)
        ? raw
        : svcNames.find((s) => s.toLowerCase() === raw.toLowerCase()) ??
          svcNames.find((s) => messageText.toLowerCase().includes(s.toLowerCase()));
    if (!matched) {
      return {
        responseText:
          "No entendí bien cuál servicio quieres. Por favor responde con el número o escribe el nombre del servicio.",
        newState: state,
      };
    }
    const next: BookingState = {
      step: "ask_date",
      selected_service: matched,
      selected_date: null,
      selected_time: null,
    };
    await setBookingState(conversationId, next);
    return {
      responseText: `Perfecto, *${matched}* 👌
¿Para qué fecha quieres tu ${c.booking_noun}?
Puedes decirme algo como 'mañana', 'el próximo lunes' o una fecha como '15 de enero'.`,
      newState: next,
    };
  }

  if (state.step === "ask_date" && state.selected_service) {
    const ymd = await extractDateYmd(messageText);
    if (ymd === "NO_DATE" || !/^\d{4}-\d{2}-\d{2}$/.test(ymd)) {
      return {
        responseText:
          "No entendí bien la fecha. ¿Puedes decirme el día y mes? Por ejemplo: 'el martes 20 de enero'.",
        newState: state,
      };
    }
    const today = todayDateStr();
    if (ymd < today) {
      return {
        responseText: `Esa fecha ya pasó. ¿Para qué día quieres la ${c.booking_noun}?`,
        newState: state,
      };
    }
    const slots = await getAvailableSlotsForDate(tenant.id, ymd, c.slots);
    if (!slots.length) {
      return {
        responseText: `Para el ${formatDateES(ymd)} no tenemos disponibilidad. ¿Quieres que revisemos otro día?`,
        newState: state,
      };
    }
    const next: BookingState = {
      step: "ask_time",
      selected_service: state.selected_service,
      selected_date: ymd,
      selected_time: null,
    };
    await setBookingState(conversationId, next);
    const slotLines = slots.map((t, i) => `${i + 1}. ${formatTime12h(t)}`);
    return {
      responseText: `Para el *${formatDateES(ymd)}* tenemos estos horarios disponibles:
${slotLines.join("\n")}
¿Cuál prefieres?`,
      newState: next,
    };
  }

  if (state.step === "ask_time" && state.selected_service && state.selected_date) {
    const slots = await getAvailableSlotsForDate(
      tenant.id,
      state.selected_date,
      c.slots
    );
    const hm = await extractTimeHm(messageText, slots);
    const normalized = hm.slice(0, 5);
    const valid = slots.find((t) => t.slice(0, 5) === normalized);
    if (hm === "NO_TIME" || !valid) {
      return {
        responseText:
          "No entendí el horario. Por favor elige un número de la lista o escribe la hora.",
        newState: state,
      };
    }
    const next: BookingState = {
      step: "confirm",
      selected_service: state.selected_service,
      selected_date: state.selected_date,
      selected_time: valid,
    };
    await setBookingState(conversationId, next);
    const fd = formatDateES(state.selected_date);
    return {
      responseText: `Perfecto, te confirmo tu ${c.booking_noun}:
📋 *Servicio:* ${state.selected_service}
📅 *Fecha:* ${fd}
⏰ *Hora:* ${formatTime12h(valid)}
📍 *Dirección:* ${c.address}

¿Confirmas? Responde *Sí* para confirmar o *No* para cancelar.`,
      newState: next,
    };
  }

  if (
    state.step === "confirm" &&
    state.selected_service &&
    state.selected_date &&
    state.selected_time
  ) {
    const pos = isPositive(messageText);
    const neg = isNegative(messageText);
    let polar: "yes" | "no" | "ambig";
    if (neg && !pos) polar = "no";
    else if (pos && !neg) polar = "yes";
    else polar = "ambig";

    if (polar === "ambig") {
      const yn = await haikuYesNo(messageText);
      polar = yn;
    }

    if (polar === "no") {
      await setBookingState(conversationId, null);
      return {
        responseText: `Sin problema, cancelamos esa ${c.booking_noun}. 😊
Cuando quieras ${c.booking_verb} una ${c.booking_noun}, aquí estamos.`,
        newState: null,
      };
    }

    if (polar === "yes") {
      const date = state.selected_date;
      const time = state.selected_time.slice(0, 5);
      const free = await isSlotAvailable(tenant.id, date, time);
      if (!free) {
        await setBookingState(conversationId, null);
        return {
          responseText:
            "Lo siento, ese horario acaba de ser tomado. ¿Quieres que revisemos otro horario para el mismo día?",
          newState: null,
        };
      }
      await createBooking({
        tenantId: tenant.id,
        conversationId,
        contactPhone,
        contactName,
        service: state.selected_service,
        bookingDate: date,
        bookingTime: time,
      });
      await setBookingState(conversationId, null);
      const noun =
        c.booking_noun.charAt(0).toUpperCase() + c.booking_noun.slice(1);
      return {
        responseText: `¡${noun} confirmada! 🎉
Te esperamos el *${formatDateES(date)}* a las *${formatTime12h(time)}*.
📍 ${c.address}
Si necesitas cancelar o reagendar, escríbenos con anticipación.
¡Hasta pronto! 😊`,
        newState: null,
      };
    }
  }

  return {
    responseText: `¿Confirmas la ${c.booking_noun}? Responde Sí o No.`,
    newState: state,
  };
}
