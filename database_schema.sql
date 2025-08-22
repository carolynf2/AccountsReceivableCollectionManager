-- Accounts Receivable Collection Manager Database Schema
-- SQLite compatible schema

-- Customers table
CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name VARCHAR(255) NOT NULL,
    company_name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    address TEXT,
    credit_limit DECIMAL(15, 2) DEFAULT 0,
    payment_terms INTEGER DEFAULT 30, -- days
    risk_rating VARCHAR(20) DEFAULT 'LOW', -- LOW, MEDIUM, HIGH
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_contact_date TIMESTAMP,
    notes TEXT
);

-- Invoices table
CREATE TABLE invoices (
    invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    invoice_date DATE NOT NULL,
    due_date DATE NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    balance DECIMAL(15, 2) NOT NULL,
    status VARCHAR(20) DEFAULT 'OPEN', -- OPEN, PARTIAL, PAID, WRITTEN_OFF
    description TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Payments table
CREATE TABLE payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER NOT NULL,
    payment_date DATE NOT NULL,
    amount DECIMAL(15, 2) NOT NULL,
    payment_method VARCHAR(50), -- CHECK, WIRE, CREDIT_CARD, ACH, etc.
    reference_number VARCHAR(100),
    notes TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

-- Collection activities table
CREATE TABLE collection_activities (
    activity_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    invoice_id INTEGER,
    activity_type VARCHAR(50) NOT NULL, -- CALL, EMAIL, LETTER, VISIT, LEGAL
    activity_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    collector_name VARCHAR(100),
    outcome VARCHAR(50), -- NO_ANSWER, SPOKE_TO_CUSTOMER, LEFT_MESSAGE, PROMISE_TO_PAY, DISPUTE, etc.
    notes TEXT,
    follow_up_date DATE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

-- Payment promises table
CREATE TABLE payment_promises (
    promise_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    invoice_id INTEGER,
    promise_date DATE NOT NULL,
    promised_amount DECIMAL(15, 2) NOT NULL,
    promise_made_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status VARCHAR(20) DEFAULT 'PENDING', -- PENDING, KEPT, BROKEN, PARTIAL
    actual_payment_date DATE,
    actual_amount DECIMAL(15, 2),
    notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
);

-- Collection priority settings table
CREATE TABLE priority_settings (
    setting_id INTEGER PRIMARY KEY AUTOINCREMENT,
    days_overdue_weight DECIMAL(5, 2) DEFAULT 1.0,
    amount_weight DECIMAL(5, 2) DEFAULT 1.0,
    risk_rating_weight DECIMAL(5, 2) DEFAULT 1.0,
    broken_promises_weight DECIMAL(5, 2) DEFAULT 1.0,
    last_contact_weight DECIMAL(5, 2) DEFAULT 1.0,
    updated_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Collection targets and metrics table
CREATE TABLE collection_metrics (
    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    total_receivables DECIMAL(15, 2) DEFAULT 0,
    collected_amount DECIMAL(15, 2) DEFAULT 0,
    collection_rate DECIMAL(5, 2) DEFAULT 0, -- percentage
    average_days_to_collect DECIMAL(5, 2) DEFAULT 0,
    total_activities INTEGER DEFAULT 0,
    successful_contacts INTEGER DEFAULT 0,
    promises_made INTEGER DEFAULT 0,
    promises_kept INTEGER DEFAULT 0,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for better performance
CREATE INDEX idx_customers_name ON customers(customer_name);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_date ON payments(payment_date);
CREATE INDEX idx_activities_customer ON collection_activities(customer_id);
CREATE INDEX idx_activities_date ON collection_activities(activity_date);
CREATE INDEX idx_promises_customer ON payment_promises(customer_id);
CREATE INDEX idx_promises_date ON payment_promises(promise_date);
CREATE INDEX idx_promises_status ON payment_promises(status);

-- Insert default priority settings
INSERT INTO priority_settings (
    days_overdue_weight,
    amount_weight,
    risk_rating_weight,
    broken_promises_weight,
    last_contact_weight
) VALUES (2.0, 1.5, 1.8, 2.5, 1.2);

-- Views for common queries

-- Overdue invoices view
CREATE VIEW overdue_invoices AS
SELECT 
    i.invoice_id,
    i.invoice_number,
    i.customer_id,
    c.customer_name,
    c.company_name,
    i.invoice_date,
    i.due_date,
    i.amount,
    i.balance,
    julianday('now') - julianday(i.due_date) as days_overdue,
    c.risk_rating,
    c.last_contact_date
FROM invoices i
JOIN customers c ON i.customer_id = c.customer_id
WHERE i.status IN ('OPEN', 'PARTIAL') 
AND i.due_date < date('now');

-- Customer summary view
CREATE VIEW customer_summary AS
SELECT 
    c.customer_id,
    c.customer_name,
    c.company_name,
    c.risk_rating,
    COUNT(i.invoice_id) as total_invoices,
    SUM(CASE WHEN i.status IN ('OPEN', 'PARTIAL') THEN i.balance ELSE 0 END) as outstanding_balance,
    SUM(CASE WHEN i.status IN ('OPEN', 'PARTIAL') AND i.due_date < date('now') THEN i.balance ELSE 0 END) as overdue_balance,
    MAX(i.due_date) as latest_due_date,
    c.last_contact_date,
    (SELECT COUNT(*) FROM payment_promises pp WHERE pp.customer_id = c.customer_id AND pp.status = 'BROKEN') as broken_promises
FROM customers c
LEFT JOIN invoices i ON c.customer_id = i.customer_id
GROUP BY c.customer_id, c.customer_name, c.company_name, c.risk_rating, c.last_contact_date;

-- Collection efficiency view
CREATE VIEW collection_efficiency AS
SELECT 
    c.customer_id,
    c.customer_name,
    COUNT(DISTINCT ca.activity_id) as total_activities,
    COUNT(DISTINCT CASE WHEN ca.outcome IN ('SPOKE_TO_CUSTOMER', 'PROMISE_TO_PAY') THEN ca.activity_id END) as successful_contacts,
    COUNT(DISTINCT pp.promise_id) as promises_made,
    COUNT(DISTINCT CASE WHEN pp.status = 'KEPT' THEN pp.promise_id END) as promises_kept,
    CASE 
        WHEN COUNT(DISTINCT ca.activity_id) > 0 
        THEN CAST(COUNT(DISTINCT CASE WHEN ca.outcome IN ('SPOKE_TO_CUSTOMER', 'PROMISE_TO_PAY') THEN ca.activity_id END) AS FLOAT) / COUNT(DISTINCT ca.activity_id) * 100
        ELSE 0 
    END as contact_success_rate,
    CASE 
        WHEN COUNT(DISTINCT pp.promise_id) > 0 
        THEN CAST(COUNT(DISTINCT CASE WHEN pp.status = 'KEPT' THEN pp.promise_id END) AS FLOAT) / COUNT(DISTINCT pp.promise_id) * 100
        ELSE 0 
    END as promise_keeping_rate
FROM customers c
LEFT JOIN collection_activities ca ON c.customer_id = ca.customer_id
LEFT JOIN payment_promises pp ON c.customer_id = pp.customer_id
GROUP BY c.customer_id, c.customer_name;