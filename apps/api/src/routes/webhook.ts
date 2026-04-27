import type { FastifyInstance, FastifyPluginAsync, FastifyRequest } from "fastify";
import { z } from "zod";
import { handleMessage } from "../bot/handler.js";
import {
  getTenantBySlug,
  getTenantByWhatsappNumber,
  insertMessageStatusEvent,
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

const statusSchema = z
  .object({
    id: z.string().optional(),
    status: z.string(),
    timestamp: z.string().optional(),
    recipient_id: z.string().optional(),
    conversation: z
      .object({
        id: z.string().optional(),
        origin: z.object({ type: z.string().optional() }).optional(),
      })
      .optional(),
    pricing: z
      .object({
        billable: z.boolean().optional(),
        category: z.string().optional(),
      })
      .optional(),
    errors: z.array(z.unknown()).optional(),
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
                  statuses: z.array(statusSchema).optional(),
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

type IncomingStatusEvent = {
  status: z.infer<typeof statusSchema>;
  phoneNumberId?: string;
};

function maskPhone(phone: string): string {
  if (!phone) return "unknown";
  return phone.length <= 4 ? phone : `***${phone.slice(-4)}`;
}

function parseMetaTimestamp(ts?: string): string {
  if (!ts) return "unknown";
  const parsed = parseInt(ts, 10);
  if (!Number.isFinite(parsed)) return "unknown";
  return new Date(parsed * 1000).toISOString();
}

function getHubVerificationParams(request: FastifyRequest): {
  mode: string | null;
  token: string | null;
  challenge: string | null;
} {
  const rawUrl = request.raw.url ?? "";
  const queryString = rawUrl.includes("?") ? rawUrl.slice(rawUrl.indexOf("?") + 1) : "";
  const params = new URLSearchParams(queryString);
  return {
    mode: params.get("hub.mode"),
    token: params.get("hub.verify_token"),
    challenge: params.get("hub.challenge"),
  };
}

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

function extractMetaStatusEvents(body: unknown): IncomingStatusEvent[] {
  const parsed = metaWebhookBodySchema.safeParse(body);
  if (!parsed.success) return [];
  const out: IncomingStatusEvent[] = [];
  for (const entry of parsed.data.entry) {
    for (const change of entry.changes) {
      const phoneNumberId = change.value.metadata?.phone_number_id;
      for (const status of change.value.statuses ?? []) {
        out.push({ status, phoneNumberId });
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
    request.log.info(
      {
        phoneNumberId: event.phoneNumberId ?? "unknown",
        from: maskPhone(from),
        name: name ?? "unknown",
        wamid,
        at: userMessageAt.toISOString(),
        type: msg.type,
        textPreview: text.slice(0, 120),
      },
      "[WEBHOOK] inbound message"
    );
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

async function processStatusEvents(
  request: FastifyRequest,
  statusEvents: IncomingStatusEvent[]
): Promise<void> {
  for (const ev of statusEvents) {
    const wamid = ev.status.id;
    if (!wamid) continue;
    const statusAt = parseMetaTimestamp(ev.status.timestamp);
    request.log.info(
      {
        phoneNumberId: ev.phoneNumberId ?? "unknown",
        status: ev.status.status,
        wamid,
        to: ev.status.recipient_id ? maskPhone(ev.status.recipient_id) : "unknown",
        at: statusAt,
        conversationId: ev.status.conversation?.id ?? "unknown",
        originType: ev.status.conversation?.origin?.type ?? "unknown",
        billable: ev.status.pricing?.billable ?? null,
        category: ev.status.pricing?.category ?? "unknown",
        hasErrors: Boolean(ev.status.errors?.length),
      },
      "[WEBHOOK] outbound status update"
    );
    try {
      await insertMessageStatusEvent({
        wamid,
        status: ev.status.status,
        recipient_id: ev.status.recipient_id ?? null,
        phone_number_id: ev.phoneNumberId ?? null,
        status_at: statusAt === "unknown" ? null : statusAt,
        conversation_id: ev.status.conversation?.id ?? null,
        origin_type: ev.status.conversation?.origin?.type ?? null,
        billable: ev.status.pricing?.billable ?? null,
        pricing_category: ev.status.pricing?.category ?? null,
        raw: ev.status,
      });
    } catch (err) {
      request.log.error(
        { err, wamid, status: ev.status.status },
        "[WEBHOOK] status persistence error"
      );
    }
  }
}

export const webhookRoutes: FastifyPluginAsync = async (
  app: FastifyInstance
) => {
  app.get<{ Params: { slug: string } }>("/webhook/:slug", async (request, reply) => {
    const { mode, token, challenge } = getHubVerificationParams(request);
    if (mode === "subscribe" && token === process.env.META_VERIFY_TOKEN && challenge) {
      return reply.code(200).send(parseInt(challenge, 10));
    }
    return reply.code(403).send("forbidden");
  });

  app.get("/webhook/meta", async (request, reply) => {
    const { mode, token, challenge } = getHubVerificationParams(request);
    if (
      mode === "subscribe" &&
      token === process.env.META_VERIFY_TOKEN &&
      challenge
    ) {
      return reply.code(200).send(challenge);
    }
    return reply.code(403).send("forbidden");
  });

  app.post("/webhook/meta", async (request, reply) => {
    const events = extractMetaEvents(request.body);
    const statusEvents = extractMetaStatusEvents(request.body);
    if (!events.length && !statusEvents.length) {
      request.log.warn("[WEBHOOK] invalid meta body");
      return reply.code(200).send({ ok: true });
    }
    void processStatusEvents(request, statusEvents).catch((err) => {
      request.log.error({ err }, "[WEBHOOK] meta status process error");
    });
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
