import json
import uuid
import os

OUT_DIR = "enterprise-ai-agent-platform/n8n"

def uid():
    return str(uuid.uuid4())

def make_wf(name, wf_id=None, tags=None):
    return {
        "name": name,
        "id": wf_id or uid(),
        "nodes": [],
        "connections": {},
        "settings": {"executionOrder": "v1"},
        "staticData": None,
        "tags": tags or [],
        "pinData": {},
        "meta": {"templateCredsSetupCompleted": False, "instanceId": uid()},
    }

def add_node(wf, node):
    wf["nodes"].append(node)
    return node

def connect(wf, src, dst, branch=0):
    if src not in wf["connections"]:
        wf["connections"][src] = {"main": []}
    while len(wf["connections"][src]["main"]) <= branch:
        wf["connections"][src]["main"].append([])
    wf["connections"][src]["main"][branch].append({"node": dst, "type": "main", "index": 0})

def save_wf(wf, filename):
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w") as f:
        json.dump(wf, f, indent=2)
    print(f"Saved {path}")

def set_node(name, x, y, fields):
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.set",
        "typeVersion": 3.4,
        "position": [x, y],
        "parameters": {
            "assignments": {
                "assignments": [
                    {"id": uid(), "name": k, "value": v, "type": "string"}
                    for k, v in fields.items()
                ]
            },
            "options": {}
        }
    }

def code_node(name, x, y, code):
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.code",
        "typeVersion": 2,
        "position": [x, y],
        "parameters": {"jsCode": code}
    }

def if_node(name, x, y, left, right, op="equals"):
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.if",
        "typeVersion": 2.2,
        "position": [x, y],
        "parameters": {
            "conditions": {
                "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "strict", "version": 2},
                "conditions": [
                    {"id": uid(), "leftValue": left, "rightValue": right, "operator": {"type": "string", "operation": op}}
                ],
                "combinator": "and"
            },
            "options": {}
        }
    }

def http_node(name, x, y, method, url, body=None, headers=None):
    p = {"method": method, "url": url, "options": {}}
    if headers:
        p["sendHeaders"] = True
        p["headerParameters"] = {"parameters": [{"name": k, "value": v} for k, v in headers.items()]}
    if body is not None:
        p["sendBody"] = True
        p["specifyBody"] = "json"
        p["jsonBody"] = body
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.httpRequest",
        "typeVersion": 4.2,
        "position": [x, y],
        "parameters": p
    }

def openai_node(name, x, y, system, user, model="gpt-4o-mini"):
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.openAi",
        "typeVersion": 1,
        "position": [x, y],
        "parameters": {
            "resource": "chat",
            "operation": "create",
            "model": model,
            "messages": {
                "values": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user}
                ]
            },
            "options": {"temperature": 0.2, "maxTokens": 1200}
        },
        "credentials": {"openAiApi": {"id": "OPENAI_CREDENTIAL", "name": "OpenAI API"}}
    }

def webhook_node(name, x, y, path, method="POST", response_mode="responseNode"):
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.webhook",
        "typeVersion": 1.1,
        "position": [x, y],
        "webhookId": uid(),
        "parameters": {"httpMethod": method, "path": path, "responseMode": response_mode, "options": {}}
    }

def respond_node(name, x, y, mode="allIncomingItems"):
    p = {"respondWith": mode, "options": {}}
    if mode != "allIncomingItems":
        p["responseBody"] = ""
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.respondToWebhook",
        "typeVersion": 1.1,
        "position": [x, y],
        "parameters": p
    }

def sticky_note(name, x, y, content, width=240, height=80):
    return {
        "id": uid(),
        "name": name,
        "type": "n8n-nodes-base.stickyNote",
        "typeVersion": 1,
        "position": [x, y],
        "parameters": {"width": width, "height": height, "content": content}
    }

