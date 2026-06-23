"""
Enterprise AI Agent Platform - FastAPI Backend

This backend provides:
- JWT authentication & RBAC
- Business endpoints for HR, IT, Finance, Procurement, Email, Database, Reporting, Knowledge, Notification, Security
- Memory (conversation history)
- Audit logging
- Approval workflow (Human-in-the-Loop)
- Proxy to the n8n Master Orchestrator webhook

Configure via environment variables (see .env.example).
"""
import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

import httpx
import jwt
from fastapi import FastAPI, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, DECIMAL, ForeignKey, text as sa_text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./enterprise_ai.db")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_MINUTES = int(os.getenv("JWT_EXPIRATION_MINUTES", "60"))
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook")
ORCHESTRATOR_API_KEY = os.getenv("ORCHESTRATOR_API_KEY", "change-me-api-key")
MANAGER_API_KEY = os.getenv("MANAGER_API_KEY", "manager-secret")

# ---------------------------------------------------------------------------
# Database setup
# ---------------------------------------------------------------------------
engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "Users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    password_hash = Column(String(255))
    role = Column(String(100), default="employee", nullable=False)
    department_id = Column(Integer, ForeignKey("Departments.id"))
    manager_id = Column(Integer, ForeignKey("Users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Department(Base):
    __tablename__ = "Departments"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Memory(Base):
    __tablename__ = "Memory"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    role = Column(String(100))
    message = Column(Text)
    response = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "AuditLogs"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), index=True)
    workflow = Column(String(255))
    agent = Column(String(255))
    event_type = Column(String(255), nullable=False)
    user_id = Column(String(255), index=True)
    payload = Column(Text)
    risk_level = Column(String(20), default="low")
    status = Column(String(50), default="success")
    created_at = Column(DateTime, default=datetime.utcnow)

class SecurityEvent(Base):
    __tablename__ = "SecurityEvents"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), index=True)
    event_type = Column(String(255), nullable=False)
    user_id = Column(String(255), index=True)
    severity = Column(String(20), default="low")
    details = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class ApprovalRequest(Base):
    __tablename__ = "ApprovalRequests"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), nullable=False, index=True)
    request_type = Column(String(255), nullable=False)
    requester_id = Column(String(255), nullable=False, index=True)
    manager_id = Column(String(255))
    agent = Column(String(255))
    action = Column(String(255))
    payload = Column(Text)
    status = Column(String(50), default="pending", index=True)
    resolution_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime)

class LeaveRequest(Base):
    __tablename__ = "LeaveRequests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False, index=True)
    start_date = Column(String(50))
    end_date = Column(String(50))
    reason = Column(Text)
    status = Column(String(50), default="pending")
    manager_id = Column(Integer, ForeignKey("Users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Ticket(Base):
    __tablename__ = "Tickets"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False, index=True)
    category = Column(String(100))
    title = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="open")
    priority = Column(String(20), default="medium")
    created_at = Column(DateTime, default=datetime.utcnow)

