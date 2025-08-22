"""
Payment Promise Tracking and Follow-up System
Comprehensive management of customer payment commitments and automated follow-up
"""

import sqlite3
import json
from datetime import datetime, timedelta, date
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Dict, Tuple, Optional, Any
import logging
from enum import Enum


class PromiseStatus(Enum):
    ACTIVE = "ACTIVE"
    KEPT = "KEPT"
    BROKEN = "BROKEN"
    PARTIALLY_KEPT = "PARTIALLY_KEPT"
    CANCELLED = "CANCELLED"


class FollowUpPriority(Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    URGENT = "URGENT"


class PaymentPromiseTracker:
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.logger = logging.getLogger(__name__)
        
        # Promise tolerance settings
        self.tolerance_settings = {
            'partial_payment_threshold': 0.1,  # 10% of promised amount
            'grace_period_days': 2,             # Days past due before marking broken
            'escalation_threshold': 3,          # Broken promises before escalation
            'follow_up_lead_time': 1            # Days before due date to follow up
        }
    
    def create_payment_promise(self, customer_id: int, promised_amount: float,
                             promised_payment_date: str, invoice_id: int = None,
                             contact_person: str = "", contact_method: str = "PHONE",
                             notes: str = "", created_by: str = "Collection Agent") -> Dict:
        """Create a new payment promise record"""
        self.logger.info(f"Creating payment promise for customer {customer_id}")
        
        try:
            # Validate inputs
            if promised_amount <= 0:
                return {"success": False, "error": "Promised amount must be positive"}
            
            # Parse and validate date
            try:
                promise_date = datetime.strptime(promised_payment_date, "%Y-%m-%d").date()
            except ValueError:
                return {"success": False, "error": "Invalid date format. Use YYYY-MM-DD"}
            
            if promise_date <= datetime.now().date():
                return {"success": False, "error": "Promise date must be in the future"}
            
            # Validate customer exists
            self.cursor.execute("SELECT customer_name FROM customers WHERE customer_id = ?", (customer_id,))
            customer_result = self.cursor.fetchone()
            if not customer_result:
                return {"success": False, "error": "Customer not found"}
            
            # Validate invoice if provided
            if invoice_id:
                self.cursor.execute("""
                    SELECT outstanding_amount FROM invoices 
                    WHERE invoice_id = ? AND customer_id = ? AND outstanding_amount > 0
                """, (invoice_id, customer_id))
                invoice_result = self.cursor.fetchone()
                if not invoice_result:
                    return {"success": False, "error": "Invoice not found or already paid"}
                
                outstanding_amount = float(invoice_result[0])
                if promised_amount > outstanding_amount:
                    return {"success": False, "error": f"Promised amount exceeds outstanding balance of ${outstanding_amount:,.2f}"}
            
            # Calculate follow-up date
            follow_up_date = promise_date - timedelta(days=self.tolerance_settings['follow_up_lead_time'])
            
            # Insert promise record
            self.cursor.execute("""
                INSERT INTO payment_promises (
                    customer_id, invoice_id, promise_date, promised_amount, promised_payment_date,
                    status, follow_up_date, follow_up_completed, escalation_required,
                    contact_person, contact_method, notes, created_by
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id, invoice_id, datetime.now().date(), promised_amount, promise_date,
                PromiseStatus.ACTIVE.value, follow_up_date, False, False,
                contact_person, contact_method, notes, created_by
            ))
            
            promise_id = self.cursor.lastrowid
            
            # Create follow-up activity
            self._create_follow_up_activity(promise_id, customer_id, invoice_id, follow_up_date)
            
            # Update invoice collection status if specific invoice
            if invoice_id:
                self.cursor.execute("""
                    UPDATE invoices 
                    SET collection_status = 'PROMISE_RECEIVED',
                        next_collection_action_date = ?,
                        updated_date = CURRENT_TIMESTAMP
                    WHERE invoice_id = ?
                """, (follow_up_date, invoice_id))
            
            self.conn.commit()
            
            return {
                "success": True,
                "promise_id": promise_id,
                "customer_name": customer_result[0],
                "promised_amount": promised_amount,
                "promised_date": promise_date.isoformat(),
                "follow_up_date": follow_up_date.isoformat(),
                "message": f"Payment promise created for ${promised_amount:,.2f} due {promise_date}"
            }
        
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error creating payment promise: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_follow_up_activity(self, promise_id: int, customer_id: int, 
                                 invoice_id: int, follow_up_date: date):
        """Create a follow-up activity for the promise"""
        self.cursor.execute("""
            INSERT INTO collection_activities (
                customer_id, invoice_id, activity_date, activity_type, activity_result,
                next_action, next_action_date, collection_stage, activity_notes,
                performed_by, assigned_to, requires_follow_up, follow_up_priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id, invoice_id, datetime.now().date(), "PROMISE_FOLLOW_UP", "SCHEDULED",
            "VERIFY_PROMISE", follow_up_date, "PROMISE_TRACKING",
            f"Follow-up scheduled for payment promise {promise_id}",
            "System", "Collection Agent", True, FollowUpPriority.NORMAL.value
        ))
    
    def update_promise_status(self, promise_id: int, new_status: PromiseStatus,
                            actual_payment_amount: float = 0, actual_payment_date: str = None,
                            notes: str = "") -> Dict:
        """Update the status of a payment promise"""
        self.logger.info(f"Updating promise {promise_id} to status {new_status.value}")
        
        try:
            # Get current promise details
            self.cursor.execute("""
                SELECT customer_id, invoice_id, promised_amount, promised_payment_date, status
                FROM payment_promises
                WHERE promise_id = ?
            """, (promise_id,))
            
            result = self.cursor.fetchone()
            if not result:
                return {"success": False, "error": "Payment promise not found"}
            
            customer_id, invoice_id, promised_amount, promised_date_str, current_status = result
            promised_amount = float(promised_amount)
            
            # Parse actual payment date if provided
            payment_date = None
            if actual_payment_date:
                try:
                    payment_date = datetime.strptime(actual_payment_date, "%Y-%m-%d").date()
                except ValueError:
                    return {"success": False, "error": "Invalid payment date format. Use YYYY-MM-DD"}
            
            # Validate status transition
            if current_status in [PromiseStatus.KEPT.value, PromiseStatus.BROKEN.value, PromiseStatus.CANCELLED.value]:
                return {"success": False, "error": f"Cannot update promise with status {current_status}"}
            
            # Validate amounts for KEPT/PARTIALLY_KEPT status
            if new_status in [PromiseStatus.KEPT, PromiseStatus.PARTIALLY_KEPT]:
                if actual_payment_amount <= 0:
                    return {"success": False, "error": "Actual payment amount required for KEPT/PARTIALLY_KEPT status"}
                
                if new_status == PromiseStatus.KEPT and abs(actual_payment_amount - promised_amount) > promised_amount * 0.01:
                    # If payment is within 1% of promised amount, consider it kept
                    if actual_payment_amount < promised_amount * 0.9:
                        new_status = PromiseStatus.PARTIALLY_KEPT
            
            # Determine escalation requirement
            escalation_required = False
            if new_status == PromiseStatus.BROKEN:
                # Check if this customer has multiple broken promises
                self.cursor.execute("""
                    SELECT COUNT(*) FROM payment_promises
                    WHERE customer_id = ? AND status = 'BROKEN'
                    AND promise_date >= date('now', '-90 days')
                """, (customer_id,))
                broken_count = self.cursor.fetchone()[0]
                
                if broken_count >= self.tolerance_settings['escalation_threshold'] - 1:  # -1 because we're about to add another
                    escalation_required = True
            
            # Update promise record
            self.cursor.execute("""
                UPDATE payment_promises
                SET status = ?, actual_payment_date = ?, actual_payment_amount = ?,
                    escalation_required = ?, follow_up_completed = TRUE,
                    notes = CASE 
                        WHEN notes IS NULL OR notes = '' THEN ?
                        ELSE notes || '; ' || ?
                    END,
                    updated_date = CURRENT_TIMESTAMP
                WHERE promise_id = ?
            """, (
                new_status.value, payment_date, actual_payment_amount,
                escalation_required, notes, notes, promise_id
            ))
            
            # Update invoice status if applicable
            if invoice_id:
                if new_status == PromiseStatus.KEPT:
                    next_action_date = datetime.now().date() + timedelta(days=30)  # Standard follow-up
                    collection_status = "PAYMENT_RECEIVED"
                elif new_status == PromiseStatus.BROKEN:
                    next_action_date = datetime.now().date() + timedelta(days=1)  # Immediate follow-up
                    collection_status = "BROKEN_PROMISE"
                elif new_status == PromiseStatus.PARTIALLY_KEPT:
                    next_action_date = datetime.now().date() + timedelta(days=7)  # Quick follow-up for balance
                    collection_status = "PARTIAL_PAYMENT"
                else:
                    next_action_date = None
                    collection_status = None
                
                if collection_status:
                    self.cursor.execute("""
                        UPDATE invoices
                        SET collection_status = ?,
                            next_collection_action_date = ?,
                            updated_date = CURRENT_TIMESTAMP
                        WHERE invoice_id = ?
                    """, (collection_status, next_action_date, invoice_id))
            
            # Create activity record for status change
            self._create_promise_activity(promise_id, customer_id, invoice_id, new_status, 
                                        actual_payment_amount, escalation_required)
            
            self.conn.commit()
            
            return {
                "success": True,
                "promise_id": promise_id,
                "old_status": current_status,
                "new_status": new_status.value,
                "escalation_required": escalation_required,
                "message": f"Promise status updated to {new_status.value}"
            }
        
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error updating promise status: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def _create_promise_activity(self, promise_id: int, customer_id: int, invoice_id: int,
                               status: PromiseStatus, payment_amount: float, escalation_required: bool):
        """Create activity record for promise status change"""
        if status == PromiseStatus.KEPT:
            activity_result = "PROMISE_KEPT"
            notes = f"Customer honored payment promise. Received ${payment_amount:,.2f}"
        elif status == PromiseStatus.BROKEN:
            activity_result = "PROMISE_BROKEN"
            notes = f"Customer failed to honor payment promise"
        elif status == PromiseStatus.PARTIALLY_KEPT:
            activity_result = "PARTIAL_PAYMENT"
            notes = f"Customer made partial payment of ${payment_amount:,.2f}"
        else:
            activity_result = "PROMISE_CANCELLED"
            notes = f"Payment promise cancelled"
        
        next_action = "ESCALATE" if escalation_required else "FOLLOW_UP"
        priority = FollowUpPriority.URGENT.value if escalation_required else FollowUpPriority.NORMAL.value
        
        self.cursor.execute("""
            INSERT INTO collection_activities (
                customer_id, invoice_id, activity_date, activity_type, activity_result,
                next_action, collection_stage, activity_notes, performed_by,
                assigned_to, requires_follow_up, follow_up_priority
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_id, invoice_id, datetime.now().date(), "PROMISE_UPDATE", activity_result,
            next_action, "PROMISE_TRACKING", notes, "System", "Collection Agent",
            escalation_required, priority
        ))
    
    def check_promise_due_dates(self, days_ahead: int = 3) -> List[Dict]:
        """Check for promises coming due within specified days"""
        self.logger.info(f"Checking promises due within {days_ahead} days")
        
        check_date = datetime.now().date() + timedelta(days=days_ahead)
        
        self.cursor.execute("""
            SELECT pp.promise_id, pp.customer_id, pp.invoice_id, pp.promised_amount,
                   pp.promised_payment_date, pp.contact_person, pp.contact_method,
                   pp.notes, c.customer_name, c.company_name, c.phone, c.email,
                   i.invoice_number, i.outstanding_amount
            FROM payment_promises pp
            JOIN customers c ON pp.customer_id = c.customer_id
            LEFT JOIN invoices i ON pp.invoice_id = i.invoice_id
            WHERE pp.status = 'ACTIVE' 
                AND pp.promised_payment_date <= ?
                AND pp.follow_up_completed = FALSE
            ORDER BY pp.promised_payment_date, pp.promised_amount DESC
        """, (check_date,))
        
        due_promises = []
        for row in self.cursor.fetchall():
            promise_data = {
                'promise_id': row[0],
                'customer_id': row[1],
                'invoice_id': row[2],
                'promised_amount': float(row[3]),
                'promised_payment_date': row[4],
                'contact_person': row[5],
                'contact_method': row[6],
                'promise_notes': row[7],
                'customer_name': row[8],
                'company_name': row[9],
                'phone': row[10],
                'email': row[11],
                'invoice_number': row[12],
                'outstanding_amount': float(row[13]) if row[13] else 0,
                'days_until_due': (datetime.strptime(row[4], "%Y-%m-%d").date() - datetime.now().date()).days,
                'is_overdue': datetime.strptime(row[4], "%Y-%m-%d").date() < datetime.now().date(),
                'follow_up_priority': self._calculate_follow_up_priority(row[0], row[1], row[3])
            }
            due_promises.append(promise_data)
        
        return due_promises
    
    def _calculate_follow_up_priority(self, promise_id: int, customer_id: int, promised_amount: float) -> str:
        """Calculate follow-up priority for a promise"""
        # Base priority on amount
        if promised_amount >= 50000:
            priority = FollowUpPriority.URGENT
        elif promised_amount >= 10000:
            priority = FollowUpPriority.HIGH
        else:
            priority = FollowUpPriority.NORMAL
        
        # Check customer's promise history
        self.cursor.execute("""
            SELECT COUNT(*) as total_promises,
                   COUNT(CASE WHEN status = 'BROKEN' THEN 1 END) as broken_promises
            FROM payment_promises
            WHERE customer_id = ? AND promise_date >= date('now', '-180 days')
        """, (customer_id,))
        
        history = self.cursor.fetchone()
        if history and history[0] > 0:
            broken_rate = history[1] / history[0]
            if broken_rate > 0.5:  # More than 50% broken promises
                priority = FollowUpPriority.URGENT
            elif broken_rate > 0.25:  # More than 25% broken promises
                if priority == FollowUpPriority.NORMAL:
                    priority = FollowUpPriority.HIGH
        
        return priority.value
    
    def process_overdue_promises(self) -> Dict:
        """Process promises that are past due and mark them as broken if no payment received"""
        self.logger.info("Processing overdue payment promises")
        
        grace_date = datetime.now().date() - timedelta(days=self.tolerance_settings['grace_period_days'])
        
        # Get overdue active promises
        self.cursor.execute("""
            SELECT promise_id, customer_id, invoice_id, promised_amount, promised_payment_date
            FROM payment_promises
            WHERE status = 'ACTIVE' AND promised_payment_date < ?
        """, (grace_date,))
        
        overdue_promises = self.cursor.fetchall()
        
        processed_count = 0
        escalated_count = 0
        results = []
        
        for promise_id, customer_id, invoice_id, promised_amount, promised_date in overdue_promises:
            # Check if payment was received for this invoice around the promise date
            payment_received = False
            actual_amount = 0
            
            if invoice_id:
                # Check for payments on or after promised date
                self.cursor.execute("""
                    SELECT SUM(pa.applied_amount)
                    FROM payment_applications pa
                    JOIN payments p ON pa.payment_id = p.payment_id
                    WHERE pa.invoice_id = ? 
                        AND p.payment_date >= ? 
                        AND p.payment_date <= date(?, '+5 days')
                """, (invoice_id, promised_date, promised_date))
                
                payment_result = self.cursor.fetchone()
                if payment_result and payment_result[0]:
                    actual_amount = float(payment_result[0])
                    promised_amount_decimal = float(promised_amount)
                    
                    if actual_amount >= promised_amount_decimal * 0.9:  # 90% threshold
                        payment_received = True
            
            # Update promise status
            if payment_received:
                status = PromiseStatus.KEPT if actual_amount >= float(promised_amount) * 0.99 else PromiseStatus.PARTIALLY_KEPT
                result = self.update_promise_status(promise_id, status, actual_amount, promised_date)
            else:
                result = self.update_promise_status(promise_id, PromiseStatus.BROKEN)
                if result.get('escalation_required'):
                    escalated_count += 1
            
            if result.get('success'):
                processed_count += 1
                results.append({
                    'promise_id': promise_id,
                    'customer_id': customer_id,
                    'status': result['new_status'],
                    'escalated': result.get('escalation_required', False)
                })
        
        return {
            'total_overdue': len(overdue_promises),
            'processed_count': processed_count,
            'escalated_count': escalated_count,
            'results': results
        }
    
    def get_promise_history(self, customer_id: int, days_back: int = 180) -> Dict:
        """Get payment promise history for a customer"""
        cutoff_date = datetime.now().date() - timedelta(days=days_back)
        
        self.cursor.execute("""
            SELECT promise_id, invoice_id, promise_date, promised_amount, promised_payment_date,
                   status, actual_payment_date, actual_payment_amount, escalation_required,
                   contact_person, contact_method, notes
            FROM payment_promises
            WHERE customer_id = ? AND promise_date >= ?
            ORDER BY promise_date DESC
        """, (customer_id, cutoff_date))
        
        promises = []
        for row in self.cursor.fetchall():
            promise_data = {
                'promise_id': row[0],
                'invoice_id': row[1],
                'promise_date': row[2],
                'promised_amount': float(row[3]),
                'promised_payment_date': row[4],
                'status': row[5],
                'actual_payment_date': row[6],
                'actual_payment_amount': float(row[7]) if row[7] else 0,
                'escalation_required': bool(row[8]),
                'contact_person': row[9],
                'contact_method': row[10],
                'notes': row[11]
            }
            promises.append(promise_data)
        
        # Calculate summary statistics
        total_promises = len(promises)
        kept_promises = len([p for p in promises if p['status'] == 'KEPT'])
        broken_promises = len([p for p in promises if p['status'] == 'BROKEN'])
        partial_promises = len([p for p in promises if p['status'] == 'PARTIALLY_KEPT'])
        
        total_promised = sum(p['promised_amount'] for p in promises)
        total_received = sum(p['actual_payment_amount'] for p in promises if p['actual_payment_amount'] > 0)
        
        return {
            'customer_id': customer_id,
            'period_days': days_back,
            'summary': {
                'total_promises': total_promises,
                'kept_promises': kept_promises,
                'broken_promises': broken_promises,
                'partial_promises': partial_promises,
                'promise_keep_rate': kept_promises / total_promises if total_promises > 0 else 0,
                'total_promised_amount': total_promised,
                'total_received_amount': total_received,
                'fulfillment_rate': total_received / total_promised if total_promised > 0 else 0
            },
            'promises': promises
        }
    
    def generate_follow_up_list(self, priority: str = None, days_ahead: int = 7) -> List[Dict]:
        """Generate prioritized follow-up list for collection agents"""
        self.logger.info(f"Generating follow-up list for {days_ahead} days ahead")
        
        # Base query for active promises needing follow-up
        query = """
            SELECT pp.promise_id, pp.customer_id, pp.invoice_id, pp.promised_amount,
                   pp.promised_payment_date, pp.follow_up_date, pp.contact_person,
                   pp.contact_method, pp.notes,
                   c.customer_name, c.company_name, c.phone, c.email, c.collection_priority,
                   i.invoice_number, i.outstanding_amount,
                   (julianday(pp.promised_payment_date) - julianday('now')) as days_until_due
            FROM payment_promises pp
            JOIN customers c ON pp.customer_id = c.customer_id
            LEFT JOIN invoices i ON pp.invoice_id = i.invoice_id
            WHERE pp.status = 'ACTIVE' 
                AND (pp.follow_up_date <= date('now', '+' || ? || ' days') OR pp.promised_payment_date <= date('now', '+' || ? || ' days'))
                AND pp.follow_up_completed = FALSE
        """
        
        params = [days_ahead, days_ahead]
        
        if priority:
            query += " AND c.collection_priority = ?"
            params.append(priority)
        
        query += " ORDER BY pp.promised_payment_date, pp.promised_amount DESC"
        
        self.cursor.execute(query, params)
        
        follow_up_items = []
        for row in self.cursor.fetchall():
            # Calculate dynamic priority
            days_until_due = int(row[16]) if row[16] is not None else 0
            promised_amount = float(row[3])
            
            if days_until_due < 0:  # Overdue
                calculated_priority = "URGENT"
            elif days_until_due <= 1:  # Due tomorrow or today
                calculated_priority = "HIGH"
            elif promised_amount >= 25000:  # High value
                calculated_priority = "HIGH"
            else:
                calculated_priority = "NORMAL"
            
            item = {
                'promise_id': row[0],
                'customer_id': row[1],
                'invoice_id': row[2],
                'promised_amount': promised_amount,
                'promised_payment_date': row[4],
                'follow_up_date': row[5],
                'contact_person': row[6],
                'contact_method': row[7],
                'promise_notes': row[8],
                'customer_name': row[9],
                'company_name': row[10],
                'phone': row[11],
                'email': row[12],
                'customer_priority': row[13],
                'invoice_number': row[14],
                'outstanding_amount': float(row[15]) if row[15] else 0,
                'days_until_due': days_until_due,
                'calculated_priority': calculated_priority,
                'is_overdue': days_until_due < 0,
                'recommended_action': self._get_recommended_action(days_until_due, promised_amount, row[13])
            }
            follow_up_items.append(item)
        
        # Sort by calculated priority and days until due
        priority_order = {"URGENT": 0, "HIGH": 1, "NORMAL": 2}
        follow_up_items.sort(key=lambda x: (priority_order.get(x['calculated_priority'], 3), x['days_until_due']))
        
        return follow_up_items
    
    def _get_recommended_action(self, days_until_due: int, promised_amount: float, customer_priority: str) -> str:
        """Get recommended action based on promise status"""
        if days_until_due < -2:  # More than 2 days overdue
            return "IMMEDIATE_ESCALATION"
        elif days_until_due < 0:  # Overdue
            return "URGENT_CONTACT"
        elif days_until_due == 0:  # Due today
            return "CONFIRM_PAYMENT"
        elif days_until_due == 1:  # Due tomorrow
            return "REMINDER_CALL"
        else:  # Future due date
            return "COURTESY_REMINDER"
    
    def mark_follow_up_completed(self, promise_id: int, notes: str = "", 
                                performed_by: str = "Collection Agent") -> Dict:
        """Mark a follow-up as completed"""
        try:
            # Update promise record
            self.cursor.execute("""
                UPDATE payment_promises
                SET follow_up_completed = TRUE,
                    notes = CASE 
                        WHEN notes IS NULL OR notes = '' THEN ?
                        ELSE notes || '; Follow-up: ' || ?
                    END,
                    updated_date = CURRENT_TIMESTAMP
                WHERE promise_id = ?
            """, (notes, notes, promise_id))
            
            if self.cursor.rowcount == 0:
                return {"success": False, "error": "Promise not found"}
            
            # Create activity record
            self.cursor.execute("""
                SELECT customer_id, invoice_id FROM payment_promises WHERE promise_id = ?
            """, (promise_id,))
            
            result = self.cursor.fetchone()
            if result:
                customer_id, invoice_id = result
                
                self.cursor.execute("""
                    INSERT INTO collection_activities (
                        customer_id, invoice_id, activity_date, activity_type, activity_result,
                        collection_stage, activity_notes, performed_by, assigned_to
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    customer_id, invoice_id, datetime.now().date(), "PROMISE_FOLLOW_UP", "COMPLETED",
                    "PROMISE_TRACKING", notes or "Follow-up completed", performed_by, performed_by
                ))
            
            self.conn.commit()
            
            return {
                "success": True,
                "promise_id": promise_id,
                "message": "Follow-up marked as completed"
            }
        
        except Exception as e:
            self.conn.rollback()
            self.logger.error(f"Error marking follow-up completed: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def generate_promise_performance_report(self, days_back: int = 90) -> Dict:
        """Generate performance report for payment promises"""
        cutoff_date = datetime.now().date() - timedelta(days=days_back)
        
        # Overall statistics
        self.cursor.execute("""
            SELECT 
                COUNT(*) as total_promises,
                COUNT(CASE WHEN status = 'KEPT' THEN 1 END) as kept_promises,
                COUNT(CASE WHEN status = 'BROKEN' THEN 1 END) as broken_promises,
                COUNT(CASE WHEN status = 'PARTIALLY_KEPT' THEN 1 END) as partial_promises,
                COUNT(CASE WHEN status = 'ACTIVE' THEN 1 END) as active_promises,
                SUM(promised_amount) as total_promised,
                SUM(CASE WHEN status IN ('KEPT', 'PARTIALLY_KEPT') THEN actual_payment_amount ELSE 0 END) as total_received,
                AVG(julianday(actual_payment_date) - julianday(promised_payment_date)) as avg_delay_days
            FROM payment_promises
            WHERE promise_date >= ?
        """, (cutoff_date,))
        
        overall_stats = self.cursor.fetchone()
        
        # Performance by customer type
        self.cursor.execute("""
            SELECT 
                c.customer_type,
                COUNT(*) as total_promises,
                COUNT(CASE WHEN pp.status = 'KEPT' THEN 1 END) as kept_promises,
                SUM(pp.promised_amount) as total_promised,
                SUM(CASE WHEN pp.status IN ('KEPT', 'PARTIALLY_KEPT') THEN pp.actual_payment_amount ELSE 0 END) as total_received
            FROM payment_promises pp
            JOIN customers c ON pp.customer_id = c.customer_id
            WHERE pp.promise_date >= ?
            GROUP BY c.customer_type
        """, (cutoff_date,))
        
        customer_type_stats = {}
        for row in self.cursor.fetchall():
            customer_type_stats[row[0]] = {
                'total_promises': row[1],
                'kept_promises': row[2],
                'keep_rate': row[2] / row[1] if row[1] > 0 else 0,
                'total_promised': float(row[3]),
                'total_received': float(row[4]),
                'fulfillment_rate': float(row[4]) / float(row[3]) if row[3] > 0 else 0
            }
        
        # Top customers by promise volume
        self.cursor.execute("""
            SELECT 
                c.customer_name,
                COUNT(*) as promise_count,
                SUM(pp.promised_amount) as total_promised,
                COUNT(CASE WHEN pp.status = 'KEPT' THEN 1 END) as kept_count
            FROM payment_promises pp
            JOIN customers c ON pp.customer_id = c.customer_id
            WHERE pp.promise_date >= ?
            GROUP BY pp.customer_id, c.customer_name
            HAVING promise_count >= 2
            ORDER BY promise_count DESC, total_promised DESC
            LIMIT 10
        """, (cutoff_date,))
        
        top_customers = []
        for row in self.cursor.fetchall():
            top_customers.append({
                'customer_name': row[0],
                'promise_count': row[1],
                'total_promised': float(row[2]),
                'kept_count': row[3],
                'keep_rate': row[3] / row[1] if row[1] > 0 else 0
            })
        
        return {
            'report_period_days': days_back,
            'generated_date': datetime.now().isoformat(),
            'overall_statistics': {
                'total_promises': overall_stats[0],
                'kept_promises': overall_stats[1],
                'broken_promises': overall_stats[2],
                'partial_promises': overall_stats[3],
                'active_promises': overall_stats[4],
                'promise_keep_rate': overall_stats[1] / overall_stats[0] if overall_stats[0] > 0 else 0,
                'total_promised_amount': float(overall_stats[5]) if overall_stats[5] else 0,
                'total_received_amount': float(overall_stats[6]) if overall_stats[6] else 0,
                'fulfillment_rate': float(overall_stats[6]) / float(overall_stats[5]) if overall_stats[5] and overall_stats[5] > 0 else 0,
                'average_delay_days': float(overall_stats[7]) if overall_stats[7] else 0
            },
            'performance_by_customer_type': customer_type_stats,
            'top_customers_by_promises': top_customers
        }
    
    def close(self):
        """Close database connection"""
        self.conn.close()


if __name__ == "__main__":
    # Example usage
    tracker = PaymentPromiseTracker()
    try:
        # Check for promises due soon
        due_promises = tracker.check_promise_due_dates(3)
        print(f"Promises due within 3 days: {len(due_promises)}")
        
        # Process overdue promises
        overdue_results = tracker.process_overdue_promises()
        print(f"Processed {overdue_results['processed_count']} overdue promises")
        
        # Generate follow-up list
        follow_up_list = tracker.generate_follow_up_list(days_ahead=7)
        print(f"Follow-up items for next 7 days: {len(follow_up_list)}")
        
        # Generate performance report
        performance = tracker.generate_promise_performance_report()
        print(f"Promise keep rate: {performance['overall_statistics']['promise_keep_rate']:.1%}")
        
    finally:
        tracker.close()