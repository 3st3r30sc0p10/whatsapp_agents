CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  slug TEXT UNIQUE NOT NULL,
  business_name TEXT NOT NULL,
  whatsapp_number TEXT,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  config JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  contact_phone TEXT NOT NULL,
  contact_name TEXT,
  status TEXT DEFAULT 'open',
  last_user_message_at TIMESTAMPTZ,
  booking_state JSONB DEFAULT NULL,
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(tenant_id, contact_phone)
);

CREATE TABLE messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
  wamid TEXT UNIQUE,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE bookings (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
  conversation_id UUID REFERENCES conversations(id),
  contact_phone TEXT NOT NULL,
  contact_name TEXT,
  service TEXT NOT NULL,
  booking_date DATE NOT NULL,
  booking_time TIME NOT NULL,
  status TEXT DEFAULT 'confirmed',
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE processed_messages (
  wamid TEXT PRIMARY KEY,
  processed_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE message_status_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  wamid TEXT NOT NULL,
  status TEXT NOT NULL,
  recipient_id TEXT,
  phone_number_id TEXT,
  status_at TIMESTAMPTZ,
  conversation_id TEXT,
  origin_type TEXT,
  billable BOOLEAN,
  pricing_category TEXT,
  raw JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id, created_at DESC);
CREATE INDEX idx_bookings_tenant_date ON bookings(tenant_id, booking_date);
CREATE INDEX idx_conversations_tenant ON conversations(tenant_id, last_user_message_at DESC);
CREATE INDEX idx_message_status_events_wamid ON message_status_events(wamid, created_at DESC);

INSERT INTO tenants (slug, business_name, config) VALUES ('salon-demo', 'Glamour Studio Medellín', '{
  "vertical": "salón de belleza",
  "services": [
    {"name": "Corte de cabello", "price": 35000, "duration_min": 30},
    {"name": "Tinte completo", "price": 130000, "duration_min": 90},
    {"name": "Mechas", "price": 180000, "duration_min": 120},
    {"name": "Manicure y pedicure", "price": 45000, "duration_min": 60},
    {"name": "Tratamiento capilar", "price": 75000, "duration_min": 45}
  ],
  "hours": "Martes a sábado 9am-7pm, domingos 10am-4pm, lunes cerrado",
  "address": "Calle 10 #43-20, El Poblado, Medellín",
  "phone": "+573001111111",
  "tone": "amable, descomplicada y con mucha energía",
  "escalation_phone": "+573009999991",
  "booking_noun": "cita",
  "booking_verb": "agendar",
  "custom_faq": [
    {"question": "¿Atienden sin cita?", "answer": "Sí, si hay disponibilidad, pero con cita garantizas tu turno."},
    {"question": "¿Tienen parqueadero?", "answer": "No tenemos parqueadero propio, pero hay zonas azules cerca."}
  ],
  "slots": [
    {"day": "tuesday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00"]},
    {"day": "wednesday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00"]},
    {"day": "thursday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00"]},
    {"day": "friday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00"]},
    {"day": "saturday", "times": ["09:00","10:00","11:00","14:00","15:00","16:00"]},
    {"day": "sunday", "times": ["10:00","11:00","12:00","14:00"]}
  ],
  "currency_label": "COP"
}'::jsonb);

INSERT INTO tenants (slug, business_name, config) VALUES ('dental-demo', 'Sonrisa Perfecta Bogotá', '{
  "vertical": "clínica dental",
  "services": [
    {"name": "Limpieza dental", "price": 80000, "duration_min": 45},
    {"name": "Blanqueamiento", "price": 250000, "duration_min": 60},
    {"name": "Consulta de urgencia", "price": 60000, "duration_min": 30},
    {"name": "Ortodoncia consulta inicial", "price": 50000, "duration_min": 30},
    {"name": "Extracción simple", "price": 90000, "duration_min": 30}
  ],
  "hours": "Lunes a viernes 7am-6pm, sábados 8am-1pm",
  "address": "Calle 72 #10-34, Chapinero, Bogotá",
  "phone": "+573002222222",
  "tone": "cálida, profesional y confiable",
  "escalation_phone": "+573009999992",
  "booking_noun": "cita",
  "booking_verb": "agendar",
  "custom_faq": [
    {"question": "¿Tienen odontólogo de urgencias?", "answer": "Sí, atendemos urgencias de lunes a viernes hasta las 6pm."},
    {"question": "¿Aceptan seguros médicos?", "answer": "Trabajamos con Sura, Colsanitas y Compensar. Para otras aseguradoras, consúltanos."}
  ],
  "slots": [
    {"day": "monday", "times": ["07:00","08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00"]},
    {"day": "tuesday", "times": ["07:00","08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00"]},
    {"day": "wednesday", "times": ["07:00","08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00"]},
    {"day": "thursday", "times": ["07:00","08:00","09:00","10:00","11:00","14:00","15:00","16:00","17:00"]},
    {"day": "friday", "times": ["07:00","08:00","09:00","10:00","11:00","14:00","15:00"]},
    {"day": "saturday", "times": ["08:00","09:00","10:00","11:00"]}
  ],
  "currency_label": "COP"
}'::jsonb);