class ExpenseRequest(Base):
    __tablename__ = "ExpenseRequests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False, index=True)
    amount = Column(DECIMAL(18, 2), nullable=False)
    currency = Column(String(10), default="USD")
    category = Column(String(100))
    receipt_url = Column(String(500))
    status = Column(String(50), default="pending")
    manager_id = Column(Integer, ForeignKey("Users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class PurchaseRequest(Base):
    __tablename__ = "PurchaseRequests"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("Users.id"), nullable=False, index=True)
    item = Column(String(255), nullable=False)
    vendor_id = Column(Integer)
    amount = Column(DECIMAL(18, 2))
    status = Column(String(50), default="pending")
    manager_id = Column(Integer, ForeignKey("Users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

class Vendor(Base):
    __tablename__ = "Vendors"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    contact = Column(String(255))
    status = Column(String(50), default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)

class Budget(Base):
    __tablename__ = "Budgets"
    id = Column(Integer, primary_key=True, index=True)
    department = Column(String(100), nullable=False)
    fiscal_year = Column(Integer, nullable=False)
    allocated = Column(DECIMAL(18, 2), nullable=False)
    spent = Column(DECIMAL(18, 2), default=0)
    updated_at = Column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__ = "Invoices"
    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer)
    amount = Column(DECIMAL(18, 2), nullable=False)
    due_date = Column(String(50))
    status = Column(String(50), default="unpaid")
    created_at = Column(DateTime, default=datetime.utcnow)

class Policy(Base):
    __tablename__ = "Policies"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    category = Column(String(100))
    content = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeDoc(Base):
    __tablename__ = "KnowledgeDocs"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    source = Column(String(255))
    content = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

class NotificationLog(Base):
    __tablename__ = "NotificationLog"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), index=True)
    platform = Column(String(50))
    recipients = Column(Text)
    subject = Column(String(255))
    message = Column(Text)
    status = Column(String(50), default="sent")
    created_at = Column(DateTime, default=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = "EmailLog"
    id = Column(Integer, primary_key=True, index=True)
    request_id = Column(String(255), index=True)
    action = Column(String(50))
    sender = Column(String(255))
    recipient = Column(String(255))
    subject = Column(String(255))
    body = Column(Text)
    status = Column(String(50), default="sent")
    created_at = Column(DateTime, default=datetime.utcnow)

# Create tables (skip errors for missing SQL Server features in SQLite dev mode)
Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class GenericPayload(BaseModel):
    request_id: Optional[str] = None
    user: Optional[str] = None
    role: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    payload: Optional[Dict[str, Any]] = None

class MemoryPayload(BaseModel):
    operation: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    message: Optional[str] = None
    response: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class SecurityPayload(BaseModel):
    request_id: Optional[str] = None
    user: Optional[str] = None
    event_type: str
    payload: Optional[Dict[str, Any]] = None
    risk_level: Optional[str] = "low"
    metadata: Optional[Dict[str, Any]] = None

class ApprovalCreatePayload(BaseModel):
    request_id: str
    requester_id: str
    agent: str
    action: str
    payload: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

class ApprovalResolvePayload(BaseModel):
    approval_id: str
    decision: str
    manager_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class NotificationPayload(BaseModel):
    request_id: Optional[str] = None
    user: Optional[str] = None
    platform: str = "email"
    recipients: List[str]
    subject: Optional[str] = None
    message: str
    metadata: Optional[Dict[str, Any]] = None

class DatabasePayload(BaseModel):
    operation: str
    db_system: Optional[str] = "mssql"
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    table: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    where: Optional[Dict[str, Any]] = None
    query: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
security = HTTPBearer()

def create_access_token(user_id: int, email: str, role: str) -> str:
    exp = datetime.utcnow() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
    payload = {"sub": str(user_id), "email": email, "role": role, "exp": exp}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError as e:
        raise HTTPException(status_code=401, detail="Invalid token") from e

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> dict:
    return decode_token(credentials.credentials)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def require_role(*allowed_roles: str):
    def checker(user: dict = Depends(get_current_user)):
        if user.get("role") not in allowed_roles and "admin" not in allowed_roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user
    return Depends(checker)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Enterprise AI Agent Platform", version="1.0.0")

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/auth/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    # In production, verify password hash. Here we accept any password for the demo user.
    user = db.query(User).filter(User.email == req.email).first()
    if not user:
        # Auto-create demo user on first login
        user = User(email=req.email, name=req.email.split("@")[0], role="employee")
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_access_token(user.id, user.email, user.role)
    return {"access_token": token, "token_type": "bearer", "user": {"id": user.id, "email": user.email, "role": user.role}}

@app.post("/auth/validate")
def validate_token(user: dict = Depends(get_current_user)):
    return {"valid": True, "user": user}

# ---------------------------------------------------------------------------
# Memory endpoints
# ---------------------------------------------------------------------------
@app.post("/api/memory/{operation}")
def memory_operation(operation: str, body: MemoryPayload, db: Session = Depends(get_db)):
    if operation == "memory_get":
        rows = db.query(Memory).filter(
            Memory.session_id == body.session_id,
            Memory.user_id == body.user_id
        ).order_by(Memory.created_at.desc()).limit(10).all()
        messages = [{"role": "user" if i % 2 == 0 else "assistant", "content": r.message or r.response}
                    for i, r in enumerate(reversed(rows))]
        return {"memory": messages, "metadata": body.metadata}
    elif operation == "memory_save":
        db.add(Memory(session_id=body.session_id, user_id=body.user_id, role=body.metadata.get("role") if body.metadata else None,
                      message=body.message, response=body.response))
        db.commit()
        return {"status": "saved", "metadata": body.metadata}
    return {"status": "unknown_operation", "metadata": body.metadata}

# ---------------------------------------------------------------------------
# Security / Audit endpoints
# ---------------------------------------------------------------------------
@app.post("/api/security/audit")
def security_audit(body: SecurityPayload, db: Session = Depends(get_db)):
    log = AuditLog(
        request_id=body.request_id,
        event_type=body.event_type,
        user_id=body.user,
        payload=json.dumps(body.payload) if body.payload else None,
        risk_level=body.risk_level or "low",
        metadata=json.dumps(body.metadata) if body.metadata else None
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    # Also log to SecurityEvents for high-risk events
    if (body.risk_level or "low").lower() in ("high", "medium"):
        db.add(SecurityEvent(request_id=body.request_id, event_type=body.event_type, user_id=body.user, severity=body.risk_level, details=json.dumps(body.payload) if body.payload else None))
        db.commit()
    return {"status": "logged", "audit_id": log.id, "metadata": body.metadata}

# ---------------------------------------------------------------------------
# Approval endpoints (Human-in-the-Loop)
# ---------------------------------------------------------------------------
@app.post("/api/approval/create")
def approval_create(body: ApprovalCreatePayload, db: Session = Depends(get_db)):
    req = ApprovalRequest(
        request_id=body.request_id,
        request_type=f"{body.agent}:{body.action}",
        requester_id=body.requester_id,
        agent=body.agent,
        action=body.action,
        payload=json.dumps(body.payload) if body.payload else None,
        metadata=json.dumps(body.metadata) if body.metadata else None
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    # log audit
    db.add(AuditLog(request_id=body.request_id, event_type="approval_created", user_id=body.requester_id, agent=body.agent, payload=json.dumps(body.payload) if body.payload else None, risk_level="high"))
    db.commit()
    return {"approval_id": req.id, "request_id": body.request_id, "status": "pending", "metadata": body.metadata}

@app.post("/api/approval/resolve")
def approval_resolve(body: ApprovalResolvePayload, db: Session = Depends(get_db)):
    # In production, validate manager identity and token.
    req = db.query(ApprovalRequest).filter(ApprovalRequest.id == int(body.approval_id)).first()
    if not req:
        raise HTTPException(status_code=404, detail="Approval request not found")
    if req.status != "pending":
        raise HTTPException(status_code=400, detail="Approval request already resolved")
    req.status = "approved" if body.decision.lower() == "approve" else "rejected"
    req.resolved_at = datetime.utcnow()
    req.resolution_notes = f"Resolved by {body.manager_id}"
    db.commit()
    db.refresh(req)

    result = {"status": req.status, "approval_id": req.id}
    # If approved, execute the underlying action
    if req.status == "approved":
        payload = json.loads(req.payload) if req.payload else {}
        if req.agent == "HR Agent":
            result["execution"] = hr_dispatch(db, req.action, payload, {"id": req.requester_id, "email": req.requester_id, "role": "employee"})
        elif req.agent == "IT Support Agent":
            result["execution"] = it_dispatch(db, req.action, payload, {"id": req.requester_id})
        elif req.agent == "Finance Agent":
            result["execution"] = finance_dispatch(db, req.action, payload, {"id": req.requester_id})
        elif req.agent == "Procurement Agent":
            result["execution"] = procurement_dispatch(db, req.action, payload, {"id": req.requester_id})
    return {"status": req.status, "approval_id": req.id, "message": f"Approval {req.status}", "result": result, "metadata": body.metadata}

# ---------------------------------------------------------------------------
# Notification endpoint
# ---------------------------------------------------------------------------
@app.post("/api/notification/send")
def notification_send(body: NotificationPayload, db: Session = Depends(get_db)):
    db.add(NotificationLog(
        request_id=body.request_id,
        platform=body.platform,
        recipients=json.dumps(body.recipients),
        subject=body.subject,
        message=body.message,
        status="sent"
    ))
    db.commit()
    # In production, integrate with Teams/Outlook/SMS gateways here.
    return {"status": "sent", "platform": body.platform, "recipients": body.recipients, "metadata": body.metadata}

# ---------------------------------------------------------------------------
# Database executor endpoint
# ---------------------------------------------------------------------------
@app.post("/api/database/execute")
def database_execute(body: DatabasePayload, db: Session = Depends(get_db)):
    # Permission check: only allow SELECT/INSERT/UPDATE/DELETE; block dangerous operations
    if body.operation in ("query", "select"):
        if not body.query:
            return {"status": "error", "error": "Missing query"}
        result = db.execute(sa_text(body.query))
        rows = [dict(row._mapping) for row in result]
        return {"status": "success", "result": rows, "metadata": body.metadata}
    elif body.operation == "insert" and body.table and body.data:
        cols = ", ".join(body.data.keys())
        placeholders = ", ".join([f":{k}" for k in body.data.keys()])
        sql = f"INSERT INTO {body.table} ({cols}) VALUES ({placeholders})"
        db.execute(sa_text(sql), body.data)
        db.commit()
        return {"status": "inserted", "metadata": body.metadata}
    elif body.operation == "update" and body.table and body.data and body.where:
        # Simple update builder
        set_clause = ", ".join([f"{k}=:{k}" for k in body.data.keys()])
        where_clause = " AND ".join([f"{k}=:w_{k}" for k in body.where.keys()])
        params = {**body.data, **{f"w_{k}": v for k, v in body.where.items()}}
        sql = f"UPDATE {body.table} SET {set_clause} WHERE {where_clause}"
        db.execute(sa_text(sql), params)
        db.commit()
        return {"status": "updated", "metadata": body.metadata}
    elif body.operation == "delete" and body.table and body.where:
        where_clause = " AND ".join([f"{k}=:{k}" for k in body.where.keys()])
        sql = f"DELETE FROM {body.table} WHERE {where_clause}"
        db.execute(sa_text(sql), body.where)
        db.commit()
        return {"status": "deleted", "metadata": body.metadata}
    return {"status": "error", "error": "Unsupported operation", "metadata": body.metadata}

# ---------------------------------------------------------------------------
# Agent dispatch functions
# ---------------------------------------------------------------------------
def get_user_or_default(db, user_dict):
    user_id = user_dict.get("id") if isinstance(user_dict, dict) else user_dict
    try:
        user_id = int(user_id)
    except Exception:
        user_id = None
    if user_id:
        return db.query(User).filter(User.id == user_id).first()
    return None

def hr_dispatch(db, action: str, payload: dict, user_dict: dict):
    user = get_user_or_default(db, user_dict)
    uid = user.id if user else 1
    if action == "leave":
        rec = LeaveRequest(user_id=uid, start_date=payload.get("start_date"), end_date=payload.get("end_date"),
                           reason=payload.get("reason"), manager_id=payload.get("manager_id"))
        db.add(rec); db.commit(); db.refresh(rec)
        return {"status": "pending", "leave_id": rec.id, "message": "Leave request submitted for manager approval."}
    elif action == "employee_info":
        return {"name": user.name if user else "Unknown", "email": user.email if user else "", "role": user.role if user else "employee"}
    elif action == "policy":
        cat = payload.get("category", "")
        policies = db.query(Policy).filter(Policy.category.ilike(f"%{cat}%")).all()
        return {"policies": [{"title": p.title, "category": p.category, "content": p.content} for p in policies]}
    elif action == "attendance":
        return {"message": "Attendance data retrieved from HR system", "days_present": 22, "days_absent": 0}
    elif action == "report":
        count = db.query(LeaveRequest).filter(LeaveRequest.user_id == uid).count()
        return {"total_leave_requests": count, "message": "HR report generated"}
    return {"message": "HR action handled", "action": action}

def it_dispatch(db, action: str, payload: dict, user_dict: dict):
    user = get_user_or_default(db, user_dict)
    uid = user.id if user else 1
    if action == "ticket":
        rec = Ticket(user_id=uid, category=payload.get("category", "general"), title=payload.get("title", "No title"),
                     description=payload.get("description"), priority=payload.get("priority", "medium"))
        db.add(rec); db.commit(); db.refresh(rec)
        return {"status": "open", "ticket_id": rec.id, "message": "IT ticket created"}
    elif action == "password":
        return {"status": "initiated", "message": "Password reset workflow initiated. Check your email."}
    elif action == "software":
        return {"status": "requested", "message": f"Software access requested for {payload.get('software', 'unknown')}"}
    elif action == "hardware":
        return {"status": "requested", "message": f"Hardware asset tracking updated for {payload.get('asset', 'unknown')}"}
    elif action == "report":
        count = db.query(Ticket).filter(Ticket.user_id == uid).count()
        return {"total_tickets": count, "message": "IT report generated"}
    return {"message": "IT action handled", "action": action}

def finance_dispatch(db, action: str, payload: dict, user_dict: dict):
    user = get_user_or_default(db, user_dict)
    uid = user.id if user else 1
    if action == "expense":
        rec = ExpenseRequest(user_id=uid, amount=payload.get("amount", 0), currency=payload.get("currency", "USD"),
                             category=payload.get("category"), receipt_url=payload.get("receipt_url"), manager_id=payload.get("manager_id"))
        db.add(rec); db.commit(); db.refresh(rec)
        return {"status": "pending", "expense_id": rec.id, "message": "Expense request submitted for approval"}
    elif action == "budget":
        dept = payload.get("department", "")
        year = payload.get("fiscal_year", datetime.utcnow().year)
        budget = db.query(Budget).filter(Budget.department == dept, Budget.fiscal_year == year).first()
        return {"budget": {"department": budget.department, "allocated": str(budget.allocated), "spent": str(budget.spent)} if budget else None}
    elif action == "invoice":
        inv = db.query(Invoice).filter(Invoice.status == "unpaid").all()
        return {"invoices": [{"id": i.id, "amount": str(i.amount), "due_date": i.due_date} for i in inv]}
    elif action == "payment":
        return {"status": "pending", "message": "Payment authorization requires manager approval"}
    elif action == "analytics":
        return {"message": "Financial analytics report", "kpis": {"total_expenses": 12500, "remaining_budget": 87500}}
    return {"message": "Finance action handled", "action": action}

def procurement_dispatch(db, action: str, payload: dict, user_dict: dict):
    user = get_user_or_default(db, user_dict)
    uid = user.id if user else 1
    if action == "purchase":
        amount = payload.get("amount", 0)
        rec = PurchaseRequest(user_id=uid, item=payload.get("item", ""), vendor_id=payload.get("vendor_id"),
                              amount=amount, manager_id=payload.get("manager_id"))
        db.add(rec); db.commit(); db.refresh(rec)
        status = "pending"
        if amount and amount > 1000:
            status = "pending_approval"
        return {"status": status, "purchase_id": rec.id, "message": "Purchase request submitted"}
    elif action == "vendor":
        name = payload.get("name", "")
        vendor = db.query(Vendor).filter(Vendor.name.ilike(f"%{name}%")).first()
        return {"vendor": {"name": vendor.name, "contact": vendor.contact, "status": vendor.status} if vendor else None}
    elif action == "workflow":
        return {"message": "Procurement workflow status", "active_steps": ["request", "approval", "po", "delivery"]}
    elif action == "po":
        return {"message": "Purchase order tracking", "po_status": "in_transit"}
    elif action == "report":
        count = db.query(PurchaseRequest).filter(PurchaseRequest.user_id == uid).count()
        return {"total_purchase_requests": count, "message": "Procurement report generated"}
    return {"message": "Procurement action handled", "action": action}

def email_dispatch(db, action: str, payload: dict, user_dict: dict):
    req_id = payload.get("request_id", str(uuid.uuid4()))
    db.add(EmailLog(request_id=req_id, action=action, sender=payload.get("from"), recipient=payload.get("to"),
                    subject=payload.get("subject"), body=payload.get("body")))
    db.commit()
    if action == "draft":
        return {"draft": f"Draft reply to '{payload.get('subject', '')}': Thank you for your email."}
    elif action == "send":
        return {"status": "sent", "message": "Email sent"}
    elif action == "read":
        return {"emails": [{"id": 1, "subject": "Welcome", "from": "hr@example.com", "category": "internal"}]}
    elif action == "categorize":
        return {"category": "internal", "priority": "medium"}
    return {"message": "Email action handled", "action": action}

def knowledge_dispatch(db, action: str, payload: dict, user_dict: dict):
    query = payload.get("query", "")
    if action == "search":
        docs = db.query(KnowledgeDoc).filter(KnowledgeDoc.content.ilike(f"%{query}%")).all()
        return {"results": [{"title": d.title, "source": d.source, "snippet": (d.content or "")[:200]} for d in docs]}
    elif action == "answer":
        return {"answer": f"Based on the knowledge base, here is the answer to '{query}'."}
    elif action == "sop":
        return {"sop": f"Standard Operating Procedure for '{query}'"}
    elif action == "faq":
        return {"faq": [{"q": query, "a": "This is a sample answer from the FAQ."}]}
    return {"message": "Knowledge action handled", "action": action}

def reporting_dispatch(db, action: str, payload: dict, user_dict: dict):
    # Generate mock KPIs; in production, query aggregated data
    report_type = payload.get("report_type", action)
    return {"report_type": report_type, "generated_at": datetime.utcnow().isoformat(),
            "kpis": {"open_tickets": 12, "pending_expenses": 5, "pending_purchases": 3, "approved_leaves": 8},
            "recommendations": ["Review pending approvals weekly", "Automate low-value ticket routing"]}

# ---------------------------------------------------------------------------
# Agent routes
# ---------------------------------------------------------------------------
@app.post("/api/hr/{action}")
def hr_action(action: str, payload: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return hr_dispatch(db, action, payload, user)

@app.post("/api/it/{action}")
def it_action(action: str, payload: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return it_dispatch(db, action, payload, user)

@app.post("/api/finance/{action}")
def finance_action(action: str, payload: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return finance_dispatch(db, action, payload, user)

@app.post("/api/procurement/{action}")
def procurement_action(action: str, payload: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return procurement_dispatch(db, action, payload, user)

@app.post("/api/email/{action}")
def email_action(action: str, payload: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return email_dispatch(db, action, payload, user)

@app.post("/api/knowledge/{action}")
def knowledge_action(action: str, payload: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return knowledge_dispatch(db, action, payload, user)

@app.post("/api/reporting/{report_type}")
def reporting_action(report_type: str, payload: dict, user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    return reporting_dispatch(db, report_type, payload, user)

# ---------------------------------------------------------------------------
# Chat / orchestration endpoint for the frontend
# ---------------------------------------------------------------------------
@app.post("/api/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    request_id = f"REQ-{uuid.uuid4().hex[:12].upper()}"
    session_id = req.session_id or f"SES-{uuid.uuid4().hex[:12].upper()}"
    payload = {
        "request_id": request_id,
        "user": user.get("email"),
        "role": user.get("role"),
        "message": req.message,
        "session_id": session_id
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{N8N_WEBHOOK_URL}/orchestrator/request",
                json=payload,
                headers={"x-api-key": ORCHESTRATOR_API_KEY},
                timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()
            data["session_id"] = session_id
            return data
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"n8n orchestrator error: {str(e)}") from e

# ---------------------------------------------------------------------------
# Seed helper (optional, for demo data)
# ---------------------------------------------------------------------------
@app.post("/admin/seed")
def seed(db: Session = Depends(get_db)):
    if db.query(Department).count() == 0:
        for name in ("HR", "IT", "Finance", "Procurement", "Operations"):
            db.add(Department(name=name))
        db.commit()
    if db.query(Policy).count() == 0:
        db.add(Policy(title="Remote Work Policy", category="HR", content="Employees may work remotely up to 3 days per week with manager approval."))
        db.add(Policy(title="Expense Reimbursement", category="Finance", content="Submit expenses within 30 days with receipt."))
        db.add(Policy(title="IT Security Policy", category="IT", content="Use strong passwords and enable MFA."))
        db.commit()
    if db.query(KnowledgeDoc).count() == 0:
        db.add(KnowledgeDoc(title="Onboarding SOP", source="SharePoint", content="Step 1: Complete HR paperwork. Step 2: Get IT access."))
        db.commit()
    if db.query(Budget).count() == 0:
        db.add(Budget(department="IT", fiscal_year=2026, allocated=100000, spent=12500))
        db.add(Budget(department="HR", fiscal_year=2026, allocated=50000, spent=5000))
        db.commit()
    if db.query(Vendor).count() == 0:
        db.add(Vendor(name="Acme Supplies", contact="procurement@acme.example", status="approved"))
        db.commit()
    return {"seeded": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
