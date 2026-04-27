import { createClient, type SupabaseClient } from "@supabase/supabase-js";
import type {
  Booking,
  BookingState,
  Conversation,
  Message,
  Tenant,
  Weekday,
} from "@autochat/shared";
import { parseTenantConfig } from "../tenantConfig.js";

let client: SupabaseClient | null = null;

export type MessageStatusEventInput = {
  wamid: string;
  status: string;
  recipient_id: string | null;
  phone_number_id: string | null;
  status_at: string | null;
  conversation_id: string | null;
  origin_type: string | null;
  billable: boolean | null;
  pricing_category: string | null;
  raw: unknown;
};

function db(): SupabaseClient {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY missing");
  if (!client) client = createClient(url, key);
  return client;
}

function mapTenant(row: Record<string, unknown>): Tenant | null {
  const cfg = parseTenantConfig(row.config);
  if (!cfg) return null;
  return {
    id: String(row.id),
    slug: String(row.slug),
    business_name: String(row.business_name),
    whatsapp_number:
      row.whatsapp_number != null ? String(row.whatsapp_number) : null,
    active: Boolean(row.active ?? true),
    created_at: String(row.created_at ?? ""),
    config: cfg,
  };
}

function mapConversation(row: Record<string, unknown>): Conversation {
  return {
    id: String(row.id),
    tenant_id: String(row.tenant_id),
    contact_phone: String(row.contact_phone),
    contact_name: row.contact_name != null ? String(row.contact_name) : null,
    status: row.status as Conversation["status"],
    last_user_message_at:
      row.last_user_message_at != null ? String(row.last_user_message_at) : null,
    booking_state: (row.booking_state as BookingState | null) ?? null,
    created_at: String(row.created_at ?? ""),
  };
}

function mapMessage(row: Record<string, unknown>): Message {
  return {
    id: String(row.id),
    conversation_id: String(row.conversation_id),
    wamid: row.wamid != null ? String(row.wamid) : null,
    role: row.role as Message["role"],
    content: String(row.content),
    created_at: String(row.created_at ?? ""),
  };
}

function mapBooking(row: Record<string, unknown>): Booking {
  return {
    id: String(row.id),
    tenant_id: String(row.tenant_id),
    conversation_id:
      row.conversation_id != null ? String(row.conversation_id) : null,
    contact_phone: String(row.contact_phone),
    contact_name: row.contact_name != null ? String(row.contact_name) : null,
    service: String(row.service),
    booking_date: String(row.booking_date),
    booking_time: String(row.booking_time).slice(0, 5),
    status: row.status as Booking["status"],
    created_at: String(row.created_at ?? ""),
  };
}

export async function getTenantBySlug(slug: string): Promise<Tenant | null> {
  const { data, error } = await db()
    .from("tenants")
    .select("*")
    .eq("slug", slug)
    .eq("active", true)
    .maybeSingle();
  if (error || !data) return null;
  return mapTenant(data as Record<string, unknown>);
}

export async function getTenantByWhatsappNumber(
  whatsappNumber: string
): Promise<Tenant | null> {
  const { data, error } = await db()
    .from("tenants")
    .select("*")
    .eq("whatsapp_number", whatsappNumber)
    .eq("active", true)
    .maybeSingle();
  if (error || !data) return null;
  return mapTenant(data as Record<string, unknown>);
}

export async function getTenantIdBySlug(slug: string): Promise<string | null> {
  const { data, error } = await db()
    .from("tenants")
    .select("id")
    .eq("slug", slug)
    .eq("active", true)
    .maybeSingle();
  if (error || !data?.id) return null;
  return String(data.id);
}

export async function upsertConversation(input: {
  tenantId: string;
  phone: string;
  name: string | null;
  lastUserMessageAt: Date;
}): Promise<Conversation> {
  const iso = input.lastUserMessageAt.toISOString();
  const { error: upErr } = await db()
    .from("conversations")
    .upsert(
      {
        tenant_id: input.tenantId,
        contact_phone: input.phone,
        contact_name: input.name,
        last_user_message_at: iso,
        status: "open",
      },
      { onConflict: "tenant_id,contact_phone" }
    );
  if (upErr) throw upErr;
  const { data, error } = await db()
    .from("conversations")
    .select("*")
    .eq("tenant_id", input.tenantId)
    .eq("contact_phone", input.phone)
    .single();
  if (error || !data) throw error ?? new Error("conversation missing");
  return mapConversation(data as Record<string, unknown>);
}

