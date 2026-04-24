import type { FastifyInstance, FastifyPluginAsync } from "fastify";
import { z } from "zod";
import { handleMessage } from "../bot/handler.js";
import { isDuplicate, getTenantBySlug } from "../services/supabase.js";

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

function contactNameFromPayload(
  contacts: z.infer<typeof dialog360WebhookBodySchema>["contacts"],
  from: string
): string | null {
  const c = contacts?.find((x) => x.wa_id === from);
  const n = c?.profile?.name;
  return n && n.trim() ? n : null;
}

export const webhookRoutes: FastifyPluginAsync = async (
  app: FastifyInstance
) => {
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
      void (async () => {
        try {
          for (const msg of body.messages) {
            if (msg.type !== "text" || !msg.text?.body) continue;
            const wamid = msg.id;
            if (await isDuplicate(wamid)) {
              request.log.info({ wamid }, "[WEBHOOK] duplicate skip");
              continue;
            }
            const tenant = await getTenantBySlug(slug);
            if (!tenant) {
              request.log.warn({ slug }, "[WEBHOOK] tenant missing or inactive");
              continue;
            }
            const from = msg.from;
            const text = msg.text.body;
            const name = contactNameFromPayload(body.contacts, from);
            const ts = parseInt(msg.timestamp, 10);
            const userMessageAt = Number.isFinite(ts)
              ? new Date(ts * 1000)
              : new Date();
            void handleMessage({
              tenant,
              contactPhone: from,
              contactName: name,
              messageText: text,
              wamid,
              userMessageAt,
            }).catch((err) => {
              request.log.error(
                { err, slug, from: from.slice(-4) },
                "[WEBHOOK] handler error"
              );
            });
          }
        } catch (err) {
          request.log.error({ err, slug }, "[WEBHOOK] process error");
        }
      })();
      return reply.code(200).send({ ok: true });
    }
  );
};
