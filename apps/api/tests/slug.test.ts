import assert from "node:assert";
import { describe, it } from "node:test";
import { buildTenantSlugBase, generateUniqueTenantSlug } from "../src/utils/slug.js";

describe("slug helpers", () => {
  it("builds base slug with country, city and business", () => {
    const slug = buildTenantSlugBase({
      businessName: "Peluquería Ñandú Centro",
      address: "Cra 45 #10-22, Medellín",
    });
    assert.ok(slug.startsWith("co-medellin-peluqueria-nandu-centro"));
  });

  it("falls back when address has no city token", () => {
    const slug = buildTenantSlugBase({
      businessName: "Negocio",
      address: "",
    });
    assert.ok(slug.startsWith("co-general-negocio"));
  });

  it("returns unique slug with random suffix", async () => {
    let calls = 0;
    const slug = await generateUniqueTenantSlug(
      { businessName: "Glamour Studio", address: "Calle 1, Bogota" },
      async () => {
        calls += 1;
        return calls === 1;
      }
    );

    assert.ok(slug.startsWith("co-bogota-glamour-studio-"));
    assert.match(slug, /-[0-9a-f]{4}$/);
    assert.strictEqual(calls, 2);
  });
});