export async function updateLastMessageAt(
  conversationId: string,
  at: Date
): Promise<void> {
  const { error } = await db()
    .from("conversations")
    .update({ last_user_message_at: at.toISOString() })
    .eq("id", conversationId);
  if (error) throw error;
}

export async function saveMessage(input: {
  conversationId: string;
  wamid: string | null;
  role: Message["role"];
  content: string;
}): Promise<void> {
  const { error } = await db().from("messages").insert({
    conversation_id: input.conversationId,
    wamid: input.wamid,
    role: input.role,
    content: input.content,
  });
  if (error) throw error;
}

export async function isDuplicate(wamid: string): Promise<boolean> {
  const { data, error } = await db()
    .from("processed_messages")
    .select("wamid")
    .eq("wamid", wamid)
    .maybeSingle();
  if (error) throw error;
  return Boolean(data?.wamid);
}

export async function markProcessed(wamid: string): Promise<void> {
  const { error } = await db().from("processed_messages").insert({ wamid });
  if (error) throw error;
}

export async function insertMessageStatusEvent(
  input: MessageStatusEventInput
): Promise<void> {
  const { error } = await db().from("message_status_events").insert({
    wamid: input.wamid,
    status: input.status,
    recipient_id: input.recipient_id,
    phone_number_id: input.phone_number_id,
    status_at: input.status_at,
    conversation_id: input.conversation_id,
    origin_type: input.origin_type,
    billable: input.billable,
    pricing_category: input.pricing_category,
    raw: input.raw,
  });
  if (error) throw error;
}

/** Returns false if wamid was already processed (race-safe). */
export async function tryMarkProcessed(wamid: string): Promise<boolean> {
  const { error } = await db().from("processed_messages").insert({ wamid });
  if (error) {
    if (error.code === "23505" || error.message.toLowerCase().includes("duplicate"))
      return false;
    throw error;
  }
  return true;
}

export async function getRecentMessages(
  conversationId: string,
  limit: number
): Promise<Message[]> {
  const { data, error } = await db()
    .from("messages")
    .select("*")
    .eq("conversation_id", conversationId)
    .order("created_at", { ascending: false })
    .limit(limit);
  if (error) throw error;
  const rows = (data ?? []) as Record<string, unknown>[];
  return rows.map(mapMessage).reverse();
}

export async function getBookingState(
  conversationId: string
): Promise<BookingState | null> {
  const { data, error } = await db()
    .from("conversations")
    .select("booking_state")
    .eq("id", conversationId)
    .maybeSingle();
  if (error || !data) return null;
  return (data.booking_state as BookingState | null) ?? null;
}

export async function setBookingState(
  conversationId: string,
  state: BookingState | null
): Promise<void> {
  const { error } = await db()
    .from("conversations")
    .update({ booking_state: state })
    .eq("id", conversationId);
  if (error) throw error;
}

export function weekdayFromDateStr(dateStr: string): Weekday {
  const [y, m, d] = dateStr.split("-").map((x) => parseInt(x, 10));
  const dt = new Date(Date.UTC(y, m - 1, d, 12, 0, 0));
  const names: Weekday[] = [
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
  ];
  return names[dt.getUTCDay()]!;
}

export async function getAvailableSlotsForDate(
  tenantId: string,
  dateStr: string,
  configSlots: Tenant["config"]["slots"]
): Promise<string[]> {
  const wd = weekdayFromDateStr(dateStr);
  const dayCfg = configSlots.find((s) => s.day === wd);
  const fromConfig = dayCfg?.times ?? [];
  const { data, error } = await db()
    .from("bookings")
    .select("booking_time")
    .eq("tenant_id", tenantId)
    .eq("booking_date", dateStr)
    .neq("status", "cancelled");
  if (error) throw error;
  const taken = new Set(
    ((data ?? []) as { booking_time: string }[]).map((r) =>
      String(r.booking_time).slice(0, 5)
    )
  );
  return fromConfig.filter((t) => !taken.has(t.slice(0, 5)));
}

