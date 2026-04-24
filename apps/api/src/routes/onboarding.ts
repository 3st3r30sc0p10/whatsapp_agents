import type { FastifyInstance, FastifyPluginAsync } from "fastify";
import { z } from "zod";
import { insertTenant, slugExists } from "../services/supabase.js";
import type { TenantConfigData } from "@autochat/shared";

const timeRe = /^([01]\d|2[0-3]):[0-5]\d$/;

const onboardingBodySchema = z.object({
  business_name: z.string().min(3).max(80),
  vertical: z.string().min(3).max(60),
  phone: z.string().regex(/^\+57[0-9]{10}$/),
  address: z.string().min(5).max(200),
  hours: z.string().min(5).max(200),
  escalation_phone: z.string().regex(/^\+57[0-9]{10}$/),
  tone: z.string().min(3).max(100),
  booking_noun: z.enum(["cita", "turno", "sesión", "reserva", "consulta"]),
  booking_verb: z.enum(["agendar", "reservar", "programar", "solicitar"]),
  currency_label: z.string().default("COP"),
  services: z
    .array(
      z.object({
        name: z.string().min(2).max(80),
        price: z.number().int().positive(),
        duration_min: z.number().int().positive(),
      })
    )
    .min(1)
    .max(15),
  custom_faq: z
    .array(
      z.object({
        question: z.string(),
        answer: z.string(),
      })
    )
    .max(10)
    .default([]),
  slots: z
    .array(
      z.object({
        day: z.enum([
          "monday",
          "tuesday",
          "wednesday",
          "thursday",
          "friday",
          "saturday",
          "sunday",
        ]),
        times: z.array(z.string().regex(timeRe)),
      })
    )
    .min(1),
});

function slugify(name: string): string {
  const noAcc = name.normalize("NFD").replace(/\p{M}/gu, "");
  const s = noAcc
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 40);
  return s || "negocio";
}

async function uniqueSlug(base: string): Promise<string> {
  let slug = base;
  let n = 2;
  while (await slugExists(slug)) {
    const suffix = `-${n}`;
    slug = (base.slice(0, Math.max(1, 40 - suffix.length)) + suffix).slice(0, 40);
    n += 1;
  }
  return slug;
}

export const onboardingRoutes: FastifyPluginAsync = async (
  app: FastifyInstance
) => {
  app.post(
    "/onboarding",
    {
      config: {
        rateLimit: {
          max: 5,
          timeWindow: "1 hour",
        },
      },
    },
    async (request, reply) => {
      const parsed = onboardingBodySchema.safeParse(request.body);
      if (!parsed.success) {
        return reply.code(400).send({ error: parsed.error.flatten() });
      }
      const b = parsed.data;
      const config: TenantConfigData = {
        vertical: b.vertical,
        services: b.services,
        hours: b.hours,
        address: b.address,
        phone: b.phone,
        tone: b.tone,
        escalation_phone: b.escalation_phone,
        booking_noun: b.booking_noun,
        booking_verb: b.booking_verb,
        custom_faq: b.custom_faq,
        slots: b.slots,
        currency_label: b.currency_label,
      };
      const baseSlug = slugify(b.business_name);
      const slug = await uniqueSlug(baseSlug);
      await insertTenant({
        slug,
        business_name: b.business_name,
        whatsapp_number: null,
        config,
      });
      const domain =
        process.env.RAILWAY_PUBLIC_DOMAIN?.replace(/^https?:\/\//, "") ||
        "tu-dominio.com";
      const webhook_url = `https://${domain}/webhook/${slug}`;
      console.log(`[DB] onboarding tenant slug=${slug}`);
      return {
        success: true,
        slug,
        webhook_url,
        message:
          "Tu bot está listo. Configura este webhook URL en tu cuenta de 360dialog.",
      };
    }
  );
};
