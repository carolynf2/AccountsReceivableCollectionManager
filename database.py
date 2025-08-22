"""
Database connection and management for AR Collection Manager
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Any, Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database connections and operations"""
    
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.connection = None
        self.initialize_database()
    
    def initialize_database(self):
        """Initialize database with schema"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Enable column access by name
            
            # Check if database is already initialized
            cursor = self.connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
            if cursor.fetchone():
                logger.info("Database already exists")
                return
            
            # Read and execute schema
            schema_path = os.path.join(os.path.dirname(__file__), 'database_schema.sql')
            if os.path.exists(schema_path):
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                    self.connection.executescript(schema_sql)
                    self.connection.commit()
                    logger.info("Database initialized successfully")
            else:
                logger.error("Schema file not found")
                
        except Exception as e:
            logger.error(f"Database initialization error: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute a SELECT query and return results as list of dictionaries"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            columns = [description[0] for description in cursor.description]
            results = []
            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))
            return results
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return affected rows"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.rowcount
        except Exception as e:
            logger.error(f"Update execution error: {e}")
            self.connection.rollback()
            raise
    
    def execute_insert(self, query: str, params: tuple = ()) -> int:
        """Execute an INSERT query and return the last inserted row ID"""
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, params)
            self.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Insert execution error: {e}")
            self.connection.rollback()
            raise
    
    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")

class CustomerManager:
    """Manages customer-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_customer(self, customer_data: Dict[str, Any]) -> int:
        """Add a new customer"""
        query = """
        INSERT INTO customers (
            customer_name, company_name, email, phone, address,
            credit_limit, payment_terms, risk_rating, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            customer_data.get('customer_name'),
            customer_data.get('company_name'),
            customer_data.get('email'),
            customer_data.get('phone'),
            customer_data.get('address'),
            customer_data.get('credit_limit', 0),
            customer_data.get('payment_terms', 30),
            customer_data.get('risk_rating', 'LOW'),
            customer_data.get('notes')
        )
        return self.db.execute_insert(query, params)
    
    def get_customer(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Get customer by ID"""
        query = "SELECT * FROM customers WHERE customer_id = ?"
        results = self.db.execute_query(query, (customer_id,))
        return results[0] if results else None
    
    def get_all_customers(self) -> List[Dict[str, Any]]:
        """Get all customers"""
        query = "SELECT * FROM customers ORDER BY customer_name"
        return self.db.execute_query(query)
    
    def update_customer(self, customer_id: int, customer_data: Dict[str, Any]) -> int:
        """Update customer information"""
        set_clauses = []
        params = []
        
        for field in ['customer_name', 'company_name', 'email', 'phone', 'address',
                     'credit_limit', 'payment_terms', 'risk_rating', 'notes']:
            if field in customer_data:
                set_clauses.append(f"{field} = ?")
                params.append(customer_data[field])
        
        if not set_clauses:
            return 0
        
        query = f"UPDATE customers SET {', '.join(set_clauses)} WHERE customer_id = ?"
        params.append(customer_id)
        
        return self.db.execute_update(query, tuple(params))
    
    def update_last_contact(self, customer_id: int, contact_date: datetime = None):
        """Update last contact date for customer"""
        if contact_date is None:
            contact_date = datetime.now()
        
        query = "UPDATE customers SET last_contact_date = ? WHERE customer_id = ?"
        return self.db.execute_update(query, (contact_date, customer_id))
    
    def get_customer_summary(self) -> List[Dict[str, Any]]:
        """Get customer summary with outstanding balances"""
        query = "SELECT * FROM customer_summary ORDER BY overdue_balance DESC"
        return self.db.execute_query(query)

