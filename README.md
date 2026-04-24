# WhatsApp Agent SaaS — Pymes Colombianas

Plataforma multi-tenant para desplegar agentes de WhatsApp con IA para pequeñas y medianas empresas colombianas. Un solo operador puede gestionar múltiples clientes (negocios) desde un panel administrativo, con memoria persistente por cliente final.

---

## Stack tecnológico

| Capa | Tecnología |
|---|---|
| Backend | Python 3.11 + FastAPI |
| Agente IA | Claude Managed Agents (Anthropic; `anthropic` SDK ≥0.90, p. ej. 0.94.x) |
| WhatsApp | Kapso (API oficial de Meta) |
| Memoria | Mem0 |
| Base de datos | Supabase (PostgreSQL) |
| Deploy | Railway |

---

## Prerrequisitos

### Cuentas necesarias (todas con tier gratuito para empezar)

1. **Anthropic Console** → https://console.anthropic.com  
   Crea una API key. Necesitas acceso a `managed-agents-2026-04-01` beta.

2. **Kapso** → https://kapso.ai  
   Crea una cuenta, obtén tu `KAPSO_API_KEY` y el `phone_number_id` de tu número de WhatsApp.

3. **Mem0** → https://app.mem0.ai  
   Crea una cuenta, obtén tu `MEM0_API_KEY`.

4. **Supabase** → https://supabase.com  
   Crea un proyecto nuevo. Guarda la `SUPABASE_URL` y la `service_role` key.

5. **Railway** → https://railway.app  
   Conecta tu repositorio GitHub.

---

## Instalación local

### 1. Clonar y configurar entorno

```bash
git clone https://github.com/tu-usuario/whatsapp-agent-saas.git
cd whatsapp-agent-saas

python -m venv venv
source venv/bin/activate        # macOS/Linux
# venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Edita .env con tus credenciales reales
```

```env
ANTHROPIC_API_KEY=sk-ant-...
KAPSO_API_KEY=kap_live_...
KAPSO_WEBHOOK_SECRET=secreto_de_32_caracteres_minimo
MEM0_API_KEY=m0-...
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
APP_ENV=development
```

### Checklist de seguridad para `.env`

- Usa `.env.example` solo con placeholders (nunca claves reales).
- Guarda claves reales unicamente en `.env` local o variables del proveedor (Railway, Vercel, etc.).
- No subas `.env` a git; verifica que este incluido en `.gitignore`.
- Antes de hacer push, corre `git diff` y confirma que no haya secretos.
- Si una clave se filtra, rotala en el proveedor y limpia el historial de git.

### 3. Crear schema en Supabase

En el Supabase Dashboard → SQL Editor, ejecuta el contenido completo de `sql/schema.sql`.

O desde la CLI de Supabase:
```bash
npx supabase db push --db-url "postgresql://..."
```

### 4. Levantar el servidor local

```bash
uvicorn app.main:app --reload --port 8000
```

Verifica: `http://localhost:8000/health` debe retornar `{"status": "ok"}`.

---

## Onboarding de un cliente pyme

Cada negocio que contratas como cliente es un **tenant** en el sistema. Para agregar uno:

```bash
python scripts/create_business.py \
  --name "Restaurante La Cazuela" \
  --slug "restaurante-cazuela" \
  --phone-number-id "647015955153740" \
  --context "Restaurante típico colombiano en El Poblado, Medellín. \
Menú del día: bandeja paisa $18.000, sancocho $15.000, mondongo $16.000. \
Domicilios a Envigado, El Poblado y Laureles. \
Horario: lunes a domingo 11am–9pm. \
Pedidos con mínimo 30 minutos de anticipación. \
WhatsApp de pagos: Nequi 310-xxx-xxxx."
```

El script:
1. Crea el registro del negocio en Supabase
2. Crea el agente en Claude Managed Agents (una vez, ID guardado en DB)
3. Crea el environment en Claude (una vez, ID guardado en DB)
4. Registra el webhook en Kapso para ese número