# ---------------------------------------------------------------------------
# Master Orchestrator
# ---------------------------------------------------------------------------
MASTER_CLASSIFICATION_PROMPT = """You are the Master AI Agent (Orchestrator) for an enterprise AI automation platform.
You receive natural language requests from employees.
Your job is to understand the request, select the appropriate specialized agent(s), and determine risk and approval requirements.

Available specialized agents:
- HR Agent: leave requests, employee information lookup, HR document generation, attendance inquiries, policy lookup, HR report generation.
- IT Support Agent: ticket creation, ticket categorization, user account requests, password reset workflows, software access requests, hardware asset tracking, IT reporting.
- Finance Agent: expense request processing, budget inquiries, invoice management, financial reporting, payment tracking, financial analytics.
- Procurement Agent: purchase request creation, vendor information retrieval, procurement workflow management, purchase order tracking, procurement reporting.
- Email Agent: read emails, categorize emails, extract tasks, generate draft responses, send emails, route emails, follow-up tracking.
- Database Agent: query databases, create records, update records, delete records, generate database reports, validate data integrity.
- Reporting Agent: daily, weekly, monthly reports, KPI reports, department performance, executive dashboards, AI-generated recommendations.
- Notification Agent: send notifications, Teams notifications, email alerts, workflow reminders, approval reminders, escalation alerts.
- Knowledge Agent: company policy search, internal documentation search, SOP retrieval, FAQ answering, knowledge base management.
- Security & Compliance Agent: monitor security events, audit user activities, compliance validation, access monitoring, risk detection, security reporting.

Rules:
- The following always require human approval and should be flagged as high-risk: employee termination, salary modifications, financial approvals, budget approvals, payment authorizations, procurement approvals above threshold, vendor onboarding approval, legal/contract approvals, high-risk operational decisions.
- The AI may recommend but must never make final decisions on these.
- If the request spans multiple departments, select multiple agents.
- Return ONLY a valid JSON object with these exact keys:
  intent_summary (string),
  selected_agents (array of agent names),
  risk_level (one of low, medium, high),
  human_approval_required (boolean),
  parameters (object with extracted parameters),
  reasoning (string)."""

MASTER_SYNTHESIS_PROMPT = "You are the Master AI Agent. Synthesize a clear, helpful response for the employee based on the results from specialized agents. Include status, any pending approvals, and next steps. Be concise and professional."

def build_master():
    w = make_wf("Master AI Agent - Orchestrator", tags=["master", "orchestrator"])
    n = []
    n.append(webhook_node("Receive Employee Request", 100, 300, "orchestrator/request"))
    n.append(set_node("Extract Request", 300, 300, {
        "request_id": "={{ $json.body.request_id }}",
        "user": "={{ $json.body.user }}",
        "role": "={{ $json.body.role }}",
        "message": "={{ $json.body.message }}",
        "session_id": "={{ $json.body.session_id }}",
    }))
    n.append(code_node("Validate API Key", 500, 300, """
const apiKey = $json.headers?.['x-api-key'] || $json.body?.api_key;
const expected = $env.ORCHESTRATOR_API_KEY;
if (apiKey !== expected) {
  return [{ json: { valid: false, error: 'Invalid API key' } }];
}
return [{ json: {
  valid: true,
  request_id: $json.body.request_id,
  user: $json.body.user,
  role: $json.body.role,
  message: $json.body.message,
  session_id: $json.body.session_id
} }];
"""))
    n.append(if_node("Auth Valid?", 700, 300, "={{ $json.valid }}", "true"))
    n.append(set_node("Set 401", 700, 520, {"status": "error", "message": "Unauthorized: invalid API key"}))
    n.append(respond_node("Respond 401", 900, 520))
    n.append(code_node("Prepare Audit Request", 900, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  request_id: ctx.request_id,
  user: ctx.user,
  event_type: "request_received",
  payload: { message: ctx.message },
  risk_level: "pending",
  metadata: { request_id: ctx.request_id, user: ctx.user, role: ctx.role, message: ctx.message, session_id: ctx.session_id }
});
return [{ json: { body } }];
"""))
    n.append(http_node("Audit Request to Security Agent", 1100, 300, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/security", body="={{ $json.body }}"))
    n.append(code_node("Recover Context After Audit", 1300, 300, """