export async function isSlotAvailable(
  tenantId: string,
  date: string,
  time: string
): Promise<boolean> {
  const t = time.slice(0, 5);
  const { data, error } = await db()
    .from("bookings")
    .select("id")
    .eq("tenant_id", tenantId)
    .eq("booking_date", date)
    .eq("booking_time", t)
    .neq("status", "cancelled")
    .maybeSingle();
  if (error) throw error;
  return !data?.id;
}

export async function createBooking(input: {
  tenantId: string;
  conversationId: string | null;
  contactPhone: string;
  contactName: string | null;
  service: string;
  bookingDate: string;
  bookingTime: string;
}): Promise<Booking> {
  const t = input.bookingTime.slice(0, 5);
  const { data, error } = await db()
    .from("bookings")
    .insert({
      tenant_id: input.tenantId,
      conversation_id: input.conversationId,
      contact_phone: input.contactPhone,
      contact_name: input.contactName,
      service: input.service,
      booking_date: input.bookingDate,
      booking_time: t,
      status: "confirmed",
    })
    .select("*")
    .single();
  if (error) throw error;
  return mapBooking(data as Record<string, unknown>);
}

export async function updateConversationStatus(
  conversationId: string,
  status: Conversation["status"]
): Promise<void> {
  const { error } = await db()
    .from("conversations")
    .update({ status })
    .eq("id", conversationId);
  if (error) throw error;
}

export async function cleanOldProcessedMessages(): Promise<number> {
  const cutoff = new Date(Date.now() - 48 * 3600 * 1000).toISOString();
  const { data: rows, error: selErr } = await db()
    .from("processed_messages")
    .select("wamid")
    .lt("processed_at", cutoff);
  if (selErr) throw selErr;
  const ids = (rows ?? []).map((r: { wamid: string }) => r.wamid);
  if (!ids.length) return 0;
  const { error: delErr } = await db()
    .from("processed_messages")
    .delete()
    .in("wamid", ids);
  if (delErr) throw delErr;
  return ids.length;
}

export async function insertTenant(input: {
  slug: string;
  business_name: string;
  whatsapp_number: string | null;
  config: Tenant["config"];
}): Promise<Tenant> {
  const { data, error } = await db()
    .from("tenants")
    .insert({
      slug: input.slug,
      business_name: input.business_name,
      whatsapp_number: input.whatsapp_number,
      config: input.config,
      active: true,
    })
    .select("*")
    .single();
  if (error) throw error;
  const t = mapTenant(data as Record<string, unknown>);
  if (!t) throw new Error("invalid tenant config");
  return t;
}

export async function slugExists(slug: string): Promise<boolean> {
  const { data, error } = await db()
    .from("tenants")
    .select("id")
    .eq("slug", slug)
    .maybeSingle();
  if (error) throw error;
  return Boolean(data?.id);
}

export async function listTenantsAdmin(): Promise<
  { id: string; slug: string; business_name: string; vertical: string; created_at: string }[]
> {
  const { data, error } = await db()
    .from("tenants")
    .select("id, slug, business_name, created_at, config")
    .eq("active", true)
    .order("created_at", { ascending: false });
  if (error) throw error;
  return ((data ?? []) as Record<string, unknown>[]).map((row) => {
    const cfg = parseTenantConfig(row.config);
    return {
      id: String(row.id),
      slug: String(row.slug),
      business_name: String(row.business_name),
      vertical: cfg?.vertical ?? "",
      created_at: String(row.created_at ?? ""),
    };
  });
}

export async function listConversationsAdmin(input: {
  tenantSlug?: string;
  status?: string;
  limit: number;
}): Promise<
  {
    id: string;
    tenant_slug: string;
    contact_phone: string;
    contact_name: string | null;
    status: string;
    last_user_message_at: string | null;
    last_preview: string | null;
  }[]
