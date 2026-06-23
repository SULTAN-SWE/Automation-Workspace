# Enterprise AI Agent Automation Platform

A production-ready, multi-agent enterprise AI automation platform built on an **Agent-Orchestrator architecture**. It uses **n8n** for workflow automation, **FastAPI** for business logic & integrations, **Microsoft SQL Server** for persistence, **OpenAI GPT models** for reasoning, and **React** for the employee chat interface.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [What You Get](#what-you-get)
3. [Technology Stack](#technology-stack)
4. [Repository Structure](#repository-structure)
5. [Prerequisites](#prerequisites)
6. [Setup Instructions](#setup-instructions)
7. [Human-in-the-Loop](#human-in-the-loop)
8. [Security & Compliance](#security--compliance)
9. [Testing the Platform](#testing-the-platform)
10. [Extending the Platform](#extending-the-platform)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Employee React Frontend                        │
│              (Chat interface with JWT / RBAC)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ POST /api/chat  + Bearer JWT
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Business Logic)                 │
│  Auth (JWT) · RBAC · Memory · Audit · Approval · Integrations    │
│  HR · IT · Finance · Procurement · Email · Knowledge · Reporting  │
└──────────────────────────┬──────────────────────────────────────┘
                           │ x-api-key + JSON
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              n8n Master AI Agent (Orchestrator)                  │
│   - Receives employee requests                                   │
│   - Classifies intent with GPT-4o-mini                            │
│   - Selects specialized agents                                     │
│   - Coordinates multi-agent execution                             │
│   - Synthesizes final response                                    │
│   - Audits & manages memory                                       │
└──────┬──────────────────────────────────────────────────────────┘
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│           Multi-Agent Coordinator (n8n sub-workflow)             │
│              Calls 1-N specialized agents in parallel           │
└──────┬──────────────────────────────────────────────────────────┘
       │
   ┌───┴───┐
   ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼       ▼
┌────┐ ┌────┐ ┌──────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
│ HR │ │ IT │ │Fin.  │ │Proc│ │Email│ │ DB │ │Report│ │Notif│ │Knowl│ │Sec. │
└────┘ └────┘ └──────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
   │       │       │       │       │       │       │       │       │
   └───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┴───┘
                              │
                              ▼
              ┌─────────────────────────────┐
              │  Microsoft SQL Server + APIs │
              │   Memory · Audit · HR · IT   │
              │  Finance · Procurement · etc │
              └─────────────────────────────┘
```

### Flow Summary

1. An employee sends a message through the React frontend.
2. FastAPI authenticates the JWT and forwards the request to the **n8n Master Orchestrator** webhook.
3. The Master Agent validates the shared API key, logs the request to the **Security Agent**, and fetches conversation memory from the **Database Agent**.
4. A GPT-4o-mini model classifies intent, selects the appropriate specialized agents, and flags high-risk requests.
5. If a request is high-risk (e.g., termination, salary changes, financial approvals), the Master escalates it to a manager and returns a pending status.
6. Otherwise, the Master calls the **Multi-Agent Coordinator**, which invokes each selected specialized agent in parallel.
7. Each specialized agent uses GPT to decide an action and then calls the FastAPI backend to perform the actual business operation.
8. The Master synthesizes the agent results into a natural-language response and saves it to memory.
9. All actions are written to the audit log and security events table.

---

## What You Get

- **13 import-ready n8n workflow JSON files**
  - `master_orchestrator.json` — Master AI Agent
  - `multi_agent_coordinator.json` — Multi-Agent Coordinator
  - `agent_hr.json` — HR Agent
  - `agent_it.json` — IT Support Agent
  - `agent_finance.json` — Finance Agent
  - `agent_procurement.json` — Procurement Agent
  - `agent_email.json` — Email Agent
  - `agent_database.json` — Database Agent
  - `agent_reporting.json` — Reporting Agent
  - `agent_notification.json` — Notification Agent
  - `agent_knowledge.json` — Knowledge Agent
  - `agent_security.json` — Security & Compliance Agent
  - `approval_handler.json` — Manager Approval Handler
- **FastAPI backend** (`fastapi/main.py`) with JWT auth, RBAC, memory, audit, approvals, and business endpoints.
- **React frontend** (`frontend/src/App.jsx`) for employees to chat with the Master Agent.
- **Microsoft SQL Server schema** (`database/schema.sql`) for the enterprise data model.
- **Docker Compose** (`docker-compose.yml`) to run n8n and SQL Server quickly.
- **Environment template** (`.env.example`) and a Python generator for the n8n workflows.

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 |
| Backend | FastAPI, SQLAlchemy 2.0, PyJWT, httpx |
| Automation Platform | n8n |
| AI Models | OpenAI GPT-4o-mini (replaceable) |
| Database | Microsoft SQL Server (SQLAlchemy supports SQLite dev fallback) |
| Auth | JWT, RBAC (role-based) |
| Integrations | Outlook / Teams / SharePoint / SMTP / ERP / CRM via backend APIs |

---

## Repository Structure

```
enterprise-ai-agent-platform/
├── n8n/                          # Import-ready n8n workflow JSON files
│   ├── master_orchestrator.json
│   ├── multi_agent_coordinator.json
│   ├── approval_handler.json
│   ├── agent_hr.json
│   ├── agent_it.json
│   ├── agent_finance.json
│   ├── agent_procurement.json
│   ├── agent_email.json
│   ├── agent_database.json
│   ├── agent_reporting.json
│   ├── agent_notification.json
│   ├── agent_knowledge.json
│   └── agent_security.json
├── fastapi/                      # FastAPI backend
│   ├── main.py
│   └── requirements.txt
├── frontend/                     # React chat app
│   ├── package.json
│   ├── public/index.html
│   └── src/App.jsx
├── database/
│   └── schema.sql                # Microsoft SQL Server schema
├── docker-compose.yml            # n8n + SQL Server
├── .env.example                  # Environment variable template
├── generate_n8n_workflows.py     # Python generator for the n8n JSON files
└── README.md                     # This file
```

---

## Prerequisites

- Docker & Docker Compose (for n8n and SQL Server)
- Python 3.10+ (for FastAPI backend)
- Node.js 18+ (for React frontend)
- OpenAI API key
- (Optional) Microsoft SQL Server ODBC driver if connecting from the FastAPI backend directly

---

## Setup Instructions

You can run the entire platform with a single command, or follow the manual steps below.

### One-command setup (recommended)

```bash
cd enterprise-ai-agent-platform
cp .env.example .env
# Edit .env and set OPENAI_API_KEY, JWT_SECRET, ORCHESTRATOR_API_KEY, etc.
make setup
```

This starts n8n, SQL Server, the FastAPI backend, and the React frontend, imports the n8n workflows, and seeds demo data. After it finishes, open the URLs shown in the terminal and complete the manual steps below.

### Manual setup

### 1. Clone / open the project

```bash
cd enterprise-ai-agent-platform
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env and set OPENAI_API_KEY, JWT_SECRET, ORCHESTRATOR_API_KEY, etc.
```

Export the variables for the current shell, or run a tool that loads `.env`.

### 3. Start n8n and SQL Server

```bash
export OPENAI_API_KEY=sk-...
docker-compose up -d
```

- n8n UI: http://localhost:5678
  - Default credentials: `admin` / `change-me-n8n-password`
- SQL Server: `localhost:1433`
  - SA password: `YourStrong@Passw0rd`

> SQL Server requires at least 2 GB of RAM. Increase Docker Desktop memory if the container fails.

### 4. Create the database schema

Run `database/schema.sql` against the SQL Server instance (or use a SQLite dev database by leaving `DATABASE_URL` as-is).

### 5. Install and run the FastAPI backend

```bash
cd fastapi
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Seed demo data:

```bash
curl -X POST http://localhost:8000/admin/seed
```

### 6. Install and run the React frontend

```bash
cd frontend
npm install
npm start
```

The frontend runs at http://localhost:3000.

### 7. Import n8n workflows

1. Open the n8n UI at http://localhost:5678.
2. For each file in `n8n/`:
   - Click the **Workflows** menu → **Import from File**.
   - Select the JSON file.
3. Configure the **OpenAI credential** (all OpenAI nodes reference credential ID `OPENAI_CREDENTIAL`).
   - Create a credential named **OpenAI API** in n8n and update the credential ID in each workflow, or use a single credential named `OPENAI_CREDENTIAL`.
4. Set the required environment variables in n8n:
   - `N8N_WEBHOOK_URL` (e.g., `http://localhost:5678/webhook`)
   - `BACKEND_API_URL` (e.g., `http://host.docker.internal:8000`)
   - `ORCHESTRATOR_API_KEY` (must match the backend)

### 8. Activate the workflows

- Activate the **Master AI Agent - Orchestrator** webhook workflow.
- Activate all agent workflows and the **Approval Handler** workflow.
- Activate the **Multi-Agent Coordinator** workflow.

---

## Human-in-the-Loop

The platform enforces the following rules:

- The AI **never** makes final decisions on:
  - Employee termination
  - Salary modifications
  - Financial approvals / budget approvals / payment authorizations
  - Procurement approvals above threshold / vendor onboarding
  - Legal / contract approvals
  - High-risk operational decisions
- When a business agent detects an approval-required action, it:
  1. Creates an `ApprovalRequest` record in the database.
  2. Sends a Teams/Email notification to the manager via the **Notification Agent**.
  3. Returns a pending response to the employee.
- The manager approves or rejects via the **Approval Handler** webhook (`/webhook/approval/action`).
- On approval, the backend executes the action and notifies the employee.

---

## Security & Compliance

- **JWT Authentication**: All FastAPI endpoints (except `/health` and `/auth/login`) require a valid Bearer token.
- **RBAC**: Routes can be protected by role using `require_role(...)`.
- **API Key**: The n8n Master Orchestrator validates a shared `ORCHESTRATOR_API_KEY` from the FastAPI backend.
- **Audit Logging**: Every request and final response is logged via the **Security Agent** to the `AuditLogs` table.
- **Security Events**: High-risk actions are written to `SecurityEvents`.
- **Transaction Tracking**: Approval workflows, leave requests, expense requests, and purchase requests are persisted with status and timestamps.
- **Database Agent**: Executes SQL with a permission-based operation whitelist (`query`, `insert`, `update`, `delete`). Dangerous statements are not explicitly blocked in the provided code; add a SQL allow-list/sandbox for production.

---

## Testing the Platform

1. Open the React frontend at http://localhost:3000.
2. Log in with any email (auto-creates a demo user).
3. Send a request, for example:
   - `"I want to take leave from Monday to Wednesday"` → routes to **HR Agent**.
   - `"My laptop is broken, create an IT ticket"` → routes to **IT Support Agent**.
   - `"What is the remote work policy?"` → routes to **Knowledge Agent**.
   - `"Approve a $5,000 purchase"` → flagged as high-risk and escalated to a manager.
4. Check the n8n execution logs to see the Master Agent routing to the appropriate agents.
5. Check the FastAPI backend logs and database for persisted records.

You can also test directly via curl:

```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alice@example.com","password":"demo"}'

# Chat (replace TOKEN with the access_token from login)
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer TOKEN" \
  -d '{"message":"I need next week off"}'
```

---

## Extending the Platform

- **Add a new agent**: Copy a business-agent JSON file, update its capabilities and system prompt, and create the corresponding backend dispatch function in `fastapi/main.py`.
- **Integrate real systems**: Replace the mock/stub functions in the dispatchers with calls to Outlook, Microsoft Teams, SharePoint, ERP APIs, or CRM APIs.
- **Use a vector database**: Connect the **Knowledge Agent** to a vector store (e.g., Pinecone, Weaviate) for semantic search over internal documents.
- **Add more RBAC**: Implement `require_role` decorators on sensitive backend endpoints and include permission checks in the agent workflows.
- **Observability**: Send n8n execution metrics and backend logs to Datadog, New Relic, or an ELK stack.

---

## License

This is a reference architecture provided as-is for educational and enterprise prototyping purposes. Review and harden all security, authentication, and integration code before production deployment.
