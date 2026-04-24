import type { FastifyInstance, FastifyPluginAsync, FastifyRequest } from "fastify";
import { z } from "zod";
import { handleMessage } from "../bot/handler.js";
import {
  getTenantBySlug,
  getTenantByWhatsappNumber,
  isDuplicate,
} from "../services/supabase.js";

const contactSchema = z.object({
  profile: z.object({ name: z.string().optional() }).optional(),
  wa_id: z.string().optional(),
});

const messageSchema = z
  .object({
    from: z.string(),
    id: z.string(),
    type: z.string(),
    timestamp: z.string(),
    text: z.object({ body: z.string() }).optional(),
  })
  .passthrough();

const dialog360WebhookBodySchema = z.object({
  contacts: z.array(contactSchema).optional(),
  messages: z.array(messageSchema),
});

const metaWebhookBodySchema = z
  .object({
    entry: z
      .array(
        z.object({
          changes: z
            .array(
              z.object({
                value: z.object({
                  metadata: z
                    .object({ phone_number_id: z.string().optional() })
                    .optional(),
                  contacts: z.array(contactSchema).optional(),
                  messages: z.array(messageSchema).optional(),
                }),
              })
            )
            .default([]),
        })
      )
      .default([]),
  })
  .passthrough();

function contactNameFromPayload(
  contacts: z.infer<typeof dialog360WebhookBodySchema>["contacts"],
  from: string
): string | null {
  const c = contacts?.find((x) => x.wa_id === from);
  const n = c?.profile?.name;
  return n && n.trim() ? n : null;
}

type IncomingEvent = {
  msg: z.infer<typeof messageSchema>;
  contacts?: z.infer<typeof contactSchema>[];
  phoneNumberId?: string;
};

function extractMetaEvents(body: unknown): IncomingEvent[] {
  const parsed = metaWebhookBodySchema.safeParse(body);
  if (!parsed.success) return [];
  const out: IncomingEvent[] = [];
  for (const entry of parsed.data.entry) {
    for (const change of entry.changes) {
      const phoneNumberId = change.value.metadata?.phone_number_id;
      for (const msg of change.value.messages ?? []) {
        out.push({ msg, contacts: change.value.contacts, phoneNumberId });
      }
    }
  }
  return out;
}

async function processEvents(
  request: FastifyRequest,
  events: IncomingEvent[],
  resolveTenant: (
    event: IncomingEvent
  ) => Promise<Awaited<ReturnType<typeof getTenantBySlug>>>
): Promise<void> {
  for (const event of events) {
    const { msg } = event;
    if (msg.type !== "text" || !msg.text?.body) continue;
    const wamid = msg.id;
    if (await isDuplicate(wamid)) {
      request.log.info({ wamid }, "[WEBHOOK] duplicate skip");
      continue;
    }
    const tenant = await resolveTenant(event);
    if (!tenant) {
      request.log.warn({ phoneNumberId: event.phoneNumberId }, "[WEBHOOK] tenant missing");
      continue;
    }
    const from = msg.from;
    const text = msg.text.body;
    const name = contactNameFromPayload(event.contacts, from);
    const ts = parseInt(msg.timestamp, 10);
    const userMessageAt = Number.isFinite(ts) ? new Date(ts * 1000) : new Date();
    void handleMessage({
      tenant,
      contactPhone: from,
      contactName: name,
      messageText: text,
      wamid,
      userMessageAt,
    }).catch((err) => {
      request.log.error(
        { err, slug: tenant.slug, from: from.slice(-4) },
        "[WEBHOOK] handler error"
      );
    });
  }
}

export const webhookRoutes: FastifyPluginAsync = async (
  app: FastifyInstance
) => {
  app.get("/webhook/meta", async (request, reply) => {
    const q = request.query as Record<string, string | undefined>;
    const mode = q["hub.mode"];
    const token = q["hub.verify_token"];
    const challenge = q["hub.challenge"];
    if (
      mode === "subscribe" &&
      token &&
      process.env.META_VERIFY_TOKEN &&
      token === process.env.META_VERIFY_TOKEN &&
      challenge
    ) {
      return reply.code(200).send(challenge);
    }
    return reply.code(403).send("forbidden");
  });

  app.post("/webhook/meta", async (request, reply) => {
    const events = extractMetaEvents(request.body);
    if (!events.length) {
      request.log.warn("[WEBHOOK] invalid meta body");
      return reply.code(200).send({ ok: true });
    }
    void processEvents(request, events, async (event) => {
      if (!event.phoneNumberId) return null;
      return getTenantByWhatsappNumber(event.phoneNumberId);
    }).catch((err) => {
      request.log.error({ err }, "[WEBHOOK] meta process error");
    });
    return reply.code(200).send({ ok: true });
  });

  app.post<{ Params: { slug: string } }>(
    "/webhook/:slug",
    async (request, reply) => {
      const slug = request.params.slug;
      const parsed = dialog360WebhookBodySchema.safeParse(request.body);
      if (!parsed.success) {
        request.log.warn({ err: parsed.error.flatten() }, "[WEBHOOK] invalid body");
        return reply.code(200).send({ ok: true });
      }
      const body = parsed.data;
      const events = body.messages.map((msg) => ({
        msg,
        contacts: body.contacts,
      }));
      void processEvents(request, events, async () => getTenantBySlug(slug)).catch((err) => {
        request.log.error({ err, slug }, "[WEBHOOK] process error");
      });
      return reply.code(200).send({ ok: true });
    }
  );
};
