-- Accounts Receivable Collection Manager Database Schema
-- SQLite compatible schema for comprehensive AR collection management

-- Customer Master Data
CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_code VARCHAR(20) UNIQUE NOT NULL,
    customer_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    
    -- Contact Information
    primary_contact VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    mobile VARCHAR(50),
    
    -- Address Information
    billing_address TEXT,
    shipping_address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    country VARCHAR(50) DEFAULT 'USA',
    
    -- Credit Information
    credit_limit DECIMAL(15,2) DEFAULT 0,
    payment_terms_days INTEGER DEFAULT 30,
    preferred_payment_method VARCHAR(50), -- CASH, CHECK, ACH, WIRE, CREDIT_CARD
    
    -- Customer Classification
    customer_type VARCHAR(50) DEFAULT 'REGULAR', -- REGULAR, VIP, HIGH_RISK, NEW
    industry VARCHAR(100),
    customer_since DATE,
    
    -- Status and Flags
    is_active BOOLEAN DEFAULT TRUE,
    is_credit_hold BOOLEAN DEFAULT FALSE,
    collection_priority VARCHAR(20) DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH, CRITICAL
    
    -- Collection History Metrics
    avg_days_to_pay DECIMAL(5,2) DEFAULT 0,
    payment_reliability_score INTEGER DEFAULT 50, -- 0-100 scale
    total_sales_lifetime DECIMAL(15,2) DEFAULT 0,
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_contact_date DATETIME,
    last_payment_date DATETIME
);

-- Invoice/AR Records
CREATE TABLE IF NOT EXISTS invoices (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    customer_id INTEGER NOT NULL,
    
    -- Invoice Details
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    
    -- Amounts
    invoice_amount DECIMAL(15,2) NOT NULL,
    paid_amount DECIMAL(15,2) DEFAULT 0,
    outstanding_amount DECIMAL(15,2) NOT NULL,
    
    -- Status
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, PARTIAL, PAID, WRITTEN_OFF, DISPUTED
    
    -- Aging Information
    days_past_due INTEGER DEFAULT 0,
    aging_bucket VARCHAR(20), -- CURRENT, 1-30, 31-60, 61-90, 91-120, 120+
    
    -- Collection Information
    collection_status VARCHAR(30) DEFAULT 'NORMAL', -- NORMAL, FIRST_NOTICE, SECOND_NOTICE, FINAL_NOTICE, COLLECTIONS, LEGAL
    last_collection_activity_date DATETIME,
    next_collection_action_date DATETIME,
    collection_priority_score INTEGER DEFAULT 50, -- 0-100, higher = more urgent
    
    -- References
    purchase_order VARCHAR(100),
    sales_order VARCHAR(100),
    reference_number VARCHAR(100),
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CHECK (outstanding_amount >= 0),
    CHECK (paid_amount >= 0),
    CHECK (paid_amount <= invoice_amount)
);

-- Payment Records
CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    
    -- Payment Details
    payment_date DATE NOT NULL,
    payment_amount DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(50) NOT NULL, -- CASH, CHECK, ACH, WIRE, CREDIT_CARD
    payment_reference VARCHAR(100), -- Check number, transaction ID, etc.
    
    -- Payment Application
    unapplied_amount DECIMAL(15,2) DEFAULT 0,
    
    -- Source Information
    received_by VARCHAR(100),
    deposit_date DATE,
    bank_account VARCHAR(50),
    
    -- Status
    status VARCHAR(20) DEFAULT 'APPLIED', -- PENDING, APPLIED, UNAPPLIED, REVERSED
    
    -- Notes
    notes TEXT,
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    CHECK (payment_amount > 0)
);

