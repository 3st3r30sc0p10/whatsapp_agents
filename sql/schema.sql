-- Tenant businesses (your SME clients)
CREATE TABLE businesses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    phone_number_id TEXT UNIQUE NOT NULL,
    business_context TEXT NOT NULL,
    agent_id TEXT,
    environment_id TEXT,
    webhook_registered BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    plan TEXT DEFAULT 'basico' CHECK (plan IN ('basico', 'estandar', 'pro')),
    monthly_message_limit INTEGER DEFAULT 500,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    client_phone TEXT NOT NULL,
    business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
    session_id TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    last_message_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(client_phone, business_id)
);

CREATE TABLE message_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    client_phone TEXT NOT NULL,
    direction TEXT NOT NULL CHECK (direction IN ('inbound', 'outbound')),
    content TEXT NOT NULL,
    whatsapp_message_id TEXT,
    processed_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE usage_counters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    business_id UUID NOT NULL REFERENCES businesses(id),
    month_year TEXT NOT NULL,
    message_count INTEGER DEFAULT 0,
    UNIQUE(business_id, month_year)
);

CREATE INDEX idx_agent_sessions_lookup ON agent_sessions(client_phone, business_id);
CREATE INDEX idx_message_logs_business ON message_logs(business_id, processed_at DESC);
CREATE INDEX idx_usage_business_month ON usage_counters(business_id, month_year);

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER businesses_updated_at
    BEFORE UPDATE ON businesses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();
