import { randomBytes } from "node:crypto";

const MAX_SLUG_LEN = 50;
const COUNTRY_CODE = "co";
const DEFAULT_CITY = "general";
const DEFAULT_BUSINESS = "negocio";

function normalizeToken(value: string, fallback: string): string {
  const normalized = value
    .normalize("NFD")
    .replace(/\p{M}/gu, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return normalized || fallback;
}

function cityFromAddress(address: string): string {
  const parts = address
    .split(",")
    .map((p) => p.trim())
    .filter(Boolean);
  if (!parts.length) return DEFAULT_CITY;
  return normalizeToken(parts[parts.length - 1]!, DEFAULT_CITY);
}

function randomSuffix(size = 2): string {
  return randomBytes(size).toString("hex");
}

function trimBaseToFit(base: string, suffix: string): string {
  const maxBaseLen = MAX_SLUG_LEN - suffix.length - 1;
  const trimmed = base.slice(0, Math.max(1, maxBaseLen)).replace(/-+$/g, "");
  return trimmed || DEFAULT_BUSINESS;
}

export function buildTenantSlugBase(input: {
  businessName: string;
  address: string;
}): string {
  const city = cityFromAddress(input.address);
  const business = normalizeToken(input.businessName, DEFAULT_BUSINESS);
  return `${COUNTRY_CODE}-${city}-${business}`.slice(0, MAX_SLUG_LEN);
}

export async function generateUniqueTenantSlug(
  input: { businessName: string; address: string },
  exists: (slug: string) => Promise<boolean>
): Promise<string> {
  const base = buildTenantSlugBase(input);
  for (let i = 0; i < 30; i += 1) {
    const suffix = randomSuffix();
    const candidate = `${trimBaseToFit(base, suffix)}-${suffix}`;
    if (!(await exists(candidate))) return candidate;
  }
  throw new Error("Unable to generate unique tenant slug");
}