const input = $input.first().json;
const metadata = input.metadata || {};
return [{ json: metadata }];
"""))
    n.append(code_node("Prepare Memory Request", 1500, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  operation: "memory_get",
  session_id: ctx.session_id,
  user_id: ctx.user,
  metadata: { request_id: ctx.request_id, user: ctx.user, role: ctx.role, message: ctx.message, session_id: ctx.session_id }
});
return [{ json: { ...ctx, body } }];
"""))
    n.append(http_node("Fetch Memory", 1700, 300, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/database", body="={{ $json.body }}"))
    n.append(code_node("Merge Memory & Context", 1900, 300, """
const input = $input.first().json;
const metadata = input.metadata || {};
const memory = input.memory || [];
return [{ json: { ...metadata, memory } }];
"""))
    n.append(set_node("Prepare Classification Prompt", 2100, 300, {
        "prompt": "={{ `Employee request: ${$json.message}\n\nConversation memory: ${JSON.stringify($json.memory)}\n\nAnalyze intent, select the appropriate specialized agent(s), and determine risk level and whether human approval is required.` }}"
    }))
    n.append(openai_node("Classify Intent & Select Agents", 2300, 300, MASTER_CLASSIFICATION_PROMPT, "={{ $json.prompt }}"))
    n.append(code_node("Parse Classification", 2500, 300, """
const raw = $json.message?.content || $json.choices?.[0]?.message?.content || $json;
let parsed = {};
try {
  parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
} catch (e) {
  parsed = {
    intent_summary: 'unknown',
    selected_agents: ['knowledge'],
    risk_level: 'low',
    human_approval_required: false,
    parameters: {},
    reasoning: 'Failed to parse LLM output; routing to Knowledge Agent.'
  };
}
const ctx = $input.first().json;
return [{ json: {
  ...ctx,
  ...parsed,
  requires_approval: parsed.human_approval_required ? 'true' : 'false'
}}];
"""))
    n.append(if_node("Requires Manager Approval?", 2700, 300, "={{ $json.requires_approval }}", "true"))
    n.append(set_node("Escalation Response", 2700, 520, {
        "status": "pending_approval",
        "response": "={{ `Your request has been escalated to a manager for approval. Risk level: ${$json.risk_level}. Reasoning: ${$json.reasoning}` }}"
    }))
    n.append(http_node("Notify Manager", 2900, 520, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/notification", body='={{ JSON.stringify({ request_id: $json.request_id, user: $json.user, role: $json.role, platform: "teams", recipients: ["manager@example.com"], subject: "Approval Required", message: $json.response, metadata: { request_id: $json.request_id, user: $json.user, role: $json.role, message: $json.message } }) }}'))
    n.append(respond_node("Respond Pending Approval", 3100, 520))
    n.append(code_node("Prepare Coordinator Request", 2900, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  selected_agents: ctx.selected_agents,
  payload: { original_message: ctx.message, parameters: ctx.parameters },
  metadata: { request_id: ctx.request_id, user: ctx.user, role: ctx.role, session_id: ctx.session_id, message: ctx.message }
});
return [{ json: { body } }];
"""))
    n.append(http_node("Call Multi-Agent Coordinator", 3100, 300, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/coordinator", body="={{ $json.body }}"))
    n.append(code_node("Parse Coordinator Results", 3300, 300, """
const input = $input.first().json;
const metadata = input.metadata || {};
const results = input.results || {};
return [{ json: { ...metadata, results } }];
"""))
    n.append(set_node("Prepare Synthesis Prompt", 3500, 300, {
        "prompt": "={{ `Original employee request: ${$json.message}\n\nResults from specialized agents: ${JSON.stringify($json.results)}\n\nSynthesize a clear, helpful response. Include status, any pending approvals, and next steps.` }}"
    }))
    n.append(openai_node("Synthesize Final Response", 3700, 300, MASTER_SYNTHESIS_PROMPT, "={{ $json.prompt }}"))
    n.append(code_node("Parse Final Response", 3900, 300, """
const raw = $json.message?.content || $json.choices?.[0]?.message?.content || $json;
const ctx = $input.first().json;
return [{ json: { ...ctx, response: raw } }];
"""))
    n.append(code_node("Prepare Save Memory", 4100, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  operation: "memory_save",
  session_id: ctx.session_id,
  user_id: ctx.user,
  message: ctx.message,
  response: ctx.response,
  metadata: { request_id: ctx.request_id, user: ctx.user, role: ctx.role, session_id: ctx.session_id }
});
return [{ json: { ...ctx, body } }];
"""))
    n.append(http_node("Save Memory", 4300, 300, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/database", body="={{ $json.body }}"))
    n.append(code_node("Prepare Final Audit", 4500, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  request_id: ctx.request_id,
  user: ctx.user,
  event_type: "final_response",
  payload: { response: ctx.response },
  risk_level: "low",
  metadata: { request_id: ctx.request_id, user: ctx.user, role: ctx.role, message: ctx.message, session_id: ctx.session_id }
});
return [{ json: { ...ctx, body } }];
"""))
    n.append(http_node("Audit Final Response", 4700, 300, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/security", body="={{ $json.body }}"))
    n.append(code_node("Final Response", 4900, 300, """
const ctx = $input.first().json;
return [{ json: { request_id: ctx.request_id, status: "success", response: ctx.response } }];
"""))
    n.append(respond_node("Respond to Employee", 5100, 300))

    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"], 1)  # false
    connect(w, n[4]["name"], n[5]["name"])
    connect(w, n[3]["name"], n[6]["name"], 0)  # true
    connect(w, n[6]["name"], n[7]["name"])
    connect(w, n[7]["name"], n[8]["name"])
    connect(w, n[8]["name"], n[9]["name"])
    connect(w, n[9]["name"], n[10]["name"])
    connect(w, n[10]["name"], n[11]["name"])
    connect(w, n[11]["name"], n[12]["name"])
    connect(w, n[12]["name"], n[13]["name"])
    connect(w, n[13]["name"], n[14]["name"])
    connect(w, n[14]["name"], n[15]["name"])
    connect(w, n[15]["name"], n[16]["name"], 0)  # true -> escalation branch
    connect(w, n[16]["name"], n[17]["name"])       # escalation -> notify manager
    connect(w, n[17]["name"], n[18]["name"])       # notify -> respond pending
    connect(w, n[15]["name"], n[19]["name"], 1)  # false -> coordinator branch
    connect(w, n[19]["name"], n[20]["name"])
    connect(w, n[20]["name"], n[21]["name"])
    connect(w, n[22]["name"], n[23]["name"])
    connect(w, n[23]["name"], n[24]["name"])
    connect(w, n[24]["name"], n[25]["name"])
    connect(w, n[25]["name"], n[26]["name"])
    connect(w, n[26]["name"], n[27]["name"])
    connect(w, n[27]["name"], n[28]["name"])
    connect(w, n[28]["name"], n[29]["name"])
    connect(w, n[29]["name"], n[30]["name"])
    save_wf(w, "master_orchestrator.json")

# ---------------------------------------------------------------------------
# Multi-Agent Coordinator
# ---------------------------------------------------------------------------
def build_coordinator():
    w = make_wf("Multi-Agent Coordinator", tags=["coordinator"])
    n = []
    n.append(webhook_node("Coordinator Trigger", 100, 300, "agent/coordinator"))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: {
  request_id: body.metadata?.request_id,
  user: body.metadata?.user,
  role: body.metadata?.role,
  session_id: body.metadata?.session_id,
  selected_agents: body.selected_agents || [],
  payload: body.payload || {},
  metadata: body.metadata || {}
}}];
"""))
    n.append(code_node("Build Agent Items", 500, 300, """
const ctx = $input.first().json;
const agents = Array.isArray(ctx.selected_agents) ? ctx.selected_agents : [];
const items = agents.map(agent => ({
  json: {
    agent,
    request_id: ctx.request_id,
    user: ctx.user,
    role: ctx.role,
    session_id: ctx.session_id,
    payload: ctx.payload,
    metadata: ctx.metadata
  }
}));
return items.length ? items : [{ json: { agent: "knowledge", request_id: ctx.request_id, user: ctx.user, role: ctx.role, session_id: ctx.session_id, payload: ctx.payload, metadata: ctx.metadata } }];
"""))
    n.append(http_node("Call Agent", 700, 300, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/{{ $json.agent }}", body='={{ JSON.stringify({ request_id: $json.request_id, user: $json.user, role: $json.role, session_id: $json.session_id, payload: $json.payload, metadata: $json.metadata }) }}'))
    n.append(code_node("Aggregate Results", 900, 300, """
const items = $input.all();
const results = {};
items.forEach(item => {
  const agent = item.json.agent;
  results[agent] = item.json;
});
const first = items[0]?.json || {};
return [{ json: { metadata: first.metadata || {}, results } }];
"""))
    n.append(respond_node("Return Results", 1100, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    save_wf(w, "multi_agent_coordinator.json")

# ---------------------------------------------------------------------------
# Approval Handler
# ---------------------------------------------------------------------------
def build_approval_handler():
    w = make_wf("Approval Handler", tags=["approval", "hitl"])
    n = []
    n.append(webhook_node("Approval Webhook", 100, 300, "approval/action", method="POST"))
    n.append(code_node("Extract Approval", 300, 300, """
const body = $json.body || $json;
return [{ json: {
  approval_id: body.approval_id,
  decision: body.decision,
  manager_id: body.manager_id,
  metadata: body.metadata || {}
}}];
"""))
    n.append(http_node("Resolve Approval", 500, 300, "POST", "={{ $env.BACKEND_API_URL }}/api/approval/resolve", body='={{ JSON.stringify({ approval_id: $json.approval_id, decision: $json.decision, manager_id: $json.manager_id, metadata: $json.metadata }) }}'))
    n.append(code_node("Prepare Notification", 700, 300, """
const input = $input.first().json;
const status = input.status || input.decision;
const ctx = input.metadata || {};
return [{ json: {
  request_id: ctx.request_id,
  user: ctx.user,
  role: ctx.role,
  platform: "email",
  recipients: [ctx.user || "employee@example.com"],
  subject: `Approval ${status}`,
  message: input.message || `Your approval request ${ctx.approval_id} was ${status}.`,
  metadata: ctx
}}];
"""))
    n.append(http_node("Notify Employee", 900, 300, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/notification", body='={{ JSON.stringify({ request_id: $json.request_id, user: $json.user, role: $json.role, platform: $json.platform, recipients: $json.recipients, subject: $json.subject, message: $json.message, metadata: $json.metadata }) }}'))
    n.append(code_node("Approval Result", 1100, 300, """
const ctx = $input.first().json;
return [{ json: { status: "resolved", approval_id: ctx.approval_id, decision: ctx.decision, message: ctx.message } }];
"""))
    n.append(respond_node("Respond to Manager", 1300, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    connect(w, n[5]["name"], n[6]["name"])
    save_wf(w, "approval_handler.json")

# ---------------------------------------------------------------------------
# Business Agents (HR, IT, Finance, Procurement)
# ---------------------------------------------------------------------------
BUSINESS_AGENTS = {
    "hr": {
        "name": "HR Agent",
        "capabilities": "leave requests, employee information lookup, HR document generation, attendance inquiries, policy lookup, HR report generation",
        "actions": "leave, employee_info, document, attendance, policy, report",
        "approval_actions": "leave approval, disciplinary actions, employee termination, salary modifications"
    },
    "it": {
        "name": "IT Support Agent",
        "capabilities": "ticket creation, ticket categorization, user account requests, password reset workflows, software access requests, hardware asset tracking, IT reporting",
        "actions": "ticket, account, password, software, hardware, report",
        "approval_actions": ""
    },
    "finance": {
        "name": "Finance Agent",
        "capabilities": "expense request processing, budget inquiries, invoice management, financial reporting, payment tracking, financial analytics",
        "actions": "expense, budget, invoice, report, payment, analytics",
        "approval_actions": "financial approvals, budget approvals, payment authorizations"
    },
    "procurement": {
        "name": "Procurement Agent",
        "capabilities": "purchase request creation, vendor information retrieval, procurement workflow management, purchase order tracking, procurement reporting",
        "actions": "purchase, vendor, workflow, po, report",
        "approval_actions": "purchase approvals above threshold, vendor onboarding approval"
    }
}

def build_business_agent(agent_id, cfg):
    w = make_wf(f"{cfg['name']} - Specialized Agent", tags=[agent_id, "agent"])
    path = f"agent/{agent_id}"
    system = f"""You are the {cfg['name']} for an enterprise AI automation platform.
Capabilities: {cfg['capabilities']}.
Actions that require manager approval before execution: {cfg['approval_actions'] or 'none'}.
Given the request, return ONLY a valid JSON object with these exact keys:
  action (one of: {cfg['actions']}),
  parameters (object),
  human_approval_required (boolean),
  confidence (number 0-1),
  response (string).
If the action requires approval, set human_approval_required to true."""
    n = []
    n.append(webhook_node(f"{cfg['name']} Trigger", 100, 300, path))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: {
  request_id: body.request_id,
  user: body.user,
  role: body.role,
  session_id: body.session_id,
  payload: body.payload || {},
  metadata: body.metadata || {}
}}];
"""))
    n.append(code_node("Validate Permissions", 500, 300, """
const ctx = $input.first().json;
const allowed = true; // Extend with RBAC checks against $env.ALLOWED_ROLES
return [{ json: { ...ctx, allowed: allowed ? 'true' : 'false' } }];
"""))
    n.append(if_node("Allowed?", 700, 300, "={{ $json.allowed }}", "true"))
    n.append(set_node("Set 403", 700, 520, {"status": "error", "message": "Forbidden: insufficient permissions"}))
    n.append(respond_node("Respond 403", 900, 520))
    n.append(set_node("Prepare Agent Prompt", 900, 300, {
        "prompt": "={{ `Original request: ${$json.payload?.original_message || ''}\n\nExtracted parameters: ${JSON.stringify($json.payload?.parameters || {})}\n\nDetermine the action, parameters, and whether manager approval is required.` }}"
    }))
    n.append(openai_node(f"{cfg['name']} Reasoning", 1100, 300, system, "={{ $json.prompt }}"))
    n.append(code_node("Parse Decision", 1300, 300, """
const raw = $json.message?.content || $json.choices?.[0]?.message?.content || $json;
let parsed = {};
try {
  parsed = typeof raw === 'string' ? JSON.parse(raw) : raw;
} catch (e) {
  parsed = { action: 'report', parameters: {}, human_approval_required: false, confidence: 0, response: 'Could not parse reasoning.' };
}
const ctx = $input.first().json;
return [{ json: { ...ctx, ...parsed, requires_approval: parsed.human_approval_required ? 'true' : 'false' } }];
"""))
    n.append(if_node("Approval Required?", 1500, 300, "={{ $json.requires_approval }}", "true"))
    # approval branch
    n.append(code_node("Create Approval Request", 1500, 520, """
const ctx = $input.first().json;
const body = JSON.stringify({
  request_id: ctx.request_id,
  requester_id: ctx.user,
  agent: '__AGENT_NAME__',
  action: ctx.action,
  payload: ctx.parameters,
  metadata: ctx.metadata
});
return [{ json: { ...ctx, body } }];
""".replace('__AGENT_NAME__', cfg['name'])))
    n.append(http_node("Create Approval Backend", 1700, 520, "POST", "={{ $env.BACKEND_API_URL }}/api/approval/create", body="={{ $json.body }}"))
    n.append(code_node("Prepare Manager Notification", 1900, 520, """
const input = $input.first().json;
const approval_id = input.approval_id || input.request_id;
const approval_url = `{{ $env.N8N_WEBHOOK_URL }}/approval/action?approval_id=${approval_id}&decision=approve&manager_id=manager`;
const ctx = input.metadata || {};
return [{ json: {
  request_id: ctx.request_id,
  user: ctx.user,
  role: ctx.role,
  platform: "teams",
  recipients: ["manager@example.com"],
  subject: "Approval Required",
  message: `Approval required for ${ctx.user}: ${input.action}. Approve: ${approval_url}`,
  metadata: ctx
}}];
"""))
    n.append(http_node("Notify Manager", 2100, 520, "POST", "={{ $env.N8N_WEBHOOK_URL }}/agent/notification", body='={{ JSON.stringify({ request_id: $json.request_id, user: $json.user, role: $json.role, platform: $json.platform, recipients: $json.recipients, subject: $json.subject, message: $json.message, metadata: $json.metadata }) }}'))
    n.append(set_node("Pending Response", 2300, 520, {
        "status": "pending_approval",
        "response": "={{ `Your request has been submitted for manager approval. You will be notified once it is reviewed.` }}"
    }))
    n.append(respond_node("Respond Pending", 2500, 520))
    # execution branch
    n.append(code_node("Prepare Tool Call", 1700, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  ...ctx.parameters,
  request_id: ctx.request_id,
  user: ctx.user,
  role: ctx.role,
  metadata: ctx.metadata
});
return [{ json: { ...ctx, body } }];
"""))
    n.append(http_node("Execute Tool", 1900, 300, "POST", f"={{{{ $env.BACKEND_API_URL }}}}/api/{agent_id}/{{{{ $json.action }}}}", body="={{ $json.body }}"))
    n.append(code_node("Format Result", 2100, 300, """
const input = $input.first().json;
const ctx = input.metadata || {};
return [{ json: { request_id: ctx.request_id, agent: input.agent || 'HR', status: input.status || 'success', result: input.result || input, message: input.message || 'Completed' } }];
"""))
    n.append(respond_node("Respond Result", 2300, 300))

    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"], 1)  # false
    connect(w, n[4]["name"], n[5]["name"])
    connect(w, n[3]["name"], n[6]["name"], 0)  # true
    connect(w, n[6]["name"], n[7]["name"])
    connect(w, n[7]["name"], n[8]["name"])
    connect(w, n[8]["name"], n[9]["name"])
    connect(w, n[9]["name"], n[10]["name"], 0)  # true (approval)
    connect(w, n[10]["name"], n[11]["name"])
    connect(w, n[11]["name"], n[12]["name"])
    connect(w, n[12]["name"], n[13]["name"])
    connect(w, n[13]["name"], n[14]["name"])
    connect(w, n[14]["name"], n[15]["name"])
    connect(w, n[9]["name"], n[16]["name"], 1)  # false (execute)
    connect(w, n[16]["name"], n[17]["name"])
    connect(w, n[17]["name"], n[18]["name"])
    connect(w, n[18]["name"], n[19]["name"])
    save_wf(w, f"agent_{agent_id}.json")

# ---------------------------------------------------------------------------
# Support Agents
# ---------------------------------------------------------------------------
def build_database_agent():
    w = make_wf("Database Agent - Specialized Agent", tags=["database", "agent"])
    n = []
    n.append(webhook_node("Database Agent Trigger", 100, 300, "agent/database"))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: {
  operation: body.operation,
  db_system: body.db_system || 'mssql',
  session_id: body.session_id,
  user_id: body.user_id,
  table: body.table,
  data: body.data || {},
  where: body.where || {},
  query: body.query,
  metadata: body.metadata || {}
}}];
"""))
    n.append(code_node("Prepare DB Request", 500, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  operation: ctx.operation,
  db_system: ctx.db_system,
  session_id: ctx.session_id,
  user_id: ctx.user_id,
  table: ctx.table,
  data: ctx.data,
  where: ctx.where,
  query: ctx.query,
  metadata: ctx.metadata
});
return [{ json: { body } }];
"""))
    n.append(http_node("Call Database Backend", 700, 300, "POST", "={{ $env.BACKEND_API_URL }}/api/database/execute", body="={{ $json.body }}"))
    n.append(code_node("Format Response", 900, 300, """
const input = $input.first().json;
const metadata = input.metadata || {};
if (input.operation === 'memory_get') {
  return [{ json: { memory: input.memory || [], metadata } }];
}
return [{ json: { status: input.status || 'success', result: input.result, metadata } }];
"""))
    n.append(respond_node("Respond", 1100, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    save_wf(w, "agent_database.json")

def build_security_agent():
    w = make_wf("Security & Compliance Agent - Specialized Agent", tags=["security", "agent"])
    n = []
    n.append(webhook_node("Security Agent Trigger", 100, 300, "agent/security"))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: {
  request_id: body.request_id,
  user: body.user,
  event_type: body.event_type,
  payload: body.payload || {},
  risk_level: body.risk_level || 'low',
  metadata: body.metadata || {}
}}];
"""))
    n.append(code_node("Prepare Audit Request", 500, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  request_id: ctx.request_id,
  user: ctx.user,
  event_type: ctx.event_type,
  payload: ctx.payload,
  risk_level: ctx.risk_level,
  metadata: ctx.metadata
});
return [{ json: { body } }];
"""))
    n.append(http_node("Log Audit", 700, 300, "POST", "={{ $env.BACKEND_API_URL }}/api/security/audit", body="={{ $json.body }}"))
    n.append(code_node("Format Response", 900, 300, """
const input = $input.first().json;
return [{ json: { status: 'logged', audit_id: input.audit_id, metadata: input.metadata || {} } }];
"""))
    n.append(respond_node("Respond", 1100, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    save_wf(w, "agent_security.json")

def build_notification_agent():
    w = make_wf("Notification Agent - Specialized Agent", tags=["notification", "agent"])
    n = []
    n.append(webhook_node("Notification Agent Trigger", 100, 300, "agent/notification"))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: {
  request_id: body.request_id,
  user: body.user,
  platform: body.platform || 'email',
  recipients: body.recipients || [],
  subject: body.subject,
  message: body.message,
  metadata: body.metadata || {}
}}];
"""))
    n.append(code_node("Prepare Notification Request", 500, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({
  request_id: ctx.request_id,
  user: ctx.user,
  platform: ctx.platform,
  recipients: ctx.recipients,
  subject: ctx.subject,
  message: ctx.message,
  metadata: ctx.metadata
});
return [{ json: { body } }];
"""))
    n.append(http_node("Send Notification Backend", 700, 300, "POST", "={{ $env.BACKEND_API_URL }}/api/notification/send", body="={{ $json.body }}"))
    n.append(code_node("Format Response", 900, 300, """
const input = $input.first().json;
return [{ json: { status: input.status || 'sent', metadata: input.metadata || {} } }];
"""))
    n.append(respond_node("Respond", 1100, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    save_wf(w, "agent_notification.json")

def build_email_agent():
    w = make_wf("Email Agent - Specialized Agent", tags=["email", "agent"])
    system = """You are the Email Agent for an enterprise AI automation platform.
Capabilities: read emails, categorize emails, extract tasks, generate draft responses, send emails, route emails, follow-up tracking.
Tools: Outlook, Gmail, SMTP.
Given the request, return ONLY a JSON object with keys: action (one of: read, categorize, extract_tasks, draft, send, route, followup), parameters, response."""
    n = []
    n.append(webhook_node("Email Agent Trigger", 100, 300, "agent/email"))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: { request_id: body.request_id, user: body.user, role: body.role, payload: body.payload || {}, metadata: body.metadata || {} } }];
