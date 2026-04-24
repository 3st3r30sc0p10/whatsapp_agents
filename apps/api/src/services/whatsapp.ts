import axios, { type AxiosError } from "axios";
import type { Tenant } from "@autochat/shared";
import { isWithinSessionWindow } from "../bot/session.js";

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
  tenant: Tenant,
  conversationLastActive: Date | null,
  to: string,
  text: string
): Promise<boolean> {
  if (!isWithinSessionWindow(conversationLastActive)) {
    console.log(
      `[WA] session expired for ${to.slice(-4)}, tenant:${tenant.slug}, skipping send`
    );
    return false;
  }
  const base = process.env.D360_BASE_URL?.replace(/\/$/, "") ?? "";
  const key = process.env.D360_API_KEY;
  if (!key || !base) {
    console.error("[WA] send failed: D360 env missing");
    return false;
  }
  const url = `${base}/v1/messages`;
  const body = {
    messaging_product: "whatsapp",
    recipient_type: "individual",
    to,
    type: "text",
    text: { preview_url: false, body: text },
  };
  const postOnce = () =>
    axios.post(url, body, {
      headers: {
        "D360-API-KEY": key,
        "Content-Type": "application/json",
      },
      timeout: 30_000,
    });
  try {
    await postOnce();
    return true;
  } catch (e) {
    const err = e as AxiosError;
    const status = err.response?.status;
    if (status === 429) {
      await new Promise((r) => setTimeout(r, 2000));
      try {
        await postOnce();
        return true;
      } catch (e2) {
        const er = e2 as AxiosError;
        console.error(`[WA] send failed: ${er.message}`);
        return false;
      }
    }
    console.error(`[WA] send failed: ${err.message}`);
    return false;
  }
}

/** Staff alerts: treat as in-window so Meta policy for customer session does not block internal escalation. */
export async function sendStaffAlert(
  tenant: Tenant,
  toDigits: string,
  text: string
): Promise<boolean> {
  return sendMessage(tenant, new Date(), toDigits, text);
}
