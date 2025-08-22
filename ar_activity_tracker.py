"""
Accounts Receivable Collection Activities and Communication Tracker
Comprehensive tracking of all collection activities, communications, and customer interactions
"""

import sqlite3
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json

class ActivityType(Enum):
    PHONE_CALL = "PHONE_CALL"
    EMAIL = "EMAIL"
    LETTER = "LETTER"
    MEETING = "MEETING"
    STATEMENT = "STATEMENT"
    DUNNING_LETTER = "DUNNING_LETTER"
    LEGAL_REFERRAL = "LEGAL_REFERRAL"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    DISPUTE_LOGGED = "DISPUTE_LOGGED"
    ESCALATION = "ESCALATION"

class ActivityResult(Enum):
    CONTACT_MADE = "CONTACT_MADE"
    NO_ANSWER = "NO_ANSWER"
    BUSY = "BUSY"
    PROMISE_MADE = "PROMISE_MADE"
    DISPUTE_RAISED = "DISPUTE_RAISED"
    PAYMENT_RECEIVED = "PAYMENT_RECEIVED"
    PAYMENT_ARRANGED = "PAYMENT_ARRANGED"
    HOSTILE_RESPONSE = "HOSTILE_RESPONSE"
    DISCONNECTED_NUMBER = "DISCONNECTED_NUMBER"
    SENT_SUCCESSFULLY = "SENT_SUCCESSFULLY"
    DELIVERY_FAILED = "DELIVERY_FAILED"

class CommunicationMethod(Enum):
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    MAIL = "MAIL"
    FAX = "FAX"
    IN_PERSON = "IN_PERSON"
    SMS = "SMS"
    PORTAL = "PORTAL"
    LEGAL = "LEGAL"

@dataclass
class CollectionActivity:
    customer_id: int
    activity_type: ActivityType
    activity_date: date
    contact_person: str
    communication_method: CommunicationMethod
    activity_result: ActivityResult
    invoice_id: Optional[int] = None
    duration_minutes: Optional[int] = None
    next_action: Optional[str] = None
    next_action_date: Optional[date] = None
    activity_notes: Optional[str] = None
    outcome_summary: Optional[str] = None
    performed_by: Optional[str] = None
    assigned_to: Optional[str] = None
    collection_stage: Optional[str] = None
    follow_up_required: bool = False
    follow_up_priority: str = "NORMAL"