"""))
    n.append(set_node("Prepare Email Prompt", 500, 300, {"prompt": "={{ `Original request: ${$json.payload?.original_message || ''}\n\nParameters: ${JSON.stringify($json.payload?.parameters || {})}\n\nDetermine the email action and parameters.` }}"}))
    n.append(openai_node("Email Reasoning", 700, 300, system, "={{ $json.prompt }}"))
    n.append(code_node("Parse Action", 900, 300, """
const raw = $json.message?.content || $json.choices?.[0]?.message?.content || $json;
let parsed = {};
try { parsed = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (e) {}
const ctx = $input.first().json;
return [{ json: { ...ctx, ...parsed } }];
"""))
    n.append(code_node("Prepare Email Backend", 1100, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({ ...ctx.parameters, request_id: ctx.request_id, user: ctx.user, role: ctx.role, metadata: ctx.metadata });
return [{ json: { ...ctx, body } }];
"""))
    n.append(http_node("Execute Email Action", 1300, 300, "POST", "={{ $env.BACKEND_API_URL }}/api/email/{{ $json.action }}", body="={{ $json.body }}"))
    n.append(code_node("Format Response", 1500, 300, """
const input = $input.first().json;
return [{ json: { request_id: input.metadata?.request_id, status: input.status || 'success', result: input.result || input } }];
"""))
    n.append(respond_node("Respond", 1700, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    connect(w, n[5]["name"], n[6]["name"])
    connect(w, n[6]["name"], n[7]["name"])
    connect(w, n[7]["name"], n[8]["name"])
    save_wf(w, "agent_email.json")

def build_knowledge_agent():
    w = make_wf("Knowledge Agent - Specialized Agent", tags=["knowledge", "agent"])
    system = """You are the Knowledge Agent for an enterprise AI automation platform.
Data sources: SharePoint, internal documents, company knowledge base.
Capabilities: company policy search, internal documentation search, SOP retrieval, FAQ answering, knowledge base management.
Given the request, return ONLY a JSON object with keys: action (search|answer|sop|faq), query (string), filters (object), response."""
    n = []
    n.append(webhook_node("Knowledge Agent Trigger", 100, 300, "agent/knowledge"))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: { request_id: body.request_id, user: body.user, payload: body.payload || {}, metadata: body.metadata || {} } }];