### Ejemplos de contexto por tipo de negocio

**Consultorio médico:**
```
Consultorio Dra. Martínez - Dermatología y Estética. 
Citas disponibles: lunes a viernes 8am–5pm, sábados 9am–1pm. 
Duración de consulta: 30 minutos. Precio consulta general: $120.000 COP. 
Para agendar, necesito: nombre completo, cédula, fecha y hora preferida. 
Urgencias: llamar al 310-xxx-xxxx.
```

**Tienda de ropa:**
```
Boutique Estilo CO - Moda femenina contemporánea. Bogotá, Chapinero.
Tallas disponibles: XS, S, M, L, XL. 
Envíos nacionales $12.000 (2-3 días hábiles). Envío gratis compras +$200.000.
Cambios y devoluciones: hasta 15 días calendario con etiqueta y factura.
Métodos de pago: Nequi, Daviplata, transferencia bancaria, tarjeta (en tienda).
Para ver catálogo: @estilocobogota en Instagram.
```

---

## Registro del webhook (si necesitas hacerlo manualmente)

Si el webhook no se registró automáticamente al crear el negocio:

```bash
python scripts/setup_kapso_webhook.py \
  --phone-number-id "647015955153740" \
  --webhook-url "https://tu-app.railway.app/webhook/whatsapp"
```

Para desarrollo local con ngrok:
```bash
ngrok http 8000
# Copia la URL https://xxxx.ngrok.io
python scripts/setup_kapso_webhook.py \
  --phone-number-id "647015955153740" \
  --webhook-url "https://xxxx.ngrok.io/webhook/whatsapp"
```

---

## Deploy en Railway

### Primera vez

```bash
# Instala Railway CLI
npm install -g @railway/cli

# Login
railway login

# Inicializa proyecto
railway init

# Despliega
railway up
```

### Variables de entorno en Railway

En el Dashboard de Railway → tu proyecto → Variables, agrega todas las variables del archivo `.env` (sin el `.env.example`, una por una).

### Auto-deploy

Railway se conecta a GitHub y hace deploy automático en cada push a `main`. Configura la rama en el Dashboard.

La URL de producción será algo como: `https://whatsapp-agent-saas.railway.app`

### Verificar el deploy

```bash
curl https://tu-app.railway.app/health
# → {"status": "ok", "env": "production"}
```

---

## API de administración

Base URL: `https://tu-app.railway.app/admin`

> Nota: En MVP no hay autenticación en el admin. Para producción, agrega un header `X-Admin-Key`.

### Negocios

```bash
# Listar todos los negocios
GET /admin/businesses

# Crear nuevo negocio
POST /admin/businesses
{
  "name": "Nombre del Negocio",
  "slug": "nombre-negocio",
  "phone_number_id": "647015955153740",
  "business_context": "...",
  "plan": "estandar"
}

# Ver detalle de un negocio
GET /admin/businesses/{business_id}

# Actualizar contexto o plan
PATCH /admin/businesses/{business_id}
{
  "business_context": "Nuevo contexto...",
  "plan": "pro"
}
```

### Logs y uso

```bash
# Últimos 100 mensajes de un negocio
GET /admin/businesses/{business_id}/logs

# Uso del mes actual
GET /admin/businesses/{business_id}/usage
# → {"month": "2026-04", "message_count": 234, "limit": 500, "percentage": 46.8}
```

### Memoria de clientes

```bash
# Ver memorias de un cliente específico
GET /admin/businesses/{business_id}/memories/573001234567

# Borrar todas las memorias de un cliente (útil si el cliente quiere privacidad)
DELETE /admin/businesses/{business_id}/memories/573001234567
```

---

## Tests

```bash
# Correr todos los tests
pytest tests/ -v

# Con coverage report
pytest tests/ -v --cov=app --cov-report=term-missing

# Solo un módulo
pytest tests/test_webhook.py -v
```

