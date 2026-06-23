-- Enterprise AI Agent Platform - Microsoft SQL Server Schema
-- This schema supports the Master AI Agent and all specialized agents.

IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'EnterpriseAIPlatform')
BEGIN
    CREATE DATABASE EnterpriseAIPlatform;
END
GO

USE EnterpriseAIPlatform;
GO

-- Departments
CREATE TABLE Departments (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL,
    created_at DATETIME DEFAULT GETDATE()
);

-- Roles & RBAC
CREATE TABLE Roles (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(100) NOT NULL UNIQUE,
    permissions NVARCHAR(MAX) -- JSON array of permissions
);

-- Users
CREATE TABLE Users (
    id INT IDENTITY(1,1) PRIMARY KEY,
    email NVARCHAR(255) NOT NULL UNIQUE,
    name NVARCHAR(255) NOT NULL,
    password_hash NVARCHAR(255), -- for local auth, or use SSO
    role NVARCHAR(100) NOT NULL DEFAULT 'employee',
    department_id INT FOREIGN KEY REFERENCES Departments(id),
    manager_id INT FOREIGN KEY REFERENCES Users(id),
    created_at DATETIME DEFAULT GETDATE()
);

CREATE TABLE UserRoles (
    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(id),
    role_id INT NOT NULL FOREIGN KEY REFERENCES Roles(id),
    PRIMARY KEY (user_id, role_id)
);

