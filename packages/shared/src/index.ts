export type IntentType =
  | "greeting"
  | "faq_price"
  | "faq_hours"
  | "faq_location"
  | "faq_services"
  | "faq_custom"
  | "booking_request"
  | "escalate"
  | "fallback";

export type BookingNoun =
  | "cita"
  | "turno"
  | "sesión"
  | "reserva"
  | "consulta";

export type BookingVerb =
  | "agendar"
  | "reservar"
  | "programar"
  | "solicitar";

export type ConversationStatus =
  | "open"
  | "escalated"
  | "resolved"
  | "window_expired";

export type BookingStatus = "confirmed" | "cancelled" | "completed";

export type Weekday =
  | "monday"
  | "tuesday"
  | "wednesday"
  | "thursday"
  | "friday"
  | "saturday"
  | "sunday";

export type TenantConfigData = {
  vertical: string;
  services: Array<{ name: string; price: number; duration_min: number }>;
  hours: string;
  address: string;
  phone: string;
  tone: string;
  escalation_phone: string;
  booking_noun: BookingNoun;
  booking_verb: BookingVerb;
  custom_faq: Array<{ question: string; answer: string }>;
  slots: Array<{ day: Weekday; times: string[] }>;
  currency_label: string;
};

export type BookingState = {
  step: "ask_service" | "ask_date" | "ask_time" | "confirm";
  selected_service: string | null;
  selected_date: string | null;
  selected_time: string | null;
};

export type Tenant = {
  id: string;
  slug: string;
  business_name: string;
  whatsapp_number: string | null;
  active: boolean;
  created_at: string;
  config: TenantConfigData;
};

export type Conversation = {
  id: string;
  tenant_id: string;
  contact_phone: string;
  contact_name: string | null;
  status: ConversationStatus;
  last_user_message_at: string | null;
  booking_state: BookingState | null;
  created_at: string;
};

export type Message = {
  id: string;
  conversation_id: string;
  wamid: string | null;
  role: "user" | "assistant";
  content: string;
  created_at: string;
};

export type Booking = {
  id: string;
  tenant_id: string;
  conversation_id: string | null;
  contact_phone: string;
  contact_name: string | null;
  service: string;
  booking_date: string;
  booking_time: string;
  status: BookingStatus;
  created_at: string;
};