"""))
    n.append(set_node("Prepare Knowledge Prompt", 500, 300, {"prompt": "={{ `Original request: ${$json.payload?.original_message || ''}\n\nParameters: ${JSON.stringify($json.payload?.parameters || {})}\n\nDetermine the knowledge action and query.` }}"}))
    n.append(openai_node("Knowledge Reasoning", 700, 300, system, "={{ $json.prompt }}"))
    n.append(code_node("Parse Action", 900, 300, """
const raw = $json.message?.content || $json.choices?.[0]?.message?.content || $json;
let parsed = {};
try { parsed = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (e) {}
const ctx = $input.first().json;
return [{ json: { ...ctx, ...parsed } }];
"""))
    n.append(code_node("Prepare Knowledge Backend", 1100, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({ query: ctx.query, filters: ctx.filters, request_id: ctx.request_id, user: ctx.user, metadata: ctx.metadata });
return [{ json: { ...ctx, body } }];
"""))
    n.append(http_node("Execute Knowledge Search", 1300, 300, "POST", "={{ $env.BACKEND_API_URL }}/api/knowledge/{{ $json.action }}", body="={{ $json.body }}"))
    n.append(code_node("Format Response", 1500, 300, """
const input = $input.first().json;
return [{ json: { request_id: input.metadata?.request_id, status: input.status || 'success', answer: input.answer || input.result || input } }];
"""))
    n.append(respond_node("Respond", 1700, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    connect(w, n[5]["name"], n[6]["name"])
    connect(w, n[6]["name"], n[7]["name"])
    connect(w, n[7]["name"], n[8]["name"])
    save_wf(w, "agent_knowledge.json")

def build_reporting_agent():
    w = make_wf("Reporting Agent - Specialized Agent", tags=["reporting", "agent"])
    system = """You are the Reporting Agent for an enterprise AI automation platform.
Capabilities: daily, weekly, monthly reports, KPI reports, department performance reports, executive dashboards, AI-generated recommendations.
Given the request, return ONLY a JSON object with keys: report_type (one of: daily, weekly, monthly, kpi, department, executive), parameters, response."""
    n = []
    n.append(webhook_node("Reporting Agent Trigger", 100, 300, "agent/reporting"))
    n.append(code_node("Extract Input", 300, 300, """
const body = $json.body || $json;
return [{ json: { request_id: body.request_id, user: body.user, payload: body.payload || {}, metadata: body.metadata || {} } }];
"""))
    n.append(set_node("Prepare Report Prompt", 500, 300, {"prompt": "={{ `Original request: ${$json.payload?.original_message || ''}\n\nParameters: ${JSON.stringify($json.payload?.parameters || {})}\n\nDetermine the report type and parameters.` }}"}))
    n.append(openai_node("Reporting Reasoning", 700, 300, system, "={{ $json.prompt }}"))
    n.append(code_node("Parse Report Request", 900, 300, """
const raw = $json.message?.content || $json.choices?.[0]?.message?.content || $json;
let parsed = {};
try { parsed = typeof raw === 'string' ? JSON.parse(raw) : raw; } catch (e) {}
const ctx = $input.first().json;
return [{ json: { ...ctx, ...parsed } }];
"""))
    n.append(code_node("Prepare Report Backend", 1100, 300, """
const ctx = $input.first().json;
const body = JSON.stringify({ ...ctx.parameters, report_type: ctx.report_type, request_id: ctx.request_id, user: ctx.user, metadata: ctx.metadata });
return [{ json: { ...ctx, body } }];
"""))
    n.append(http_node("Generate Report", 1300, 300, "POST", "={{ $env.BACKEND_API_URL }}/api/reporting/{{ $json.report_type }}", body="={{ $json.body }}"))
    n.append(code_node("Format Response", 1500, 300, """
const input = $input.first().json;
return [{ json: { request_id: input.metadata?.request_id, status: input.status || 'success', report: input.report || input } }];
"""))
    n.append(respond_node("Respond", 1700, 300))
    for node in n:
        add_node(w, node)
    connect(w, n[0]["name"], n[1]["name"])
    connect(w, n[1]["name"], n[2]["name"])
    connect(w, n[2]["name"], n[3]["name"])
    connect(w, n[3]["name"], n[4]["name"])
    connect(w, n[4]["name"], n[5]["name"])
    connect(w, n[5]["name"], n[6]["name"])
    connect(w, n[6]["name"], n[7]["name"])
    connect(w, n[7]["name"], n[8]["name"])
    save_wf(w, "agent_reporting.json")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    build_master()
    build_coordinator()
    build_approval_handler()
    for agent_id, cfg in BUSINESS_AGENTS.items():
        build_business_agent(agent_id, cfg)
    build_database_agent()
    build_security_agent()
    build_notification_agent()
    build_email_agent()
    build_knowledge_agent()
    build_reporting_agent()
    print("All n8n workflows generated.")