class CollectionActivityTracker:
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._setup_logging()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def log_activity(self, activity: CollectionActivity) -> int:
        """Log a new collection activity"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO collection_activities (
                    customer_id, invoice_id, activity_date, activity_type,
                    activity_result, contact_person, communication_method,
                    duration_minutes, next_action, next_action_date,
                    collection_stage, activity_notes, outcome_summary,
                    performed_by, assigned_to, requires_follow_up,
                    follow_up_priority
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                activity.customer_id, activity.invoice_id, activity.activity_date,
                activity.activity_type.value, activity.activity_result.value,
                activity.contact_person, activity.communication_method.value,
                activity.duration_minutes, activity.next_action, activity.next_action_date,
                activity.collection_stage, activity.activity_notes, activity.outcome_summary,
                activity.performed_by, activity.assigned_to, activity.follow_up_required,
                activity.follow_up_priority
            ))
            
            activity_id = cursor.lastrowid
            
            # Update customer last contact date
            cursor.execute("""
                UPDATE customers 
                SET last_contact_date = ?
                WHERE customer_id = ?
            """, (activity.activity_date, activity.customer_id))
            
            # Update invoice collection status if applicable
            if activity.invoice_id:
                self._update_invoice_collection_status(cursor, activity)
            
            conn.commit()
            
        self.logger.info(f"Logged activity {activity_id} for customer {activity.customer_id}")
        return activity_id

    def _update_invoice_collection_status(self, cursor, activity: CollectionActivity):
        """Update invoice collection status based on activity"""
        if activity.activity_result == ActivityResult.PAYMENT_RECEIVED:
            status = "NORMAL"
        elif activity.activity_result == ActivityResult.DISPUTE_RAISED:
            status = "DISPUTED"
        elif activity.collection_stage in ["LEGAL", "FINAL_NOTICE"]:
            status = "COLLECTIONS"
        else:
            status = "FIRST_NOTICE" if activity.activity_type in [ActivityType.PHONE_CALL, ActivityType.EMAIL] else "SECOND_NOTICE"
        
        cursor.execute("""
            UPDATE invoices 
            SET collection_status = ?,
                last_collection_activity_date = ?,
                next_collection_action_date = ?
            WHERE invoice_id = ?
        """, (status, activity.activity_date, activity.next_action_date, activity.invoice_id))

    def get_customer_activity_history(self, customer_id: int, 
                                    days_back: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get activity history for a specific customer"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT ca.*, c.customer_name, i.invoice_number
                FROM collection_activities ca
                JOIN customers c ON ca.customer_id = c.customer_id
                LEFT JOIN invoices i ON ca.invoice_id = i.invoice_id
                WHERE ca.customer_id = ?
            """
            
            params = [customer_id]
            
            if days_back:
                query += " AND ca.activity_date >= ?"
                params.append((datetime.now() - timedelta(days=days_back)).date())
            
            query += " ORDER BY ca.activity_date DESC, ca.created_date DESC"
            
            cursor.execute(query, params)
            
            columns = [description[0] for description in cursor.description]
            activities = []
            
            for row in cursor.fetchall():
                activity_dict = dict(zip(columns, row))
                activities.append(activity_dict)
            
            return activities

    def get_follow_up_activities(self, assigned_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get activities that require follow-up"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            query = """
                SELECT ca.*, c.customer_name, c.phone, c.email,
                       i.invoice_number, i.outstanding_amount
                FROM collection_activities ca
                JOIN customers c ON ca.customer_id = c.customer_id
                LEFT JOIN invoices i ON ca.invoice_id = i.invoice_id
                WHERE ca.requires_follow_up = TRUE
                AND (ca.next_action_date <= ? OR ca.next_action_date IS NULL)
            """
            
            params = [datetime.now().date()]
            
            if assigned_to:
                query += " AND ca.assigned_to = ?"
                params.append(assigned_to)
            
            query += " ORDER BY ca.follow_up_priority DESC, ca.next_action_date ASC"
            
            cursor.execute(query, params)
            
            columns = [description[0] for description in cursor.description]
            follow_ups = []
            
            for row in cursor.fetchall():
                follow_up_dict = dict(zip(columns, row))
                follow_ups.append(follow_up_dict)
            
            return follow_ups

    def mark_follow_up_completed(self, activity_id: int, completion_notes: str,
                               performer: str) -> bool:
        """Mark a follow-up activity as completed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get the original activity details
            cursor.execute("""
                SELECT customer_id, invoice_id, next_action
                FROM collection_activities
                WHERE activity_id = ?
            """, (activity_id,))
            
            original_activity = cursor.fetchone()
            if not original_activity:
                return False
            
            customer_id, invoice_id, next_action = original_activity
            
            # Create a new activity for the follow-up completion
            cursor.execute("""
                INSERT INTO collection_activities (
                    customer_id, invoice_id, activity_date, activity_type,
                    activity_result, contact_person, communication_method,
                    activity_notes, performed_by, requires_follow_up
                ) VALUES (?, ?, ?, 'FOLLOW_UP', 'COMPLETED', 
                         'Follow-up Completion', 'INTERNAL', ?, ?, FALSE)
            """, (customer_id, invoice_id, datetime.now().date(),
                  f"Follow-up completed: {next_action}. {completion_notes}",
                  performer))
            
            # Mark original activity as follow-up completed
            cursor.execute("""
                UPDATE collection_activities
                SET requires_follow_up = FALSE
                WHERE activity_id = ?
            """, (activity_id,))
            
            conn.commit()
            
        self.logger.info(f"Follow-up completed for activity {activity_id}")
        return True

    def get_communication_summary(self, customer_id: int) -> Dict[str, Any]:
        """Get communication summary for a customer"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Basic communication stats
            cursor.execute("""
                SELECT 
                    communication_method,
                    COUNT(*) as count,
                    MAX(activity_date) as last_contact
                FROM collection_activities
                WHERE customer_id = ?
                GROUP BY communication_method
            """, (customer_id,))
            
            communication_methods = {}
            for method, count, last_contact in cursor.fetchall():
                communication_methods[method] = {
                    'count': count,
                    'last_contact': last_contact
                }
            
            # Activity results summary
            cursor.execute("""
                SELECT 
                    activity_result,
                    COUNT(*) as count
                FROM collection_activities
                WHERE customer_id = ?
                GROUP BY activity_result
            """, (customer_id,))
            
            results_summary = dict(cursor.fetchall())
            
            # Recent activity trend (last 30 days)
            cursor.execute("""
                SELECT 
                    DATE(activity_date) as date,
                    COUNT(*) as activity_count
                FROM collection_activities
                WHERE customer_id = ?
                AND activity_date >= ?
                GROUP BY DATE(activity_date)
                ORDER BY date
            """, (customer_id, (datetime.now() - timedelta(days=30)).date()))
            
            recent_trend = [{'date': date, 'count': count} for date, count in cursor.fetchall()]
            
            # Outstanding follow-ups
            cursor.execute("""
                SELECT COUNT(*)
                FROM collection_activities
                WHERE customer_id = ?
                AND requires_follow_up = TRUE
                AND (next_action_date <= ? OR next_action_date IS NULL)
            """, (customer_id, datetime.now().date()))
            
            outstanding_follow_ups = cursor.fetchone()[0]
            
            # Most recent meaningful contact
            cursor.execute("""
                SELECT activity_date, activity_type, activity_result, 
                       contact_person, performed_by
                FROM collection_activities
                WHERE customer_id = ?
                AND activity_result NOT IN ('NO_ANSWER', 'BUSY', 'DELIVERY_FAILED')
                ORDER BY activity_date DESC, created_date DESC
                LIMIT 1
            """, (customer_id,))
            
            last_meaningful_contact = cursor.fetchone()
            
            return {
                'communication_methods': communication_methods,
                'results_summary': results_summary,
                'recent_trend': recent_trend,
                'outstanding_follow_ups': outstanding_follow_ups,
                'last_meaningful_contact': dict(zip(
                    ['date', 'type', 'result', 'contact_person', 'performer'],
                    last_meaningful_contact or [None] * 5
                ))
            }

    def get_collection_effectiveness(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Analyze collection activity effectiveness"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Overall activity stats
            cursor.execute("""
                SELECT 
                    activity_type,
                    COUNT(*) as total_activities,
                    COUNT(CASE WHEN activity_result IN ('CONTACT_MADE', 'PROMISE_MADE', 'PAYMENT_RECEIVED', 'PAYMENT_ARRANGED') THEN 1 END) as successful_contacts,
                    AVG(CASE WHEN duration_minutes IS NOT NULL THEN duration_minutes END) as avg_duration
                FROM collection_activities
                WHERE activity_date BETWEEN ? AND ?
                GROUP BY activity_type
            """, (start_date, end_date))
            
            activity_effectiveness = {}
            for activity_type, total, successful, avg_duration in cursor.fetchall():
                activity_effectiveness[activity_type] = {
                    'total_activities': total,
                    'successful_contacts': successful,
                    'success_rate': (successful / total * 100) if total > 0 else 0,
                    'avg_duration_minutes': avg_duration
                }
            
            # Communication method effectiveness
            cursor.execute("""
                SELECT 
                    communication_method,
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN activity_result IN ('CONTACT_MADE', 'PROMISE_MADE', 'PAYMENT_RECEIVED') THEN 1 END) as successful_attempts
                FROM collection_activities
                WHERE activity_date BETWEEN ? AND ?
                GROUP BY communication_method
            """, (start_date, end_date))
            
            communication_effectiveness = {}
            for method, total, successful in cursor.fetchall():
                communication_effectiveness[method] = {
                    'total_attempts': total,
                    'successful_attempts': successful,
                    'success_rate': (successful / total * 100) if total > 0 else 0
                }
            
            # Promise fulfillment tracking
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN ca.activity_result = 'PROMISE_MADE' THEN 1 END) as promises_made,
                    COUNT(CASE WHEN pp.status = 'KEPT' THEN 1 END) as promises_kept,
                    COUNT(CASE WHEN pp.status = 'BROKEN' THEN 1 END) as promises_broken
                FROM collection_activities ca
                LEFT JOIN payment_promises pp ON ca.customer_id = pp.customer_id
                    AND pp.promise_date BETWEEN ? AND ?
                WHERE ca.activity_date BETWEEN ? AND ?
            """, (start_date, end_date, start_date, end_date))
            
            promise_stats = cursor.fetchone()
            promises_made, promises_kept, promises_broken = promise_stats
            
            # Collector performance
            cursor.execute("""
                SELECT 
                    performed_by,
                    COUNT(*) as total_activities,
                    COUNT(CASE WHEN activity_result IN ('CONTACT_MADE', 'PROMISE_MADE', 'PAYMENT_RECEIVED') THEN 1 END) as successful_activities,
                    SUM(duration_minutes) as total_time_minutes,
                    COUNT(DISTINCT customer_id) as customers_contacted
                FROM collection_activities
                WHERE activity_date BETWEEN ? AND ?
                AND performed_by IS NOT NULL
                GROUP BY performed_by
            """, (start_date, end_date))
            
            collector_performance = {}
            for performer, total, successful, total_time, customers in cursor.fetchall():
                collector_performance[performer] = {
                    'total_activities': total,
                    'successful_activities': successful,
                    'success_rate': (successful / total * 100) if total > 0 else 0,
                    'total_time_hours': (total_time / 60) if total_time else 0,
                    'customers_contacted': customers,
                    'avg_time_per_activity': (total_time / total) if total and total_time else 0
                }
            
            return {
                'period': {'start_date': start_date.isoformat(), 'end_date': end_date.isoformat()},
                'activity_effectiveness': activity_effectiveness,
                'communication_effectiveness': communication_effectiveness,
                'promise_statistics': {
                    'promises_made': promises_made or 0,
                    'promises_kept': promises_kept or 0,
                    'promises_broken': promises_broken or 0,
                    'fulfillment_rate': ((promises_kept or 0) / (promises_made or 1) * 100) if promises_made else 0
                },
                'collector_performance': collector_performance
            }

    def create_activity_report(self, customer_id: Optional[int] = None,
                             start_date: Optional[date] = None,
                             end_date: Optional[date] = None,
                             activity_type: Optional[str] = None) -> Dict[str, Any]:
        """Generate comprehensive activity report"""
        if not start_date:
            start_date = (datetime.now() - timedelta(days=30)).date()
        if not end_date:
            end_date = datetime.now().date()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Build query conditions
            conditions = ["ca.activity_date BETWEEN ? AND ?"]
            params = [start_date, end_date]
            
            if customer_id:
                conditions.append("ca.customer_id = ?")
                params.append(customer_id)
            
            if activity_type:
                conditions.append("ca.activity_type = ?")
                params.append(activity_type)
            
            where_clause = " AND ".join(conditions)
            
            # Activity summary
            cursor.execute(f"""
                SELECT 
                    COUNT(*) as total_activities,
                    COUNT(DISTINCT ca.customer_id) as customers_contacted,
                    COUNT(CASE WHEN ca.activity_result IN ('CONTACT_MADE', 'PROMISE_MADE', 'PAYMENT_RECEIVED') THEN 1 END) as successful_contacts,
                    SUM(ca.duration_minutes) as total_duration_minutes,
                    COUNT(CASE WHEN ca.requires_follow_up = TRUE THEN 1 END) as follow_ups_generated
                FROM collection_activities ca
                WHERE {where_clause}
            """, params)
            
            summary = cursor.fetchone()
            
            # Daily activity breakdown
            cursor.execute(f"""
                SELECT 
                    ca.activity_date,
                    COUNT(*) as activity_count,
                    COUNT(CASE WHEN ca.activity_result IN ('CONTACT_MADE', 'PROMISE_MADE', 'PAYMENT_RECEIVED') THEN 1 END) as successful_count
                FROM collection_activities ca
                WHERE {where_clause}
                GROUP BY ca.activity_date
                ORDER BY ca.activity_date
            """, params)
            
            daily_breakdown = [
                {
                    'date': row[0],
                    'total_activities': row[1],
                    'successful_activities': row[2],
                    'success_rate': (row[2] / row[1] * 100) if row[1] > 0 else 0
                }
                for row in cursor.fetchall()
            ]
            
            # Top customers by activity
            cursor.execute(f"""
                SELECT 
                    c.customer_name,
                    c.customer_code,
                    COUNT(*) as activity_count,
                    MAX(ca.activity_date) as last_activity,
                    SUM(CASE WHEN i.outstanding_amount > 0 THEN i.outstanding_amount ELSE 0 END) as outstanding_amount
                FROM collection_activities ca
                JOIN customers c ON ca.customer_id = c.customer_id
                LEFT JOIN invoices i ON ca.invoice_id = i.invoice_id
                WHERE {where_clause}
                GROUP BY c.customer_id, c.customer_name, c.customer_code
                ORDER BY activity_count DESC
                LIMIT 10
            """, params)
            
            top_customers = [
                {
                    'customer_name': row[0],
                    'customer_code': row[1],
                    'activity_count': row[2],
                    'last_activity': row[3],
                    'outstanding_amount': row[4] or 0
                }
                for row in cursor.fetchall()
            ]
            
            return {
                'report_period': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat()
                },
                'summary': {
                    'total_activities': summary[0],
                    'customers_contacted': summary[1],
                    'successful_contacts': summary[2],
                    'success_rate': (summary[2] / summary[0] * 100) if summary[0] > 0 else 0,
                    'total_duration_hours': (summary[3] / 60) if summary[3] else 0,
                    'follow_ups_generated': summary[4]
                },
                'daily_breakdown': daily_breakdown,
                'top_customers_by_activity': top_customers
            }

    def log_bulk_activities(self, activities: List[CollectionActivity]) -> List[int]:
        """Log multiple activities in bulk for efficiency"""
        activity_ids = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for activity in activities:
                cursor.execute("""
                    INSERT INTO collection_activities (
                        customer_id, invoice_id, activity_date, activity_type,
                        activity_result, contact_person, communication_method,
                        duration_minutes, next_action, next_action_date,
                        collection_stage, activity_notes, outcome_summary,
                        performed_by, assigned_to, requires_follow_up,
                        follow_up_priority
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    activity.customer_id, activity.invoice_id, activity.activity_date,
                    activity.activity_type.value, activity.activity_result.value,
                    activity.contact_person, activity.communication_method.value,
                    activity.duration_minutes, activity.next_action, activity.next_action_date,
                    activity.collection_stage, activity.activity_notes, activity.outcome_summary,
                    activity.performed_by, activity.assigned_to, activity.follow_up_required,
                    activity.follow_up_priority
                ))
                
                activity_ids.append(cursor.lastrowid)
                
                # Update customer last contact date
                cursor.execute("""
                    UPDATE customers 
                    SET last_contact_date = ?
                    WHERE customer_id = ?
                """, (activity.activity_date, activity.customer_id))
            
            conn.commit()
        
        self.logger.info(f"Bulk logged {len(activity_ids)} activities")
        return activity_ids

# Usage example and testing
if __name__ == "__main__":
    tracker = CollectionActivityTracker()
    
    # Example: Log a phone call activity
    phone_activity = CollectionActivity(
        customer_id=1,
        activity_type=ActivityType.PHONE_CALL,
        activity_date=datetime.now().date(),
        contact_person="John Smith",
        communication_method=CommunicationMethod.PHONE,
        activity_result=ActivityResult.PROMISE_MADE,
        duration_minutes=15,
        next_action="Follow up on payment promise",
        next_action_date=(datetime.now() + timedelta(days=3)).date(),
        activity_notes="Customer promised to pay $5000 by Friday",
        performed_by="Sarah Johnson",
        follow_up_required=True,
        follow_up_priority="HIGH"
    )
    
    activity_id = tracker.log_activity(phone_activity)
    print(f"Logged activity: {activity_id}")
    
    # Get customer activity history
    history = tracker.get_customer_activity_history(1, days_back=30)
    print(f"Activity history: {len(history)} activities")
    
    # Get follow-up activities
    follow_ups = tracker.get_follow_up_activities()
    print(f"Follow-ups needed: {len(follow_ups)}")
    
    # Get communication summary
    summary = tracker.get_communication_summary(1)
    print(f"Communication summary: {summary}")
    
    # Generate activity report
    report = tracker.create_activity_report(start_date=(datetime.now() - timedelta(days=7)).date())
    print(f"Weekly report: {report['summary']}")