---

## Arquitectura del flujo de mensajes

```
1. Cliente escribe en WhatsApp
   ↓
2. Meta → Kapso → POST /webhook/whatsapp (tu servidor)
   ↓
3. Verificación HMAC-SHA256 (firma del webhook)
   ↓
4. Lookup: phone_number_id → business_id (Supabase)
   ↓
5. Mem0: buscar memorias relevantes del cliente
   ↓
6. Claude Managed Agents:
   - Busca sesión existente (Supabase) o crea nueva
   - Envía: [memorias] + [mensaje del cliente]
   - Recibe respuesta
   ↓
7. Kapso: enviar respuesta a WhatsApp del cliente
   ↓
8. Mem0: guardar conversación (para próximas interacciones)
   ↓
9. Supabase: log del mensaje + incrementar contador de uso
```

---

## Escalado humano

Cuando Claude detecta que el cliente quiere hablar con una persona, responde con el tag `[ESCALATE]`. Tu servidor detecta ese tag y puede:

- Enviar una notificación al dueño del negocio (Telegram, email, SMS)
- Abrir un ticket en el CRM del negocio
- Activar la bandeja de entrada manual de Kapso

Configura la acción de escalado en `app/core/orchestrator.py` → método `_handle_escalation()`.

---

## Planes y precios sugeridos

| Plan | Precio COP/mes | Mensajes/mes | WhatsApp números |
|---|---|---|---|
| Básico | $150.000 | 500 | 1 |
| Estándar | $350.000 | ilimitados | 1 |
| Pro | $650.000 | ilimitados | 3 |

### Costo de operación estimado por cliente

| Concepto | Costo/mes |
|---|---|
| Claude API (tokens) | ~$8–12 USD |
| Managed Agents runtime | ~$4–5 USD |
| Kapso (prorrateado) | ~$5–8 USD |
| Railway (compartido) | ~$1 USD |
| **Total** | **~$18–26 USD** |

Margen bruto con plan Estándar a $87 USD: **~70–80%**

---

## Monitoreo

Railway provee logs en tiempo real desde el Dashboard. Para monitoreo adicional:

```bash
# Ver logs en tiempo real
railway logs --tail

# Los logs son JSON estructurado en producción:
# {"event": "message_processed", "business_id": "...", "duration_ms": 1240, ...}
```

---

## Solución de problemas frecuentes

**El webhook devuelve 401:**  
Verifica que `KAPSO_WEBHOOK_SECRET` en tu `.env` coincide exactamente con el secret configurado al registrar el webhook en Kapso.

**Claude no responde / timeout:**  
Revisa que `ANTHROPIC_API_KEY` tiene acceso a la beta `managed-agents-2026-04-01`. Solicita acceso en https://claude.com/form/claude-managed-agents

**El agente no recuerda al cliente:**  
Mem0 tarda ~100ms adicionales. Verifica en logs que aparece `"memory_results": N` con N > 0. Si N = 0 siempre, revisa el `MEM0_API_KEY`.

**Mensajes duplicados:**  
Kapso puede reenviar webhooks. El sistema debe ser idempotente usando el `whatsapp_message_id` como clave de deduplicación en la tabla `message_logs`.

---

## Estructura de costos iniciales

| Item | Costo |
|---|---|
| Kapso (primer mes) | $0 (trial) |
| Mem0 (primeros 10k ops) | $0 |
| Anthropic API | Pay-per-use (~$0.003/1k tokens) |
| Railway Hobby | $5 USD/mes |
| Supabase Free tier | $0 |
| **Total mes 1** | **~$5–20 USD** |

Con el primer cliente pagando $87 USD/mes = rentable desde el día 1.

---

## Licencia

MIT — libre para uso comercial.

---

*Construido con Claude Code · Stack: FastAPI + Anthropic Managed Agents + Kapso + Mem0 + Supabase + Railway*