class InvoiceManager:
    """Manages invoice-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_invoice(self, invoice_data: Dict[str, Any]) -> int:
        """Add a new invoice"""
        query = """
        INSERT INTO invoices (
            customer_id, invoice_number, invoice_date, due_date,
            amount, balance, status, description
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            invoice_data['customer_id'],
            invoice_data['invoice_number'],
            invoice_data['invoice_date'],
            invoice_data['due_date'],
            invoice_data['amount'],
            invoice_data.get('balance', invoice_data['amount']),
            invoice_data.get('status', 'OPEN'),
            invoice_data.get('description')
        )
        return self.db.execute_insert(query, params)
    
    def get_invoice(self, invoice_id: int) -> Optional[Dict[str, Any]]:
        """Get invoice by ID"""
        query = """
        SELECT i.*, c.customer_name, c.company_name
        FROM invoices i
        JOIN customers c ON i.customer_id = c.customer_id
        WHERE i.invoice_id = ?
        """
        results = self.db.execute_query(query, (invoice_id,))
        return results[0] if results else None
    
    def get_customer_invoices(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all invoices for a customer"""
        query = """
        SELECT * FROM invoices 
        WHERE customer_id = ? 
        ORDER BY due_date DESC
        """
        return self.db.execute_query(query, (customer_id,))
    
    def get_overdue_invoices(self) -> List[Dict[str, Any]]:
        """Get all overdue invoices"""
        query = "SELECT * FROM overdue_invoices ORDER BY days_overdue DESC, balance DESC"
        return self.db.execute_query(query)
    
    def update_invoice_balance(self, invoice_id: int, new_balance: float) -> int:
        """Update invoice balance"""
        # Determine new status based on balance
        if new_balance <= 0:
            status = 'PAID'
        elif new_balance < self.get_invoice(invoice_id)['amount']:
            status = 'PARTIAL'
        else:
            status = 'OPEN'
        
        query = "UPDATE invoices SET balance = ?, status = ? WHERE invoice_id = ?"
        return self.db.execute_update(query, (new_balance, status, invoice_id))
    
    def get_aging_report(self) -> Dict[str, Any]:
        """Generate aging report"""
        query = """
        SELECT 
            COUNT(*) as total_invoices,
            SUM(balance) as total_balance,
            SUM(CASE WHEN days_overdue <= 0 THEN balance ELSE 0 END) as current_balance,
            SUM(CASE WHEN days_overdue BETWEEN 1 AND 30 THEN balance ELSE 0 END) as days_1_30,
            SUM(CASE WHEN days_overdue BETWEEN 31 AND 60 THEN balance ELSE 0 END) as days_31_60,
            SUM(CASE WHEN days_overdue BETWEEN 61 AND 90 THEN balance ELSE 0 END) as days_61_90,
            SUM(CASE WHEN days_overdue > 90 THEN balance ELSE 0 END) as days_over_90
        FROM overdue_invoices
        """
        results = self.db.execute_query(query)
        return results[0] if results else {}

class PaymentManager:
    """Manages payment-related database operations"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_payment(self, payment_data: Dict[str, Any]) -> int:
        """Add a new payment"""
        query = """
        INSERT INTO payments (
            invoice_id, payment_date, amount, payment_method,
            reference_number, notes
        ) VALUES (?, ?, ?, ?, ?, ?)
        """
        params = (
            payment_data['invoice_id'],
            payment_data['payment_date'],
            payment_data['amount'],
            payment_data.get('payment_method'),
            payment_data.get('reference_number'),
            payment_data.get('notes')
        )
        
        payment_id = self.db.execute_insert(query, params)
        
        # Update invoice balance
        invoice_manager = InvoiceManager(self.db)
        invoice = invoice_manager.get_invoice(payment_data['invoice_id'])
        if invoice:
            new_balance = invoice['balance'] - payment_data['amount']
            invoice_manager.update_invoice_balance(payment_data['invoice_id'], new_balance)
        
        return payment_id
    
    def get_invoice_payments(self, invoice_id: int) -> List[Dict[str, Any]]:
        """Get all payments for an invoice"""
        query = """
        SELECT * FROM payments 
        WHERE invoice_id = ? 
        ORDER BY payment_date DESC
        """
        return self.db.execute_query(query, (invoice_id,))
    
    def get_customer_payments(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all payments for a customer"""
        query = """
        SELECT p.*, i.invoice_number
        FROM payments p
        JOIN invoices i ON p.invoice_id = i.invoice_id
        WHERE i.customer_id = ?
        ORDER BY p.payment_date DESC
        """
        return self.db.execute_query(query, (customer_id,))

class CollectionActivityManager:
    """Manages collection activity tracking"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_activity(self, activity_data: Dict[str, Any]) -> int:
        """Add a new collection activity"""
        query = """
        INSERT INTO collection_activities (
            customer_id, invoice_id, activity_type, collector_name,
            outcome, notes, follow_up_date
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        params = (
            activity_data['customer_id'],
            activity_data.get('invoice_id'),
            activity_data['activity_type'],
            activity_data.get('collector_name'),
            activity_data.get('outcome'),
            activity_data.get('notes'),
            activity_data.get('follow_up_date')
        )
        
        activity_id = self.db.execute_insert(query, params)
        
        # Update customer last contact date
        customer_manager = CustomerManager(self.db)
        customer_manager.update_last_contact(activity_data['customer_id'])
        
        return activity_id
    
    def get_customer_activities(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all activities for a customer"""
        query = """
        SELECT ca.*, i.invoice_number
        FROM collection_activities ca
        LEFT JOIN invoices i ON ca.invoice_id = i.invoice_id
        WHERE ca.customer_id = ?
        ORDER BY ca.activity_date DESC
        """
        return self.db.execute_query(query, (customer_id,))
    
    def get_follow_up_activities(self, follow_up_date: date = None) -> List[Dict[str, Any]]:
        """Get activities that need follow-up"""
        if follow_up_date is None:
            follow_up_date = date.today()
        
        query = """
        SELECT ca.*, c.customer_name, c.company_name
        FROM collection_activities ca
        JOIN customers c ON ca.customer_id = c.customer_id
        WHERE ca.follow_up_date <= ?
        ORDER BY ca.follow_up_date
        """
        return self.db.execute_query(query, (follow_up_date,))

class PaymentPromiseManager:
    """Manages payment promises tracking"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def add_promise(self, promise_data: Dict[str, Any]) -> int:
        """Add a new payment promise"""
        query = """
        INSERT INTO payment_promises (
            customer_id, invoice_id, promise_date, promised_amount, notes
        ) VALUES (?, ?, ?, ?, ?)
        """
        params = (
            promise_data['customer_id'],
            promise_data.get('invoice_id'),
            promise_data['promise_date'],
            promise_data['promised_amount'],
            promise_data.get('notes')
        )
        return self.db.execute_insert(query, params)
    
    def update_promise_status(self, promise_id: int, status: str, 
                            actual_payment_date: date = None, 
                            actual_amount: float = None) -> int:
        """Update payment promise status"""
        query = """
        UPDATE payment_promises 
        SET status = ?, actual_payment_date = ?, actual_amount = ?
        WHERE promise_id = ?
        """
        return self.db.execute_update(query, (status, actual_payment_date, actual_amount, promise_id))
    
    def get_pending_promises(self) -> List[Dict[str, Any]]:
        """Get all pending payment promises"""
        query = """
        SELECT pp.*, c.customer_name, c.company_name, i.invoice_number
        FROM payment_promises pp
        JOIN customers c ON pp.customer_id = c.customer_id
        LEFT JOIN invoices i ON pp.invoice_id = i.invoice_id
        WHERE pp.status = 'PENDING'
        ORDER BY pp.promise_date
        """
        return self.db.execute_query(query)
    
    def get_overdue_promises(self) -> List[Dict[str, Any]]:
        """Get overdue payment promises"""
        query = """
        SELECT pp.*, c.customer_name, c.company_name, i.invoice_number
        FROM payment_promises pp
        JOIN customers c ON pp.customer_id = c.customer_id
        LEFT JOIN invoices i ON pp.invoice_id = i.invoice_id
        WHERE pp.status = 'PENDING' AND pp.promise_date < date('now')
        ORDER BY pp.promise_date
        """
        return self.db.execute_query(query)
    
    def get_customer_promises(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get all promises for a customer"""
        query = """
        SELECT pp.*, i.invoice_number
        FROM payment_promises pp
        LEFT JOIN invoices i ON pp.invoice_id = i.invoice_id
        WHERE pp.customer_id = ?
        ORDER BY pp.promise_date DESC
        """
        return self.db.execute_query(query, (customer_id,))