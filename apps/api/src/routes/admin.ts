import type { FastifyInstance, FastifyPluginAsync } from "fastify";
import { z } from "zod";
import {
  cleanOldProcessedMessages,
  getStatsAdmin,
  listBookingsAdmin,
  listConversationsAdmin,
  listTenantsAdmin,
  patchConversationStatus,
} from "../services/supabase.js";

function bearerOk(auth: string | undefined, token: string | undefined): boolean {
  if (!token) return false;
  const m = /^Bearer\s+(.+)$/i.exec(auth ?? "");
  return Boolean(m && m[1] === token);
}

export const adminRoutes: FastifyPluginAsync = async (app: FastifyInstance) => {
  app.addHook("preHandler", async (request, reply) => {
    const tok = process.env.ADMIN_TOKEN;
    if (!bearerOk(request.headers.authorization, tok)) {
      return reply.code(401).send({ error: "unauthorized" });
    }
  });

  app.get("/tenants", async () => {
    const tenants = await listTenantsAdmin();
    console.log(`[DB] admin list tenants count=${tenants.length}`);
    return { tenants };
  });

  app.get("/conversations", async (request) => {
    const q = z
      .object({
        tenant_slug: z.string().optional(),
        status: z.string().optional(),
        limit: z.coerce.number().min(1).max(200).default(50),
      })
      .parse(request.query);
    const rows = await listConversationsAdmin({
      tenantSlug: q.tenant_slug,
      status: q.status,
      limit: q.limit,
    });
    return { conversations: rows };
  });

  app.get("/bookings", async (request) => {
    const q = z
      .object({
        tenant_slug: z.string(),
        date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
      })
      .parse(request.query);
    const bookings = await listBookingsAdmin({
      tenantSlug: q.tenant_slug,
      date: q.date,
    });
    return { bookings };
  });

  app.get("/stats", async (request) => {
    const q = z.object({ tenant_slug: z.string() }).parse(request.query);
    const stats = await getStatsAdmin(q.tenant_slug);
    return stats;
  });

  app.patch<{ Params: { id: string } }>("/conversations/:id", async (request, reply) => {
    const body = z
      .object({ status: z.enum(["resolved", "open"]) })
      .parse(request.body);
    await patchConversationStatus(request.params.id, body.status);
    console.log(`[DB] admin patch conversation ${request.params.id} -> ${body.status}`);
    return { ok: true };
  });

  app.post("/processed-messages/cleanup", async () => {
    const n = await cleanOldProcessedMessages();
    console.log(`[DB] cleaned processed_messages rows=${n}`);
    return { deleted: n };
  });
};
