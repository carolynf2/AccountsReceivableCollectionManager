"""
Synthetic Data Generator for Accounts Receivable Collection Manager
Generates realistic AR data for testing and demonstration purposes
"""

import sqlite3
import random
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional
import json
import uuid


class ARDataGenerator:
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Initialize the database schema
        self._create_schema()
        
        # Customer data templates
        self.company_names = [
            "ABC Manufacturing Inc", "Tech Solutions LLC", "Global Services Corp",
            "Metro Construction", "Premier Industries", "Coastal Enterprises",
            "Advanced Systems", "Quality Products Inc", "Universal Trading",
            "Summit Corporation", "Elite Manufacturing", "Dynamic Solutions",
            "Precision Tools Ltd", "Innovation Labs", "Strategic Partners",
            "Excellence Group", "Prime Logistics", "Superior Products",
            "Modern Industries", "Future Technologies", "Capital Ventures",
            "Professional Services", "Integrated Solutions", "Reliable Supply",
            "Standard Equipment", "Custom Manufacturing"
        ]
        
        self.industries = [
            "Manufacturing", "Technology", "Healthcare", "Construction", "Retail",
            "Automotive", "Food & Beverage", "Logistics", "Professional Services",
            "Energy", "Agriculture", "Education", "Finance", "Real Estate"
        ]
        
        self.contact_names = [
            "John Smith", "Sarah Johnson", "Michael Brown", "Lisa Davis",
            "Robert Wilson", "Jennifer Garcia", "David Miller", "Karen Rodriguez",
            "Christopher Martinez", "Nancy Anderson", "Matthew Taylor", "Betty Thomas",
            "Daniel Jackson", "Helen White", "Paul Harris", "Sandra Martin",
            "Mark Thompson", "Donna Garcia", "Steven Martinez", "Carol Robinson"
        ]
        
        self.payment_methods = ["CHECK", "ACH", "WIRE", "CREDIT_CARD", "CASH"]
        self.customer_types = ["REGULAR", "VIP", "HIGH_RISK", "NEW"]
        
        # Invoice patterns for realistic scenarios
        self.invoice_patterns = [
            {"min_amount": 100, "max_amount": 2000, "probability": 0.4, "terms": 30},
            {"min_amount": 2000, "max_amount": 10000, "probability": 0.3, "terms": 45},
            {"min_amount": 10000, "max_amount": 50000, "probability": 0.2, "terms": 60},
            {"min_amount": 50000, "max_amount": 200000, "probability": 0.1, "terms": 90}
        ]
        
        # Payment behavior patterns
        self.payment_behaviors = [
            {"type": "EXCELLENT", "probability": 0.2, "avg_days_early": 5, "payment_rate": 0.98},
            {"type": "GOOD", "probability": 0.4, "avg_days_late": 3, "payment_rate": 0.95},
            {"type": "AVERAGE", "probability": 0.25, "avg_days_late": 10, "payment_rate": 0.88},
            {"type": "SLOW", "probability": 0.1, "avg_days_late": 25, "payment_rate": 0.75},
            {"type": "PROBLEM", "probability": 0.05, "avg_days_late": 60, "payment_rate": 0.60}
        ]
    
    def _create_schema(self):
        """Create database schema from SQL file"""
        with open("ar_database_schema.sql", "r") as f:
            schema_sql = f.read()
        
        # Execute each statement separately
        statements = schema_sql.split(';')
        for statement in statements:
            if statement.strip():
                try:
                    self.cursor.execute(statement)
                except sqlite3.Error as e:
                    if "already exists" not in str(e):
                        print(f"Error executing SQL: {e}")
        self.conn.commit()
    
    def generate_customers(self, num_customers: int = 50) -> List[int]:
        """Generate realistic customer data"""
        print(f"Generating {num_customers} customers...")
        
        customer_ids = []
        
        for i in range(num_customers):
            # Select company and contact info
            company_name = random.choice(self.company_names)
            primary_contact = random.choice(self.contact_names)
            
            # Generate customer code
            customer_code = f"CUST{i+1:04d}"
            
            # Contact information
            email = f"{primary_contact.lower().replace(' ', '.')}@{company_name.lower().replace(' ', '').replace('inc', '').replace('llc', '').replace('corp', '')}.com"
            phone = f"({random.randint(200, 999)}) {random.randint(200, 999)}-{random.randint(1000, 9999)}"
            
            # Address
            city = random.choice(["New York", "Los Angeles", "Chicago", "Houston", "Phoenix", 
                                "Philadelphia", "San Antonio", "San Diego", "Dallas", "San Jose"])
            state = random.choice(["NY", "CA", "IL", "TX", "AZ", "PA", "TX", "CA", "TX", "CA"])
            zip_code = f"{random.randint(10000, 99999)}"
            
            # Credit and payment terms
            credit_limit = random.choice([5000, 10000, 25000, 50000, 100000, 250000])
            payment_terms = random.choice([15, 30, 45, 60, 90])
            payment_method = random.choice(self.payment_methods)
            
            # Customer classification
            customer_type = random.choice(self.customer_types)
            industry = random.choice(self.industries)
            customer_since = datetime.now() - timedelta(days=random.randint(30, 1800))
            
            # Performance metrics (will be updated based on actual behavior)
            avg_days_to_pay = random.randint(25, 65)
            reliability_score = random.randint(30, 95)
            
            # Status flags
            is_active = random.choice([True, True, True, True, False])  # 80% active
            is_credit_hold = random.choice([False, False, False, False, True]) if is_active else False  # 20% if active
            
            # Collection priority
            if customer_type == "VIP":
                priority = "LOW"
            elif customer_type == "HIGH_RISK":
                priority = "HIGH"
            else:
                priority = random.choice(["NORMAL", "NORMAL", "NORMAL", "HIGH"])
            
            self.cursor.execute("""
                INSERT INTO customers (
                    customer_code, customer_name, company_name, primary_contact,
                    email, phone, city, state, zip_code,
                    credit_limit, payment_terms_days, preferred_payment_method,
                    customer_type, industry, customer_since,
                    avg_days_to_pay, payment_reliability_score,
                    is_active, is_credit_hold, collection_priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_code, primary_contact, company_name, primary_contact,
                email, phone, city, state, zip_code,
                credit_limit, payment_terms, payment_method,
                customer_type, industry, customer_since.date(),
                avg_days_to_pay, reliability_score,
                is_active, is_credit_hold, priority
            ))
            
            customer_ids.append(self.cursor.lastrowid)
        
        self.conn.commit()
        print(f"Created {len(customer_ids)} customers")
        return customer_ids
    
    def generate_invoices(self, customer_ids: List[int], months_back: int = 6, 
                         invoices_per_month: int = 100) -> List[int]:
        """Generate realistic invoice data across multiple months"""
        print(f"Generating invoices for {months_back} months...")
        
        invoice_ids = []
        invoice_counter = 1
        
        # Generate invoices for each month going back
        for month_offset in range(months_back):
            month_start = datetime.now().replace(day=1) - timedelta(days=30 * month_offset)
            
            for week in range(4):  # 4 weeks per month
                week_start = month_start + timedelta(days=7 * week)
                week_invoices = invoices_per_month // 4
                
                for _ in range(week_invoices):
                    customer_id = random.choice(customer_ids)
                    
                    # Get customer payment terms
                    self.cursor.execute(
                        "SELECT payment_terms_days, customer_type FROM customers WHERE customer_id = ?",
                        (customer_id,)
                    )
                    customer_info = self.cursor.fetchone()
                    payment_terms = customer_info[0] if customer_info else 30
                    customer_type = customer_info[1] if customer_info else "REGULAR"
                    
                    # Generate invoice details
                    invoice_date = week_start + timedelta(days=random.randint(0, 6))
                    due_date = invoice_date + timedelta(days=payment_terms)
                    
                    # Select invoice amount based on pattern probability
                    rand = random.random()
                    cumulative_prob = 0
                    selected_pattern = None
                    
                    for pattern in self.invoice_patterns:
                        cumulative_prob += pattern["probability"]
                        if rand <= cumulative_prob:
                            selected_pattern = pattern
                            break
                    
                    if not selected_pattern:
                        selected_pattern = self.invoice_patterns[0]
                    
                    invoice_amount = Decimal(str(random.uniform(
                        selected_pattern["min_amount"], 
                        selected_pattern["max_amount"]
                    ))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                    
                    # Calculate aging and status
                    days_past_due = max(0, (datetime.now().date() - due_date.date()).days)
                    aging_bucket = self._calculate_aging_bucket(days_past_due)
                    
                    # Determine collection status based on aging
                    collection_status = self._determine_collection_status(days_past_due, customer_type)
                    
                    # Calculate priority score
                    priority_score = self._calculate_priority_score(invoice_amount, days_past_due, customer_type)
                    
                    # Generate references
                    invoice_number = f"INV-{invoice_counter:06d}"
                    po_number = f"PO-{random.randint(10000, 99999)}" if random.random() > 0.3 else None
                    
                    self.cursor.execute("""
                        INSERT INTO invoices (
                            invoice_number, customer_id, invoice_date, due_date,
                            invoice_amount, outstanding_amount, days_past_due,
                            aging_bucket, collection_status, collection_priority_score,
                            purchase_order, status
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        invoice_number, customer_id, invoice_date.date(), due_date.date(),
                        invoice_amount, invoice_amount, days_past_due,
                        aging_bucket, collection_status, priority_score,
                        po_number, "OPEN"
                    ))
                    
                    invoice_ids.append(self.cursor.lastrowid)
                    invoice_counter += 1
        
        self.conn.commit()
        print(f"Created {len(invoice_ids)} invoices")
        return invoice_ids
    
    def generate_payments(self, customer_ids: List[int], invoice_ids: List[int]) -> List[int]:
        """Generate realistic payment data based on customer behavior patterns"""
        print("Generating payments...")
        
        payment_ids = []
        
        # Get all invoices that could have payments
        for invoice_id in invoice_ids:
            self.cursor.execute("""
                SELECT i.customer_id, i.invoice_amount, i.due_date, i.invoice_date, c.customer_type
                FROM invoices i
                JOIN customers c ON i.customer_id = c.customer_id
                WHERE i.invoice_id = ?
            """, (invoice_id,))
            
            invoice_info = self.cursor.fetchone()
            if not invoice_info:
                continue
            
            customer_id, invoice_amount, due_date_str, invoice_date_str, customer_type = invoice_info
            due_date = datetime.strptime(due_date_str, "%Y-%m-%d").date()
            invoice_date = datetime.strptime(invoice_date_str, "%Y-%m-%d").date()
            
            # Determine payment behavior based on customer type
            behavior = self._get_payment_behavior(customer_type)
            
            # Decide if this invoice gets paid
            if random.random() > behavior["payment_rate"]:
                continue  # This invoice remains unpaid
            
            # Calculate payment date
            if "avg_days_early" in behavior:
                payment_date = due_date - timedelta(days=random.randint(0, behavior["avg_days_early"]))
            else:
                payment_date = due_date + timedelta(days=random.randint(0, behavior["avg_days_late"] * 2))
            
            # Ensure payment date is not in the future
            payment_date = min(payment_date, datetime.now().date())
            
            # Decide on partial vs full payment
            if random.random() < 0.1:  # 10% chance of partial payment
                payment_amount = invoice_amount * Decimal(str(random.uniform(0.3, 0.8)))
                payment_amount = payment_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                payment_amount = invoice_amount
            
            # Get customer payment method
            self.cursor.execute(
                "SELECT preferred_payment_method FROM customers WHERE customer_id = ?",
                (customer_id,)
            )
            payment_method_result = self.cursor.fetchone()
            payment_method = payment_method_result[0] if payment_method_result else "CHECK"
            
            # Generate payment reference
            if payment_method == "CHECK":
                payment_ref = f"CHK-{random.randint(1000, 9999)}"
            elif payment_method == "ACH":
                payment_ref = f"ACH-{random.randint(100000, 999999)}"
            elif payment_method == "WIRE":
                payment_ref = f"WIRE-{random.randint(100000, 999999)}"
            else:
                payment_ref = f"TXN-{random.randint(100000, 999999)}"
            
            # Create payment record
            self.cursor.execute("""
                INSERT INTO payments (
                    customer_id, payment_date, payment_amount, payment_method,
                    payment_reference, received_by, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, payment_date, payment_amount, payment_method,
                payment_ref, "AR Department", "APPLIED"
            ))
            
            payment_id = self.cursor.lastrowid
            payment_ids.append(payment_id)
            
            # Create payment application
            self.cursor.execute("""
                INSERT INTO payment_applications (
                    payment_id, invoice_id, applied_amount, application_date
                ) VALUES (?, ?, ?, ?)
            """, (payment_id, invoice_id, payment_amount, payment_date))
            
            # Update invoice paid amount and outstanding amount
            self.cursor.execute("""
                UPDATE invoices 
                SET paid_amount = paid_amount + ?,
                    outstanding_amount = outstanding_amount - ?,
                    status = CASE 
                        WHEN outstanding_amount - ? <= 0.01 THEN 'PAID'
                        ELSE 'PARTIAL'
                    END,
                    updated_date = CURRENT_TIMESTAMP
                WHERE invoice_id = ?
            """, (payment_amount, payment_amount, payment_amount, invoice_id))
        
        self.conn.commit()
        print(f"Created {len(payment_ids)} payments")
        return payment_ids
    
    def generate_payment_promises(self, customer_ids: List[int], invoice_ids: List[int]) -> List[int]:
        """Generate payment promises for overdue invoices"""
        print("Generating payment promises...")
        
        promise_ids = []
        
        # Get overdue invoices
        self.cursor.execute("""
            SELECT invoice_id, customer_id, outstanding_amount, days_past_due
            FROM invoices
            WHERE outstanding_amount > 0 AND days_past_due > 0
            ORDER BY RANDOM()
            LIMIT 30
        """)
        
        overdue_invoices = self.cursor.fetchall()
        
        for invoice_id, customer_id, outstanding_amount, days_past_due in overdue_invoices:
            # 40% chance of having a payment promise
            if random.random() > 0.4:
                continue
            
            # Generate promise details
            promise_date = datetime.now().date() - timedelta(days=random.randint(1, 14))
            
            # Promise amount - could be partial
            if random.random() < 0.3:  # 30% chance of partial promise
                promised_amount = Decimal(str(outstanding_amount)) * Decimal(str(random.uniform(0.5, 0.9)))
                promised_amount = promised_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                promised_amount = Decimal(str(outstanding_amount))
            
            # Promised payment date
            promised_payment_date = promise_date + timedelta(days=random.randint(1, 30))
            
            # Determine if promise was kept
            if promised_payment_date <= datetime.now().date():
                # Promise date has passed, determine if kept
                keep_probability = 0.7  # 70% chance promises are kept
                if random.random() < keep_probability:
                    status = "KEPT"
                    actual_payment_date = promised_payment_date + timedelta(days=random.randint(-2, 5))
                    actual_payment_amount = promised_amount
                else:
                    status = "BROKEN"
                    actual_payment_date = None
                    actual_payment_amount = 0
            else:
                status = "ACTIVE"
                actual_payment_date = None
                actual_payment_amount = 0
            
            # Contact details
            contact_person = random.choice(self.contact_names)
            contact_method = random.choice(["PHONE", "EMAIL", "IN_PERSON"])
            
            # Follow-up information
            if status == "ACTIVE":
                follow_up_date = promised_payment_date + timedelta(days=1)
                follow_up_completed = False
                escalation_required = False
            elif status == "BROKEN":
                follow_up_date = promised_payment_date + timedelta(days=1)
                follow_up_completed = False
                escalation_required = True
            else:
                follow_up_date = None
                follow_up_completed = True
                escalation_required = False
            
            # Notes
            if status == "KEPT":
                notes = f"Customer honored payment promise. Paid ${actual_payment_amount} as promised."
            elif status == "BROKEN":
                notes = f"Customer failed to honor payment promise. No payment received by {promised_payment_date}."
            else:
                notes = f"Customer promised to pay ${promised_amount} by {promised_payment_date}."
            
            self.cursor.execute("""
                INSERT INTO payment_promises (
                    customer_id, invoice_id, promise_date, promised_amount, promised_payment_date,
                    status, actual_payment_date, actual_payment_amount,
                    follow_up_date, follow_up_completed, escalation_required,
                    contact_person, contact_method, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, invoice_id, promise_date, promised_amount, promised_payment_date,
                status, actual_payment_date, actual_payment_amount,
                follow_up_date, follow_up_completed, escalation_required,
                contact_person, contact_method, notes, "Collection Agent"
            ))
            
            promise_ids.append(self.cursor.lastrowid)
        
        self.conn.commit()
        print(f"Created {len(promise_ids)} payment promises")
        return promise_ids
    
    def generate_collection_activities(self, customer_ids: List[int], invoice_ids: List[int]) -> List[int]:
        """Generate collection activities and communications"""
        print("Generating collection activities...")
        
        activity_ids = []
        
        # Get customers with overdue invoices
        self.cursor.execute("""
            SELECT DISTINCT i.customer_id, i.invoice_id, i.outstanding_amount, i.days_past_due, i.collection_status
            FROM invoices i
            WHERE i.outstanding_amount > 0 AND i.days_past_due > 0
            ORDER BY i.days_past_due DESC
            LIMIT 50
        """)
        
        overdue_records = self.cursor.fetchall()
        
        activity_types = ["PHONE_CALL", "EMAIL", "LETTER", "STATEMENT"]
        activity_results = ["CONTACT_MADE", "NO_ANSWER", "BUSY", "PROMISE_MADE", "DISPUTE_RAISED"]
        collection_stages = ["FRIENDLY_REMINDER", "FIRST_NOTICE", "SECOND_NOTICE", "FINAL_NOTICE"]
        collectors = ["John Collector", "Sarah Collections", "Mike Recovery", "Lisa AR"]
        
        for customer_id, invoice_id, outstanding_amount, days_past_due, collection_status in overdue_records:
            # Generate 1-3 activities per overdue invoice
            num_activities = random.randint(1, min(3, days_past_due // 15 + 1))
            
            for activity_num in range(num_activities):
                # Activity date - spread over the past due period
                days_back = random.randint(1, min(days_past_due, 60))
                activity_date = datetime.now().date() - timedelta(days=days_back)
                
                # Activity details
                activity_type = random.choice(activity_types)
                activity_result = random.choice(activity_results)
                
                # Collection stage based on days past due
                if days_past_due <= 30:
                    collection_stage = "FRIENDLY_REMINDER"
                elif days_past_due <= 60:
                    collection_stage = "FIRST_NOTICE"
                elif days_past_due <= 90:
                    collection_stage = "SECOND_NOTICE"
                else:
                    collection_stage = "FINAL_NOTICE"
                
                # Contact details
                contact_person = random.choice(self.contact_names)
                duration = random.randint(2, 15) if activity_type == "PHONE_CALL" else None
                
                # Next action
                if activity_result == "PROMISE_MADE":
                    next_action = "FOLLOW_UP_PROMISE"
                    next_action_date = activity_date + timedelta(days=random.randint(1, 7))
                elif activity_result == "DISPUTE_RAISED":
                    next_action = "RESOLVE_DISPUTE"
                    next_action_date = activity_date + timedelta(days=random.randint(1, 3))
                elif activity_result == "NO_ANSWER":
                    next_action = "RETRY_CONTACT"
                    next_action_date = activity_date + timedelta(days=random.randint(1, 5))
                else:
                    next_action = "ESCALATE" if days_past_due > 60 else "FOLLOW_UP"
                    next_action_date = activity_date + timedelta(days=random.randint(7, 14))
                
                # Activity notes
                if activity_result == "CONTACT_MADE":
                    notes = f"Spoke with {contact_person}. Discussed outstanding balance of ${outstanding_amount}."
                elif activity_result == "PROMISE_MADE":
                    notes = f"Customer promised payment. Follow-up required."
                elif activity_result == "DISPUTE_RAISED":
                    notes = f"Customer disputes charges. Requires investigation."
                else:
                    notes = f"{activity_type} attempt. {activity_result}."
                
                collector = random.choice(collectors)
                
                self.cursor.execute("""
                    INSERT INTO collection_activities (
                        customer_id, invoice_id, activity_date, activity_type, activity_result,
                        contact_person, duration_minutes, next_action, next_action_date,
                        collection_stage, activity_notes, performed_by, assigned_to,
                        requires_follow_up
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    customer_id, invoice_id, activity_date, activity_type, activity_result,
                    contact_person, duration, next_action, next_action_date,
                    collection_stage, notes, collector, collector,
                    next_action_date > datetime.now().date()
                ))
                
                activity_ids.append(self.cursor.lastrowid)
        
        self.conn.commit()
        print(f"Created {len(activity_ids)} collection activities")
        return activity_ids
    
    def generate_disputes(self, invoice_ids: List[int]) -> List[int]:
        """Generate dispute records for some invoices"""
        print("Generating disputes...")
        
        dispute_ids = []
        dispute_reasons = [
            "QUALITY_ISSUE", "PRICING_ERROR", "DELIVERY_ISSUE", 
            "SERVICE_PROBLEM", "BILLING_ERROR"
        ]
        
        # Get some random invoices to dispute
        sample_invoices = random.sample(invoice_ids, min(10, len(invoice_ids)))
        
        for invoice_id in sample_invoices:
            # 15% chance of dispute
            if random.random() > 0.15:
                continue
            
            self.cursor.execute("""
                SELECT customer_id, outstanding_amount FROM invoices WHERE invoice_id = ?
            """, (invoice_id,))
            
            result = self.cursor.fetchone()
            if not result:
                continue
            
            customer_id, outstanding_amount = result
            
            # Dispute details
            dispute_date = datetime.now().date() - timedelta(days=random.randint(1, 30))
            disputed_amount = Decimal(str(outstanding_amount)) * Decimal(str(random.uniform(0.2, 1.0)))
            disputed_amount = disputed_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            dispute_reason = random.choice(dispute_reasons)
            
            # Status - some resolved, some open
            if random.random() < 0.6:  # 60% resolved
                status = "RESOLVED"
                resolution = random.choice(["CUSTOMER_CREDIT", "PARTIAL_CREDIT", "NO_ADJUSTMENT"])
                resolution_date = dispute_date + timedelta(days=random.randint(1, 14))
                
                if resolution == "CUSTOMER_CREDIT":
                    resolution_amount = disputed_amount
                elif resolution == "PARTIAL_CREDIT":
                    resolution_amount = disputed_amount * Decimal(str(random.uniform(0.3, 0.7)))
                    resolution_amount = resolution_amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                else:
                    resolution_amount = 0
            else:
                status = "OPEN"
                resolution = None
                resolution_date = None
                resolution_amount = 0
            
            # Assignment
            assigned_to = random.choice(["AR Manager", "Customer Service", "Sales Manager"])
            priority = random.choice(["NORMAL", "HIGH"]) if disputed_amount > 5000 else "NORMAL"
            
            description = f"Customer disputes {dispute_reason.lower().replace('_', ' ')} on invoice."
            
            self.cursor.execute("""
                INSERT INTO disputes (
                    customer_id, invoice_id, dispute_date, disputed_amount, dispute_reason,
                    dispute_description, status, resolution, resolution_amount, resolution_date,
                    assigned_to, priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, invoice_id, dispute_date, disputed_amount, dispute_reason,
                description, status, resolution, resolution_amount, resolution_date,
                assigned_to, priority
            ))
            
            dispute_ids.append(self.cursor.lastrowid)
        
        self.conn.commit()
        print(f"Created {len(dispute_ids)} disputes")
        return dispute_ids
    
    def generate_collection_workflows(self):
        """Generate collection workflow rules"""
        print("Generating collection workflows...")
        
        workflows = [
            {
                "name": "30-Day Friendly Reminder",
                "days_trigger": 30,
                "amount_threshold": 100,
                "action_type": "EMAIL_REMINDER",
                "escalation_days": 7,
                "assigned_to": "AR Team"
            },
            {
                "name": "45-Day Phone Call",
                "days_trigger": 45,
                "amount_threshold": 500,
                "action_type": "PHONE_CALL",
                "escalation_days": 10,
                "assigned_to": "Collection Specialist"
            },
            {
                "name": "60-Day Formal Letter",
                "days_trigger": 60,
                "amount_threshold": 1000,
                "action_type": "DUNNING_LETTER",
                "escalation_days": 15,
                "assigned_to": "Collection Manager"
            },
            {
                "name": "90-Day Final Notice",
                "days_trigger": 90,
                "amount_threshold": 0,
                "action_type": "FINAL_NOTICE",
                "escalation_days": 30,
                "assigned_to": "Collection Manager"
            },
            {
                "name": "120-Day Legal Referral",
                "days_trigger": 120,
                "amount_threshold": 2000,
                "action_type": "LEGAL_REFERRAL",
                "escalation_days": 0,
                "assigned_to": "Legal Department"
            }
        ]
        
        for i, workflow in enumerate(workflows):
            self.cursor.execute("""
                INSERT INTO collection_workflows (
                    workflow_name, days_past_due_trigger, amount_threshold,
                    action_type, escalation_days, assigned_to, execution_order
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                workflow["name"], workflow["days_trigger"], workflow["amount_threshold"],
                workflow["action_type"], workflow["escalation_days"], 
                workflow["assigned_to"], i + 1
            ))
        
        self.conn.commit()
        print(f"Created {len(workflows)} collection workflows")
    
    def update_aging_and_metrics(self):
        """Update aging buckets and calculate current metrics"""
        print("Updating aging buckets and metrics...")
        
        # Update aging buckets for all open invoices
        self.cursor.execute("""
            UPDATE invoices 
            SET days_past_due = CASE 
                WHEN julianday('now') - julianday(due_date) < 0 THEN 0
                ELSE CAST(julianday('now') - julianday(due_date) AS INTEGER)
            END,
            aging_bucket = CASE 
                WHEN julianday('now') - julianday(due_date) <= 0 THEN 'CURRENT'
                WHEN julianday('now') - julianday(due_date) <= 30 THEN '1-30'
                WHEN julianday('now') - julianday(due_date) <= 60 THEN '31-60'
                WHEN julianday('now') - julianday(due_date) <= 90 THEN '61-90'
                WHEN julianday('now') - julianday(due_date) <= 120 THEN '91-120'
                ELSE '120+'
            END
            WHERE outstanding_amount > 0
        """)
        
        # Calculate and insert current metrics
        today = datetime.now().date()
        
        # Get AR totals by aging bucket
        self.cursor.execute("""
            SELECT 
                SUM(CASE WHEN aging_bucket = 'CURRENT' THEN outstanding_amount ELSE 0 END) as current_ar,
                SUM(CASE WHEN aging_bucket = '1-30' THEN outstanding_amount ELSE 0 END) as ar_1_30,
                SUM(CASE WHEN aging_bucket = '31-60' THEN outstanding_amount ELSE 0 END) as ar_31_60,
                SUM(CASE WHEN aging_bucket = '61-90' THEN outstanding_amount ELSE 0 END) as ar_61_90,
                SUM(CASE WHEN aging_bucket = '91-120' THEN outstanding_amount ELSE 0 END) as ar_91_120,
                SUM(CASE WHEN aging_bucket = '120+' THEN outstanding_amount ELSE 0 END) as ar_120_plus,
                SUM(outstanding_amount) as total_ar,
                SUM(CASE WHEN days_past_due > 0 THEN outstanding_amount ELSE 0 END) as past_due_ar
            FROM invoices
            WHERE outstanding_amount > 0
        """)
        
        ar_data = self.cursor.fetchone()
        
        # Get activity counts
        self.cursor.execute("""
            SELECT 
                COUNT(CASE WHEN activity_type = 'PHONE_CALL' THEN 1 END) as calls,
                COUNT(CASE WHEN activity_type = 'EMAIL' THEN 1 END) as emails,
                COUNT(CASE WHEN activity_type = 'LETTER' THEN 1 END) as letters
            FROM collection_activities
            WHERE activity_date = ?
        """, (today,))
        
        activity_data = self.cursor.fetchone()
        
        # Get promise counts
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_promises,
                COUNT(CASE WHEN status = 'KEPT' THEN 1 END) as kept_promises
            FROM payment_promises
            WHERE promise_date >= ?
        """, (today - timedelta(days=30),))
        
        promise_data = self.cursor.fetchone()
        
        # Calculate DSO (simplified)
        dso = 45.5  # Placeholder calculation
        
        # Insert metrics record
        self.cursor.execute("""
            INSERT INTO collection_metrics (
                metric_date, period_start_date, period_end_date, metric_type,
                total_ar_balance, current_ar, past_due_ar,
                ar_0_30_days, ar_31_60_days, ar_61_90_days, ar_91_120_days, ar_over_120_days,
                days_sales_outstanding, collection_calls_made, emails_sent, letters_sent,
                promises_received, promises_kept
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            today, today, today, "DAILY",
            ar_data[6], ar_data[0], ar_data[7],  # total, current, past_due
            ar_data[1], ar_data[2], ar_data[3], ar_data[4], ar_data[5],  # aging buckets
            dso, activity_data[0], activity_data[1], activity_data[2],  # activities
            promise_data[0], promise_data[1]  # promises
        ))
        
        self.conn.commit()
        print("Updated aging and metrics")
    
    def _calculate_aging_bucket(self, days_past_due: int) -> str:
        """Calculate aging bucket based on days past due"""
        if days_past_due <= 0:
            return "CURRENT"
        elif days_past_due <= 30:
            return "1-30"
        elif days_past_due <= 60:
            return "31-60"
        elif days_past_due <= 90:
            return "61-90"
        elif days_past_due <= 120:
            return "91-120"
        else:
            return "120+"
    
    def _determine_collection_status(self, days_past_due: int, customer_type: str) -> str:
        """Determine collection status based on aging and customer type"""
        if days_past_due <= 0:
            return "NORMAL"
        elif days_past_due <= 30:
            return "FIRST_NOTICE"
        elif days_past_due <= 60:
            return "SECOND_NOTICE"
        elif days_past_due <= 90:
            return "FINAL_NOTICE"
        else:
            return "COLLECTIONS"
    
    def _calculate_priority_score(self, invoice_amount: Decimal, days_past_due: int, customer_type: str) -> int:
        """Calculate collection priority score (0-100)"""
        score = 50  # Base score
        
        # Amount factor (0-25 points)
        if invoice_amount >= 50000:
            score += 25
        elif invoice_amount >= 10000:
            score += 15
        elif invoice_amount >= 5000:
            score += 10
        elif invoice_amount >= 1000:
            score += 5
        
        # Days past due factor (0-30 points)
        if days_past_due >= 120:
            score += 30
        elif days_past_due >= 90:
            score += 25
        elif days_past_due >= 60:
            score += 20
        elif days_past_due >= 30:
            score += 15
        elif days_past_due > 0:
            score += 5
        
        # Customer type factor
        if customer_type == "HIGH_RISK":
            score += 15
        elif customer_type == "VIP":
            score -= 10
        
        return min(100, max(0, score))
    
    def _get_payment_behavior(self, customer_type: str) -> Dict:
        """Get payment behavior pattern based on customer type"""
        if customer_type == "VIP":
            return {"payment_rate": 0.98, "avg_days_early": 3}
        elif customer_type == "HIGH_RISK":
            return {"payment_rate": 0.60, "avg_days_late": 45}
        elif customer_type == "NEW":
            return {"payment_rate": 0.85, "avg_days_late": 15}
        else:
            # Return weighted random behavior for regular customers
            return random.choice(self.payment_behaviors)
    
    def generate_sample_data(self, num_customers: int = 50, months_back: int = 6):
        """Generate complete sample dataset"""
        print("Generating complete AR collection sample dataset...")
        
        # Generate master data
        customer_ids = self.generate_customers(num_customers)
        
        # Generate transactional data
        invoice_ids = self.generate_invoices(customer_ids, months_back)
        payment_ids = self.generate_payments(customer_ids, invoice_ids)
        promise_ids = self.generate_payment_promises(customer_ids, invoice_ids)
        activity_ids = self.generate_collection_activities(customer_ids, invoice_ids)
        dispute_ids = self.generate_disputes(invoice_ids)
        
        # Generate workflow rules
        self.generate_collection_workflows()
        
        # Update aging and calculate metrics
        self.update_aging_and_metrics()
        
        print("\nSample data generation complete!")
        print(f"Generated:")
        print(f"  - {len(customer_ids)} customers")
        print(f"  - {len(invoice_ids)} invoices")
        print(f"  - {len(payment_ids)} payments")
        print(f"  - {len(promise_ids)} payment promises")
        print(f"  - {len(activity_ids)} collection activities")
        print(f"  - {len(dispute_ids)} disputes")
        print(f"  - Collection workflows and metrics")
    
    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == "__main__":
    generator = ARDataGenerator()
    try:
        generator.generate_sample_data()
        print("\nAR Collection Manager database ready!")
        print("Run 'python ar_main.py' to start the collection management system")
    finally:
        generator.close()