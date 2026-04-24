import { z } from "zod";
import type { TenantConfigData } from "@autochat/shared";

const weekday = z.enum([
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
]);

export const tenantConfigZod = z.object({
  vertical: z.string(),
  services: z.array(
    z.object({
      name: z.string(),
      price: z.number(),
      duration_min: z.number(),
    })
  ),
  hours: z.string(),
  address: z.string(),
  phone: z.string(),
  tone: z.string(),
  escalation_phone: z.string(),
  booking_noun: z.enum(["cita", "turno", "sesión", "reserva", "consulta"]),
  booking_verb: z.enum(["agendar", "reservar", "programar", "solicitar"]),
  custom_faq: z
    .array(z.object({ question: z.string(), answer: z.string() }))
    .default([]),
  slots: z.array(
    z.object({
      day: weekday,
      times: z.array(z.string()),
    })
  ),
  currency_label: z.string(),
});

export function parseTenantConfig(raw: unknown): TenantConfigData | null {
  const r = tenantConfigZod.safeParse(raw);
  return r.success ? r.data : null;
}