> {
  let q = db()
    .from("conversations")
    .select("id, tenant_id, contact_phone, contact_name, status, last_user_message_at")
    .order("last_user_message_at", { ascending: false, nullsFirst: false })
    .limit(input.limit);
  if (input.status) q = q.eq("status", input.status);
  if (input.tenantSlug) {
    const tid = await getTenantIdBySlug(input.tenantSlug);
    if (!tid) return [];
    q = q.eq("tenant_id", tid);
  }
  const { data, error } = await q;
  if (error) throw error;
  const rows = (data ?? []) as Record<string, unknown>[];
  const out: Awaited<ReturnType<typeof listConversationsAdmin>> = [];
  for (const r of rows) {
    const { data: slugRow } = await db()
      .from("tenants")
      .select("slug")
      .eq("id", String(r.tenant_id))
      .maybeSingle();
    const { data: lastMsg } = await db()
      .from("messages")
      .select("content")
      .eq("conversation_id", String(r.id))
      .order("created_at", { ascending: false })
      .limit(1)
      .maybeSingle();
    out.push({
      id: String(r.id),
      tenant_slug: String(slugRow?.slug ?? ""),
      contact_phone: String(r.contact_phone),
      contact_name: r.contact_name != null ? String(r.contact_name) : null,
      status: String(r.status),
      last_user_message_at:
        r.last_user_message_at != null ? String(r.last_user_message_at) : null,
      last_preview: lastMsg?.content != null ? String(lastMsg.content).slice(0, 120) : null,
    });
  }
  return out;
}

export async function listBookingsAdmin(input: {
  tenantSlug: string;
  date: string;
}): Promise<Booking[]> {
  const tid = await getTenantIdBySlug(input.tenantSlug);
  if (!tid) return [];
  const { data, error } = await db()
    .from("bookings")
    .select("*")
    .eq("tenant_id", tid)
    .eq("booking_date", input.date)
    .order("booking_time", { ascending: true });
  if (error) throw error;
  return ((data ?? []) as Record<string, unknown>[]).map(mapBooking);
}

export async function getStatsAdmin(tenantSlug: string): Promise<{
  total_conversations: number;
  open_conversations: number;
  escalated_conversations: number;
  bookings_today: number;
  bookings_this_week: number;
  window_expired_conversations: number;
}> {
  const tid = await getTenantIdBySlug(tenantSlug);
  if (!tid) {
    return {
      total_conversations: 0,
      open_conversations: 0,
      escalated_conversations: 0,
      bookings_today: 0,
      bookings_this_week: 0,
      window_expired_conversations: 0,
    };
  }
  const { count: total } = await db()
    .from("conversations")
    .select("*", { count: "exact", head: true })
    .eq("tenant_id", tid);
  const { count: openC } = await db()
    .from("conversations")
    .select("*", { count: "exact", head: true })
    .eq("tenant_id", tid)
    .eq("status", "open");
  const { count: esc } = await db()
    .from("conversations")
    .select("*", { count: "exact", head: true })
    .eq("tenant_id", tid)
    .eq("status", "escalated");
  const { count: win } = await db()
    .from("conversations")
    .select("*", { count: "exact", head: true })
    .eq("tenant_id", tid)
    .eq("status", "window_expired");
  const today = new Date().toISOString().slice(0, 10);
  const { count: bToday } = await db()
    .from("bookings")
    .select("*", { count: "exact", head: true })
    .eq("tenant_id", tid)
    .eq("booking_date", today);
  const weekAgo = new Date(Date.now() - 7 * 24 * 3600 * 1000)
    .toISOString()
    .slice(0, 10);
  const { count: bWeek } = await db()
    .from("bookings")
    .select("*", { count: "exact", head: true })
    .eq("tenant_id", tid)
    .gte("booking_date", weekAgo);
  return {
    total_conversations: total ?? 0,
    open_conversations: openC ?? 0,
    escalated_conversations: esc ?? 0,
    bookings_today: bToday ?? 0,
    bookings_this_week: bWeek ?? 0,
    window_expired_conversations: win ?? 0,
  };
}

export async function patchConversationStatus(
  id: string,
  status: "resolved" | "open"
): Promise<void> {
  const { error } = await db().from("conversations").update({ status }).eq("id", id);
  if (error) throw error;
}
