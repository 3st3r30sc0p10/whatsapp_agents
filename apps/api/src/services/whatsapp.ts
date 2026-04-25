import axios from "axios";
import type { Tenant } from "@autochat/shared";

export function formatTime12h(time: string): string {
  const [hStr, mStr] = time.slice(0, 5).split(":");
  let h = parseInt(hStr ?? "0", 10);
  const m = parseInt(mStr ?? "0", 10);
  const am = h < 12;
  const h12 = h % 12 === 0 ? 12 : h % 12;
  const mm = m.toString().padStart(2, "0");
  return `${h12}:${mm} ${am ? "a. m." : "p. m."}`;
}

export function formatDateES(date: string): string {
  const [y, mo, d] = date.split("-").map((x) => parseInt(x, 10));
  const dt = new Date(Date.UTC(y, mo - 1, d, 12, 0, 0));
  return dt.toLocaleDateString("es-CO", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "America/Bogota",
  });
}

export async function sendMessage(
  to: string,
  text: string
): Promise<boolean> {
  const phoneId = process.env.META_PHONE_ID;
  const token = process.env.META_TOKEN;
  if (!phoneId || !token) {
    console.error("[WA] Send failed: META_PHONE_ID or META_TOKEN missing");
    return false;
  }

  try {
    await axios.post(
      `https://graph.facebook.com/v18.0/${phoneId}/messages`,
      {
        messaging_product: "whatsapp",
        recipient_type: "individual",
        to,
        type: "text",
        text: { preview_url: false, body: text },
      },
      {
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      }
    );
    return true;
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err);
    console.error("[WA] Send failed:", message);
    return false;
  }
}

/** Staff alerts use the same outbound channel for now. */
export async function sendStaffAlert(
  _tenant: Tenant,
  toDigits: string,
  text: string
): Promise<boolean> {
  return sendMessage(toDigits, text);
}