-- Payment Applications (linking payments to specific invoices)
CREATE TABLE IF NOT EXISTS payment_applications (
    application_id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    applied_amount DECIMAL(15,2) NOT NULL,
    application_date DATE NOT NULL,
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (payment_id) REFERENCES payments(payment_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
    CHECK (applied_amount > 0),
    UNIQUE(payment_id, invoice_id)
);

-- Payment Promises
CREATE TABLE IF NOT EXISTS payment_promises (
    promise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    invoice_id INTEGER, -- Can be NULL for general promises
    
    -- Promise Details
    promise_date DATE NOT NULL,
    promised_amount DECIMAL(15,2) NOT NULL,
    promised_payment_date DATE NOT NULL,
    
    -- Status Tracking
    status VARCHAR(20) DEFAULT 'ACTIVE', -- ACTIVE, KEPT, BROKEN, PARTIALLY_KEPT, CANCELLED
    actual_payment_date DATE,
    actual_payment_amount DECIMAL(15,2) DEFAULT 0,
    
    -- Follow-up Information
    follow_up_date DATE,
    follow_up_completed BOOLEAN DEFAULT FALSE,
    escalation_required BOOLEAN DEFAULT FALSE,
    
    -- Contact Information
    contact_person VARCHAR(255),
    contact_method VARCHAR(50), -- PHONE, EMAIL, IN_PERSON, LETTER
    
    -- Notes
    notes TEXT,
    internal_notes TEXT,
    
    -- Created by
    created_by VARCHAR(100),
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
    CHECK (promised_amount > 0)
);

-- Collection Activities
CREATE TABLE IF NOT EXISTS collection_activities (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    invoice_id INTEGER, -- Can be NULL for general customer activities
    
    -- Activity Details
    activity_date DATE NOT NULL,
    activity_type VARCHAR(50) NOT NULL, -- PHONE_CALL, EMAIL, LETTER, MEETING, STATEMENT, DUNNING_LETTER
    activity_result VARCHAR(50), -- CONTACT_MADE, NO_ANSWER, BUSY, PROMISE_MADE, DISPUTE_RAISED, PAYMENT_RECEIVED
    
    -- Communication Details
    contact_person VARCHAR(255),
    communication_method VARCHAR(50),
    duration_minutes INTEGER,
    
    -- Next Action
    next_action VARCHAR(50),
    next_action_date DATE,
    
    -- Collection Stage
    collection_stage VARCHAR(30), -- FRIENDLY_REMINDER, FIRST_NOTICE, SECOND_NOTICE, FINAL_NOTICE, COLLECTIONS, LEGAL
    
    -- Notes
    activity_notes TEXT,
    outcome_summary TEXT,
    
    -- Staff Information
    performed_by VARCHAR(100),
    assigned_to VARCHAR(100),
    
    -- Follow-up
    requires_follow_up BOOLEAN DEFAULT FALSE,
    follow_up_priority VARCHAR(20) DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH, URGENT
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

-- Collection Workflow Rules
CREATE TABLE IF NOT EXISTS collection_workflows (
    workflow_id INTEGER PRIMARY KEY AUTOINCREMENT,
    workflow_name VARCHAR(255) NOT NULL,
    
    -- Trigger Conditions
    days_past_due_trigger INTEGER NOT NULL,
    amount_threshold DECIMAL(15,2) DEFAULT 0,
    customer_type_filter VARCHAR(50), -- NULL means all types
    
    -- Action Configuration
    action_type VARCHAR(50) NOT NULL, -- EMAIL_REMINDER, PHONE_CALL, DUNNING_LETTER, LEGAL_REFERRAL
    action_template_id VARCHAR(100),
    
    -- Escalation
    escalation_days INTEGER DEFAULT 7,
    escalation_action VARCHAR(50),
    
    -- Assignment
    assigned_to VARCHAR(100),
    department VARCHAR(50),
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    execution_order INTEGER DEFAULT 1,
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Collection Efficiency Metrics
CREATE TABLE IF NOT EXISTS collection_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_date DATE NOT NULL,
    
    -- Period Information
    period_start_date DATE NOT NULL,
    period_end_date DATE NOT NULL,
    metric_type VARCHAR(50) NOT NULL, -- DAILY, WEEKLY, MONTHLY, QUARTERLY
    
    -- AR Metrics
    total_ar_balance DECIMAL(15,2) DEFAULT 0,
    current_ar DECIMAL(15,2) DEFAULT 0,
    past_due_ar DECIMAL(15,2) DEFAULT 0,
    
    -- Aging Buckets
    ar_0_30_days DECIMAL(15,2) DEFAULT 0,
    ar_31_60_days DECIMAL(15,2) DEFAULT 0,
    ar_61_90_days DECIMAL(15,2) DEFAULT 0,
    ar_91_120_days DECIMAL(15,2) DEFAULT 0,
    ar_over_120_days DECIMAL(15,2) DEFAULT 0,
    
    -- Collection Performance
    cash_collected DECIMAL(15,2) DEFAULT 0,
    collection_effectiveness_index DECIMAL(5,2) DEFAULT 0, -- Percentage
    days_sales_outstanding DECIMAL(5,2) DEFAULT 0,
    
    -- Activity Metrics
    collection_calls_made INTEGER DEFAULT 0,
    emails_sent INTEGER DEFAULT 0,
    letters_sent INTEGER DEFAULT 0,
    promises_received INTEGER DEFAULT 0,
    promises_kept INTEGER DEFAULT 0,
    
    -- Efficiency Ratios
    collection_cost DECIMAL(15,2) DEFAULT 0,
    collection_cost_ratio DECIMAL(5,4) DEFAULT 0, -- Cost per dollar collected
    
    -- Staff Performance
    collector_id VARCHAR(100),
    
    -- Calculated Fields
    calculated_date DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Collection Disputes
CREATE TABLE IF NOT EXISTS disputes (
    dispute_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    invoice_id INTEGER NOT NULL,
    
    -- Dispute Details
    dispute_date DATE NOT NULL,
    disputed_amount DECIMAL(15,2) NOT NULL,
    dispute_reason VARCHAR(100) NOT NULL, -- QUALITY_ISSUE, PRICING_ERROR, DELIVERY_ISSUE, SERVICE_PROBLEM, BILLING_ERROR
    dispute_description TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, INVESTIGATING, RESOLVED, CLOSED
    resolution VARCHAR(50), -- CUSTOMER_CREDIT, PARTIAL_CREDIT, NO_ADJUSTMENT, CUSTOMER_ERROR
    
    -- Resolution Details
    resolution_amount DECIMAL(15,2) DEFAULT 0,
    resolution_date DATE,
    resolution_notes TEXT,
    
    -- Assigned Staff
    assigned_to VARCHAR(100),
    escalated_to VARCHAR(100),
    
    -- Priority
    priority VARCHAR(20) DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH, CRITICAL
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    resolved_date DATETIME,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id),
    CHECK (disputed_amount > 0)
);

-- Collection Notes
CREATE TABLE IF NOT EXISTS collection_notes (
    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    invoice_id INTEGER, -- Can be NULL for general customer notes
    
    -- Note Details
    note_date DATE NOT NULL,
    note_type VARCHAR(50) DEFAULT 'GENERAL', -- GENERAL, PAYMENT_ARRANGEMENT, DISPUTE, CREDIT_ISSUE, LEGAL
    note_text TEXT NOT NULL,
    
    -- Visibility
    is_internal BOOLEAN DEFAULT FALSE,
    is_customer_visible BOOLEAN DEFAULT FALSE,
    
    -- Alert Settings
    is_alert BOOLEAN DEFAULT FALSE,
    alert_until_date DATE,
    
    -- Created by
    created_by VARCHAR(100),
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

-- Customer Credit History
CREATE TABLE IF NOT EXISTS credit_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    
    -- Credit Event
    event_date DATE NOT NULL,
    event_type VARCHAR(50) NOT NULL, -- CREDIT_LIMIT_INCREASE, CREDIT_LIMIT_DECREASE, CREDIT_HOLD, CREDIT_RELEASE, PAYMENT_TERMS_CHANGE
    
    -- Changes
    old_credit_limit DECIMAL(15,2),
    new_credit_limit DECIMAL(15,2),
    old_payment_terms INTEGER,
    new_payment_terms INTEGER,
    
    -- Reason
    reason VARCHAR(255),
    notes TEXT,
    
    -- Authorization
    authorized_by VARCHAR(100),
    
    -- Timestamps
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Collection Reports Cache
CREATE TABLE IF NOT EXISTS report_cache (
    cache_id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type VARCHAR(100) NOT NULL,
    report_parameters TEXT, -- JSON parameters
    
    -- Cache Data
    report_data TEXT, -- JSON report data
    
    -- Cache Management
    generated_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_date DATETIME,
    is_valid BOOLEAN DEFAULT TRUE
);

-- Performance Indexes for Optimization
CREATE INDEX IF NOT EXISTS idx_customers_code ON customers(customer_code);
CREATE INDEX IF NOT EXISTS idx_customers_name ON customers(customer_name);
CREATE INDEX IF NOT EXISTS idx_customers_priority ON customers(collection_priority);
CREATE INDEX IF NOT EXISTS idx_customers_active ON customers(is_active);

CREATE INDEX IF NOT EXISTS idx_invoices_number ON invoices(invoice_number);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_invoices_aging ON invoices(aging_bucket);
CREATE INDEX IF NOT EXISTS idx_invoices_collection_status ON invoices(collection_status);
CREATE INDEX IF NOT EXISTS idx_invoices_priority_score ON invoices(collection_priority_score);

CREATE INDEX IF NOT EXISTS idx_payments_customer ON payments(customer_id);
CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);
CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);

CREATE INDEX IF NOT EXISTS idx_payment_applications_payment ON payment_applications(payment_id);
CREATE INDEX IF NOT EXISTS idx_payment_applications_invoice ON payment_applications(invoice_id);

CREATE INDEX IF NOT EXISTS idx_promises_customer ON payment_promises(customer_id);
CREATE INDEX IF NOT EXISTS idx_promises_invoice ON payment_promises(invoice_id);
CREATE INDEX IF NOT EXISTS idx_promises_status ON payment_promises(status);
CREATE INDEX IF NOT EXISTS idx_promises_promised_date ON payment_promises(promised_payment_date);
CREATE INDEX IF NOT EXISTS idx_promises_follow_up ON payment_promises(follow_up_date);

CREATE INDEX IF NOT EXISTS idx_activities_customer ON collection_activities(customer_id);
CREATE INDEX IF NOT EXISTS idx_activities_invoice ON collection_activities(invoice_id);
CREATE INDEX IF NOT EXISTS idx_activities_date ON collection_activities(activity_date);
CREATE INDEX IF NOT EXISTS idx_activities_type ON collection_activities(activity_type);
CREATE INDEX IF NOT EXISTS idx_activities_assigned ON collection_activities(assigned_to);
CREATE INDEX IF NOT EXISTS idx_activities_next_action ON collection_activities(next_action_date);

CREATE INDEX IF NOT EXISTS idx_disputes_customer ON disputes(customer_id);
CREATE INDEX IF NOT EXISTS idx_disputes_invoice ON disputes(invoice_id);
CREATE INDEX IF NOT EXISTS idx_disputes_status ON disputes(status);
CREATE INDEX IF NOT EXISTS idx_disputes_assigned ON disputes(assigned_to);

CREATE INDEX IF NOT EXISTS idx_metrics_date ON collection_metrics(metric_date);
CREATE INDEX IF NOT EXISTS idx_metrics_type ON collection_metrics(metric_type);
CREATE INDEX IF NOT EXISTS idx_metrics_collector ON collection_metrics(collector_id);