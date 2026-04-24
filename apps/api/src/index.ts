import "dotenv/config";
import cors from "@fastify/cors";
import helmet from "@fastify/helmet";
import rateLimit from "@fastify/rate-limit";
import Fastify, { type FastifyRequest } from "fastify";
import { adminRoutes } from "./routes/admin.js";
import { onboardingRoutes } from "./routes/onboarding.js";
import { webhookRoutes } from "./routes/webhook.js";

async function main(): Promise<void> {
  const app = Fastify({ logger: true });
  await app.register(helmet);
  await app.register(cors, { origin: true });
  await app.register(rateLimit, {
    max: 200,
    timeWindow: "1 minute",
    allowList: (req: FastifyRequest) => (req.url ?? "").startsWith("/webhook/"),
  });

  app.get("/health", async () => ({
    status: "ok",
    uptime: process.uptime(),
    version: "1.0.0",
  }));

  await app.register(webhookRoutes);
  await app.register(onboardingRoutes);
  await app.register(adminRoutes, { prefix: "/admin" });

  const port = Number(process.env.APP_PORT ?? "3000");
  await app.listen({ port, host: "0.0.0.0" });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