-- Memory for conversation context
CREATE TABLE Memory (
    id INT IDENTITY(1,1) PRIMARY KEY,
    session_id NVARCHAR(255) NOT NULL,
    user_id NVARCHAR(255) NOT NULL,
    role NVARCHAR(100),
    message NVARCHAR(MAX),
    response NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_Memory_SessionUser ON Memory(session_id, user_id, created_at DESC);

-- Audit logs for all agent actions
CREATE TABLE AuditLogs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    request_id NVARCHAR(255),
    workflow NVARCHAR(255),
    agent NVARCHAR(255),
    event_type NVARCHAR(255) NOT NULL,
    user_id NVARCHAR(255),
    payload NVARCHAR(MAX),
    risk_level NVARCHAR(20) DEFAULT 'low',
    status NVARCHAR(50) DEFAULT 'success',
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_AuditLogs_Request ON AuditLogs(request_id, created_at DESC);
CREATE INDEX IX_AuditLogs_User ON AuditLogs(user_id, created_at DESC);

-- Security events
CREATE TABLE SecurityEvents (
    id INT IDENTITY(1,1) PRIMARY KEY,
    request_id NVARCHAR(255),
    event_type NVARCHAR(255) NOT NULL,
    user_id NVARCHAR(255),
    severity NVARCHAR(20) DEFAULT 'low',
    details NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_SecurityEvents_User ON SecurityEvents(user_id, created_at DESC);

-- Approval requests for Human-in-the-Loop
CREATE TABLE ApprovalRequests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    request_id NVARCHAR(255) NOT NULL,
    request_type NVARCHAR(255) NOT NULL,
    requester_id NVARCHAR(255) NOT NULL,
    manager_id NVARCHAR(255),
    agent NVARCHAR(255),
    action NVARCHAR(255),
    payload NVARCHAR(MAX),
    status NVARCHAR(50) DEFAULT 'pending',
    resolution_notes NVARCHAR(MAX),
    created_at DATETIME DEFAULT GETDATE(),
    resolved_at DATETIME
);
CREATE INDEX IX_ApprovalRequests_Status ON ApprovalRequests(status, created_at DESC);

-- HR Agent tables
CREATE TABLE LeaveRequests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(id),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    reason NVARCHAR(MAX),
    status NVARCHAR(50) DEFAULT 'pending',
    manager_id INT FOREIGN KEY REFERENCES Users(id),
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_LeaveRequests_User ON LeaveRequests(user_id, created_at DESC);

-- IT Support Agent tables
CREATE TABLE Tickets (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(id),
    category NVARCHAR(100),
    title NVARCHAR(255) NOT NULL,
    description NVARCHAR(MAX),
    status NVARCHAR(50) DEFAULT 'open',
    priority NVARCHAR(20) DEFAULT 'medium',
    assigned_to INT FOREIGN KEY REFERENCES Users(id),
    created_at DATETIME DEFAULT GETDATE(),
    resolved_at DATETIME
);
CREATE INDEX IX_Tickets_User ON Tickets(user_id, created_at DESC);

-- Finance Agent tables
CREATE TABLE ExpenseRequests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(id),
    amount DECIMAL(18,2) NOT NULL,
    currency NVARCHAR(10) DEFAULT 'USD',
    category NVARCHAR(100),
    receipt_url NVARCHAR(500),
    status NVARCHAR(50) DEFAULT 'pending',
    manager_id INT FOREIGN KEY REFERENCES Users(id),
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_ExpenseRequests_User ON ExpenseRequests(user_id, created_at DESC);

CREATE TABLE Budgets (
    id INT IDENTITY(1,1) PRIMARY KEY,
    department NVARCHAR(100) NOT NULL,
    fiscal_year INT NOT NULL,
    allocated DECIMAL(18,2) NOT NULL,
    spent DECIMAL(18,2) DEFAULT 0,
    updated_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_Budgets_DeptYear ON Budgets(department, fiscal_year);

CREATE TABLE Invoices (
    id INT IDENTITY(1,1) PRIMARY KEY,
    vendor_id INT,
    amount DECIMAL(18,2) NOT NULL,
    due_date DATE,
    status NVARCHAR(50) DEFAULT 'unpaid',
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_Invoices_Status ON Invoices(status, due_date);

-- Procurement Agent tables
CREATE TABLE PurchaseRequests (
    id INT IDENTITY(1,1) PRIMARY KEY,
    user_id INT NOT NULL FOREIGN KEY REFERENCES Users(id),
    item NVARCHAR(255) NOT NULL,
    vendor_id INT,
    amount DECIMAL(18,2),
    status NVARCHAR(50) DEFAULT 'pending',
    manager_id INT FOREIGN KEY REFERENCES Users(id),
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_PurchaseRequests_User ON PurchaseRequests(user_id, created_at DESC);

CREATE TABLE Vendors (
    id INT IDENTITY(1,1) PRIMARY KEY,
    name NVARCHAR(255) NOT NULL,
    contact NVARCHAR(255),
    status NVARCHAR(50) DEFAULT 'pending',
    created_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_Vendors_Status ON Vendors(status, name);

-- Knowledge Agent tables
CREATE TABLE Policies (
    id INT IDENTITY(1,1) PRIMARY KEY,
    title NVARCHAR(255) NOT NULL,
    category NVARCHAR(100),
    content NVARCHAR(MAX),
    updated_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_Policies_Category ON Policies(category, title);

CREATE TABLE KnowledgeDocs (
    id INT IDENTITY(1,1) PRIMARY KEY,
    title NVARCHAR(255) NOT NULL,
    source NVARCHAR(255),
    content NVARCHAR(MAX),
    updated_at DATETIME DEFAULT GETDATE()
);
CREATE INDEX IX_KnowledgeDocs_Source ON KnowledgeDocs(source, title);

-- Notification log
CREATE TABLE NotificationLog (
    id INT IDENTITY(1,1) PRIMARY KEY,
    request_id NVARCHAR(255),
    platform NVARCHAR(50),
    recipients NVARCHAR(MAX),
    subject NVARCHAR(255),
    message NVARCHAR(MAX),
    status NVARCHAR(50) DEFAULT 'sent',
    created_at DATETIME DEFAULT GETDATE()
);

-- Email log
CREATE TABLE EmailLog (
    id INT IDENTITY(1,1) PRIMARY KEY,
    request_id NVARCHAR(255),
    action NVARCHAR(50),
    sender NVARCHAR(255),
    recipient NVARCHAR(255),
    subject NVARCHAR(255),
    body NVARCHAR(MAX),
    status NVARCHAR(50) DEFAULT 'sent',
    created_at DATETIME DEFAULT GETDATE()
);