INSERT INTO tenants (slug, business_name, config) VALUES ('mecanica-demo', 'Taller AutoExpress Cali', '{
  "vertical": "mecánica automotriz",
  "services": [
    {"name": "Cambio de aceite", "price": 85000, "duration_min": 30},
    {"name": "Revisión frenos", "price": 60000, "duration_min": 45},
    {"name": "Diagnóstico electrónico", "price": 50000, "duration_min": 60},
    {"name": "Cambio de llantas (4 unidades)", "price": 40000, "duration_min": 60},
    {"name": "Revisión previa viaje", "price": 70000, "duration_min": 60}
  ],
  "hours": "Lunes a viernes 7:30am-6pm, sábados 8am-2pm",
  "address": "Calle 25N #2-45, Granada, Cali",
  "phone": "+573003333333",
  "tone": "directa, técnica y confiable",
  "escalation_phone": "+573009999993",
  "booking_noun": "turno",
  "booking_verb": "reservar",
  "custom_faq": [
    {"question": "¿Trabajan con todas las marcas?", "answer": "Sí, trabajamos con todas las marcas de carros y algunas motos."},
    {"question": "¿Dan garantía?", "answer": "Sí, todos nuestros servicios tienen garantía de 30 días o 1.000 km."}
  ],
  "slots": [
    {"day": "monday", "times": ["07:30","09:00","10:30","14:00","15:30"]},
    {"day": "tuesday", "times": ["07:30","09:00","10:30","14:00","15:30"]},
    {"day": "wednesday", "times": ["07:30","09:00","10:30","14:00","15:30"]},
    {"day": "thursday", "times": ["07:30","09:00","10:30","14:00","15:30"]},
    {"day": "friday", "times": ["07:30","09:00","10:30","14:00","15:30"]},
    {"day": "saturday", "times": ["08:00","09:30","11:00"]}
  ],
  "currency_label": "COP"
}'::jsonb);

INSERT INTO tenants (slug, business_name, config) VALUES ('psicologia-demo', 'Centro Mente Clara Bogotá', '{
  "vertical": "consultorio de psicología",
  "services": [
    {"name": "Sesión individual adultos", "price": 120000, "duration_min": 50},
    {"name": "Sesión de pareja", "price": 160000, "duration_min": 60},
    {"name": "Sesión niños y adolescentes", "price": 120000, "duration_min": 50},
    {"name": "Primera consulta de valoración", "price": 80000, "duration_min": 60}
  ],
  "hours": "Lunes a viernes 8am-7pm, sábados 9am-1pm",
  "address": "Carrera 11 #93-42, Oficina 305, Chicó, Bogotá",
  "phone": "+573004444444",
  "tone": "empática, cálida y discreta",
  "escalation_phone": "+573009999994",
  "booking_noun": "sesión",
  "booking_verb": "programar",
  "custom_faq": [
    {"question": "¿Las sesiones son presenciales o virtuales?", "answer": "Ofrecemos ambas modalidades. Puedes elegir la que prefieras al agendar."},
    {"question": "¿Manejan confidencialidad?", "answer": "Absolutamente. Toda la información es completamente confidencial bajo el secreto profesional."}
  ],
  "slots": [
    {"day": "monday", "times": ["08:00","09:00","10:00","11:00","15:00","16:00","17:00","18:00"]},
    {"day": "tuesday", "times": ["08:00","09:00","10:00","11:00","15:00","16:00","17:00","18:00"]},
    {"day": "wednesday", "times": ["08:00","09:00","10:00","11:00","15:00","16:00","17:00","18:00"]},
    {"day": "thursday", "times": ["08:00","09:00","10:00","11:00","15:00","16:00","17:00","18:00"]},
    {"day": "friday", "times": ["08:00","09:00","10:00","11:00","15:00","16:00"]},
    {"day": "saturday", "times": ["09:00","10:00","11:00"]}
  ],
  "currency_label": "COP"
}'::jsonb);

INSERT INTO tenants (slug, business_name, config) VALUES ('barberia-demo', 'La Barbería del Barrio Laureles', '{
  "vertical": "barbería",
  "services": [
    {"name": "Corte clásico", "price": 25000, "duration_min": 30},
    {"name": "Corte + barba", "price": 40000, "duration_min": 45},
    {"name": "Arreglo de barba", "price": 20000, "duration_min": 20},
    {"name": "Corte con diseño", "price": 35000, "duration_min": 40},
    {"name": "Afeitado clásico con navaja", "price": 30000, "duration_min": 30}
  ],
  "hours": "Lunes a sábado 9am-8pm, domingos 10am-3pm",
  "address": "Carrera 76 #33-12, Laureles, Medellín",
  "phone": "+573005555555",
  "tone": "relajada, amigable y de barrio",
  "escalation_phone": "+573009999995",
  "booking_noun": "cita",
  "booking_verb": "agendar",
  "custom_faq": [
    {"question": "¿Tienen wifi?", "answer": "Sí parce, tenemos wifi gratis mientras esperas."},
    {"question": "¿Aceptan niños?", "answer": "Claro, cortamos a niños de todas las edades."}
  ],
  "slots": [
    {"day": "monday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00","19:00"]},
    {"day": "tuesday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00","19:00"]},
    {"day": "wednesday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00","19:00"]},
    {"day": "thursday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00","19:00"]},
    {"day": "friday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00","19:00"]},
    {"day": "saturday", "times": ["09:00","10:00","11:00","12:00","14:00","15:00","16:00","17:00","18:00","19:00"]},
    {"day": "sunday", "times": ["10:00","11:00","12:00","14:00"]}
  ],
  "currency_label": "COP"
}'::jsonb);
