"""
Accounts Receivable Collection Workflow Engine
Automated workflow management for collection processes based on rules and triggers
"""

import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class WorkflowStatus(Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

class ActionType(Enum):
    EMAIL_REMINDER = "EMAIL_REMINDER"
    PHONE_CALL = "PHONE_CALL"
    DUNNING_LETTER = "DUNNING_LETTER"
    LEGAL_REFERRAL = "LEGAL_REFERRAL"
    CREDIT_HOLD = "CREDIT_HOLD"
    ESCALATION = "ESCALATION"
    PAYMENT_PLAN = "PAYMENT_PLAN"

@dataclass
class WorkflowTrigger:
    days_past_due: int
    amount_threshold: float
    customer_type: Optional[str] = None
    aging_bucket: Optional[str] = None
    priority_score_min: Optional[int] = None

@dataclass
class WorkflowAction:
    action_type: ActionType
    template_id: Optional[str] = None
    assigned_to: Optional[str] = None
    delay_days: int = 0
    escalation_days: Optional[int] = None

@dataclass
class WorkflowInstance:
    instance_id: str
    workflow_id: int
    customer_id: int
    invoice_id: Optional[int]
    status: WorkflowStatus
    current_step: int
    scheduled_date: datetime
    created_date: datetime
    completed_date: Optional[datetime] = None

class CollectionWorkflowEngine:
    def __init__(self, db_path: str = "ar_collection.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        self._setup_workflow_tables()

    def _setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def _setup_workflow_tables(self):
        """Create additional tables for workflow management"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Workflow instances table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_instances (
                    instance_id TEXT PRIMARY KEY,
                    workflow_id INTEGER NOT NULL,
                    customer_id INTEGER NOT NULL,
                    invoice_id INTEGER,
                    status TEXT NOT NULL,
                    current_step INTEGER DEFAULT 0,
                    scheduled_date DATETIME NOT NULL,
                    created_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completed_date DATETIME,
                    last_action_date DATETIME,
                    failure_reason TEXT,
                    retry_count INTEGER DEFAULT 0,
                    FOREIGN KEY (workflow_id) REFERENCES collection_workflows(workflow_id),
                    FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
                    FOREIGN KEY (invoice_id) REFERENCES invoices(invoice_id)
                )
            """)

            # Workflow steps table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_steps (
                    step_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    step_order INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    template_id TEXT,
                    assigned_to TEXT,
                    delay_days INTEGER DEFAULT 0,
                    escalation_days INTEGER,
                    conditions TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    FOREIGN KEY (workflow_id) REFERENCES collection_workflows(workflow_id)
                )
            """)

            # Workflow execution log
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS workflow_execution_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    instance_id TEXT NOT NULL,
                    step_id INTEGER NOT NULL,
                    execution_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    result_data TEXT,
                    error_message TEXT,
                    execution_time_ms INTEGER,
                    FOREIGN KEY (instance_id) REFERENCES workflow_instances(instance_id),
                    FOREIGN KEY (step_id) REFERENCES workflow_steps(step_id)
                )
            """)

            conn.commit()

    def create_workflow_definition(self, name: str, trigger: WorkflowTrigger, 
                                 actions: List[WorkflowAction]) -> int:
        """Create a new workflow definition with triggers and actions"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create main workflow record
            cursor.execute("""
                INSERT INTO collection_workflows 
                (workflow_name, days_past_due_trigger, amount_threshold, 
                 customer_type_filter, action_type, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (name, trigger.days_past_due, trigger.amount_threshold,
                  trigger.customer_type, actions[0].action_type.value, True))
            
            workflow_id = cursor.lastrowid
            
            # Create workflow steps
            for idx, action in enumerate(actions):
                cursor.execute("""
                    INSERT INTO workflow_steps
                    (workflow_id, step_order, action_type, template_id, 
                     assigned_to, delay_days, escalation_days)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (workflow_id, idx + 1, action.action_type.value,
                      action.template_id, action.assigned_to, 
                      action.delay_days, action.escalation_days))
            
            conn.commit()
            
        self.logger.info(f"Created workflow definition: {name} (ID: {workflow_id})")
        return workflow_id

    def trigger_workflows(self) -> List[str]:
        """Scan for invoices that match workflow triggers and create instances"""
        triggered_instances = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get active workflows
            cursor.execute("""
                SELECT workflow_id, workflow_name, days_past_due_trigger,
                       amount_threshold, customer_type_filter
                FROM collection_workflows
                WHERE is_active = TRUE
                ORDER BY execution_order
            """)
            
            workflows = cursor.fetchall()
            
            for workflow in workflows:
                workflow_id, name, days_trigger, amount_threshold, customer_filter = workflow
                
                # Find matching invoices
                query = """
                    SELECT i.invoice_id, i.customer_id, i.outstanding_amount,
                           i.days_past_due, c.customer_type
                    FROM invoices i
                    JOIN customers c ON i.customer_id = c.customer_id
                    WHERE i.status = 'OPEN' 
                    AND i.days_past_due >= ?
                    AND i.outstanding_amount >= ?
                """
                
                params = [days_trigger, amount_threshold]
                
                if customer_filter:
                    query += " AND c.customer_type = ?"
                    params.append(customer_filter)
                
                # Exclude invoices already in active workflows
                query += """
                    AND i.invoice_id NOT IN (
                        SELECT invoice_id FROM workflow_instances 
                        WHERE status IN ('PENDING', 'ACTIVE') 
                        AND invoice_id IS NOT NULL
                    )
                """
                
                cursor.execute(query, params)
                matching_invoices = cursor.fetchall()
                
                # Create workflow instances
                for invoice in matching_invoices:
                    invoice_id, customer_id = invoice[0], invoice[1]
                    instance_id = self._create_workflow_instance(
                        workflow_id, customer_id, invoice_id
                    )
                    triggered_instances.append(instance_id)
                    
                    self.logger.info(
                        f"Triggered workflow '{name}' for customer {customer_id}, "
                        f"invoice {invoice_id} (Instance: {instance_id})"
                    )
        
        return triggered_instances

    def _create_workflow_instance(self, workflow_id: int, customer_id: int, 
                                invoice_id: Optional[int] = None) -> str:
        """Create a new workflow instance"""
        instance_id = f"WF_{workflow_id}_{customer_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO workflow_instances
                (instance_id, workflow_id, customer_id, invoice_id, 
                 status, scheduled_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (instance_id, workflow_id, customer_id, invoice_id,
                  WorkflowStatus.PENDING.value, datetime.now()))
            
            conn.commit()
        
        return instance_id

    def execute_pending_workflows(self) -> Dict[str, Any]:
        """Execute all pending workflow instances that are due"""
        execution_results = {
            'executed': 0,
            'failed': 0,
            'skipped': 0,
            'instances': []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get pending instances that are due
            cursor.execute("""
                SELECT instance_id, workflow_id, customer_id, invoice_id,
                       current_step, scheduled_date
                FROM workflow_instances
                WHERE status = 'PENDING'
                AND scheduled_date <= ?
                ORDER BY scheduled_date
            """, (datetime.now(),))
            
            pending_instances = cursor.fetchall()
            
            for instance in pending_instances:
                instance_id = instance[0]
                try:
                    result = self._execute_workflow_instance(instance_id)
                    execution_results['instances'].append({
                        'instance_id': instance_id,
                        'status': 'success',
                        'result': result
                    })
                    execution_results['executed'] += 1
                    
                except Exception as e:
                    self.logger.error(f"Failed to execute workflow {instance_id}: {e}")
                    self._mark_instance_failed(instance_id, str(e))
                    execution_results['instances'].append({
                        'instance_id': instance_id,
                        'status': 'failed',
                        'error': str(e)
                    })
                    execution_results['failed'] += 1
        
        return execution_results

    def _execute_workflow_instance(self, instance_id: str) -> Dict[str, Any]:
        """Execute a specific workflow instance"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get instance details
            cursor.execute("""
                SELECT wi.workflow_id, wi.customer_id, wi.invoice_id, wi.current_step,
                       cw.workflow_name
                FROM workflow_instances wi
                JOIN collection_workflows cw ON wi.workflow_id = cw.workflow_id
                WHERE wi.instance_id = ?
            """, (instance_id,))
            
            instance_data = cursor.fetchone()
            if not instance_data:
                raise ValueError(f"Workflow instance {instance_id} not found")
            
            workflow_id, customer_id, invoice_id, current_step, workflow_name = instance_data
            
            # Get next step to execute
            cursor.execute("""
                SELECT step_id, action_type, template_id, assigned_to, 
                       delay_days, escalation_days
                FROM workflow_steps
                WHERE workflow_id = ? AND step_order = ? AND is_active = TRUE
            """, (workflow_id, current_step + 1))
            
            step_data = cursor.fetchone()
            if not step_data:
                # No more steps, mark as completed
                self._mark_instance_completed(instance_id)
                return {'status': 'completed', 'message': 'All steps executed'}
            
            step_id, action_type, template_id, assigned_to, delay_days, escalation_days = step_data
            
            # Execute the action
            start_time = datetime.now()
            execution_result = self._execute_action(
                action_type, customer_id, invoice_id, template_id, assigned_to
            )
            end_time = datetime.now()
            execution_time_ms = int((end_time - start_time).total_seconds() * 1000)
            
            # Log execution
            cursor.execute("""
                INSERT INTO workflow_execution_log
                (instance_id, step_id, status, result_data, execution_time_ms)
                VALUES (?, ?, ?, ?, ?)
            """, (instance_id, step_id, 'SUCCESS', str(execution_result), execution_time_ms))
            
            # Update instance
            next_step = current_step + 1
            next_scheduled = datetime.now() + timedelta(days=delay_days) if delay_days else datetime.now()
            
            cursor.execute("""
                UPDATE workflow_instances
                SET current_step = ?, scheduled_date = ?, last_action_date = ?,
                    status = CASE 
                        WHEN ? = (SELECT MAX(step_order) FROM workflow_steps WHERE workflow_id = ?)
                        THEN 'COMPLETED'
                        ELSE 'ACTIVE'
                    END
                WHERE instance_id = ?
            """, (next_step, next_scheduled, datetime.now(), next_step, workflow_id, instance_id))
            
            conn.commit()
            
            return {
                'status': 'success',
                'action_executed': action_type,
                'next_scheduled': next_scheduled.isoformat(),
                'execution_time_ms': execution_time_ms
            }

    def _execute_action(self, action_type: str, customer_id: int, 
                       invoice_id: Optional[int], template_id: Optional[str],
                       assigned_to: Optional[str]) -> Dict[str, Any]:
        """Execute a specific workflow action"""
        
        # Get customer and invoice details
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT customer_name, email, phone, outstanding_amount
                FROM customers c
                LEFT JOIN (
                    SELECT customer_id, SUM(outstanding_amount) as outstanding_amount
                    FROM invoices WHERE status = 'OPEN'
                    GROUP BY customer_id
                ) i ON c.customer_id = i.customer_id
                WHERE c.customer_id = ?
            """, (customer_id,))
            
            customer_data = cursor.fetchone()
            
        if action_type == ActionType.EMAIL_REMINDER.value:
            return self._send_email_reminder(customer_data, invoice_id, template_id)
        elif action_type == ActionType.PHONE_CALL.value:
            return self._schedule_phone_call(customer_data, assigned_to)
        elif action_type == ActionType.DUNNING_LETTER.value:
            return self._generate_dunning_letter(customer_data, invoice_id)
        elif action_type == ActionType.CREDIT_HOLD.value:
            return self._apply_credit_hold(customer_id)
        elif action_type == ActionType.LEGAL_REFERRAL.value:
            return self._create_legal_referral(customer_data, invoice_id)
        elif action_type == ActionType.ESCALATION.value:
            return self._escalate_case(customer_id, assigned_to)
        else:
            return {'status': 'not_implemented', 'action': action_type}

    def _send_email_reminder(self, customer_data: tuple, invoice_id: Optional[int],
                           template_id: Optional[str]) -> Dict[str, Any]:
        """Simulate sending email reminder"""
        customer_name, email, phone, outstanding = customer_data
        
        # Create collection activity record
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO collection_activities
                (customer_id, invoice_id, activity_date, activity_type, 
                 activity_result, contact_person, communication_method,
                 activity_notes, performed_by)
                VALUES ((SELECT customer_id FROM customers WHERE customer_name = ?),
                        ?, ?, 'EMAIL', 'SENT', ?, 'EMAIL',
                        ?, 'Workflow Engine')
            """, (customer_name, invoice_id, datetime.now().date(), 
                  customer_name, f"Automated email reminder sent using template {template_id or 'default'}"))
            
            conn.commit()
        
        return {
            'action': 'email_sent',
            'recipient': email,
            'template': template_id or 'default',
            'outstanding_amount': outstanding
        }

    def _schedule_phone_call(self, customer_data: tuple, assigned_to: Optional[str]) -> Dict[str, Any]:
        """Schedule a phone call task"""
        customer_name, email, phone, outstanding = customer_data
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO collection_activities
                (customer_id, activity_date, activity_type, activity_result,
                 contact_person, communication_method, next_action, 
                 next_action_date, assigned_to, performed_by)
                VALUES ((SELECT customer_id FROM customers WHERE customer_name = ?),
                        ?, 'PHONE_CALL', 'SCHEDULED', ?, 'PHONE',
                        'MAKE_CALL', ?, ?, 'Workflow Engine')
            """, (customer_name, datetime.now().date(), customer_name,
                  (datetime.now() + timedelta(days=1)).date(), assigned_to or 'Collection Team'))
            
            conn.commit()
        
        return {
            'action': 'call_scheduled',
            'phone': phone,
            'assigned_to': assigned_to or 'Collection Team',
            'scheduled_date': (datetime.now() + timedelta(days=1)).date().isoformat()
        }

    def _generate_dunning_letter(self, customer_data: tuple, invoice_id: Optional[int]) -> Dict[str, Any]:
        """Generate dunning letter"""
        customer_name, email, phone, outstanding = customer_data
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO collection_activities
                (customer_id, invoice_id, activity_date, activity_type,
                 activity_result, contact_person, communication_method,
                 activity_notes, performed_by)
                VALUES ((SELECT customer_id FROM customers WHERE customer_name = ?),
                        ?, ?, 'LETTER', 'SENT', ?, 'MAIL',
                        'Dunning letter generated and sent', 'Workflow Engine')
            """, (customer_name, invoice_id, datetime.now().date(), customer_name))
            
            conn.commit()
        
        return {
            'action': 'dunning_letter_sent',
            'customer': customer_name,
            'outstanding_amount': outstanding
        }

    def _apply_credit_hold(self, customer_id: int) -> Dict[str, Any]:
        """Apply credit hold to customer"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Update customer credit hold status
            cursor.execute("""
                UPDATE customers 
                SET is_credit_hold = TRUE,
                    updated_date = CURRENT_TIMESTAMP
                WHERE customer_id = ?
            """, (customer_id,))
            
            # Record credit history event
            cursor.execute("""
                INSERT INTO credit_history
                (customer_id, event_date, event_type, reason, authorized_by)
                VALUES (?, ?, 'CREDIT_HOLD', 'Automated workflow action', 'Workflow Engine')
            """, (customer_id, datetime.now().date()))
            
            conn.commit()
        
        return {
            'action': 'credit_hold_applied',
            'customer_id': customer_id,
            'effective_date': datetime.now().date().isoformat()
        }

    def _create_legal_referral(self, customer_data: tuple, invoice_id: Optional[int]) -> Dict[str, Any]:
        """Create legal referral case"""
        customer_name, email, phone, outstanding = customer_data
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO collection_activities
                (customer_id, invoice_id, activity_date, activity_type,
                 activity_result, contact_person, communication_method,
                 activity_notes, assigned_to, collection_stage, performed_by)
                VALUES ((SELECT customer_id FROM customers WHERE customer_name = ?),
                        ?, ?, 'LEGAL_REFERRAL', 'REFERRED', ?, 'LEGAL',
                        'Case referred to legal department for collection action',
                        'Legal Department', 'LEGAL', 'Workflow Engine')
            """, (customer_name, invoice_id, datetime.now().date(), customer_name))
            
            conn.commit()
        
        return {
            'action': 'legal_referral_created',
            'customer': customer_name,
            'outstanding_amount': outstanding,
            'referral_date': datetime.now().date().isoformat()
        }

    def _escalate_case(self, customer_id: int, assigned_to: Optional[str]) -> Dict[str, Any]:
        """Escalate case to supervisor"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO collection_activities
                (customer_id, activity_date, activity_type, activity_result,
                 communication_method, activity_notes, assigned_to, performed_by)
                VALUES (?, ?, 'ESCALATION', 'ESCALATED', 'INTERNAL',
                        'Case escalated due to workflow trigger', ?, 'Workflow Engine')
            """, (customer_id, datetime.now().date(), assigned_to or 'Collection Supervisor'))
            
            conn.commit()
        
        return {
            'action': 'case_escalated',
            'customer_id': customer_id,
            'assigned_to': assigned_to or 'Collection Supervisor',
            'escalation_date': datetime.now().date().isoformat()
        }

    def _mark_instance_completed(self, instance_id: str):
        """Mark workflow instance as completed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflow_instances
                SET status = 'COMPLETED', completed_date = CURRENT_TIMESTAMP
                WHERE instance_id = ?
            """, (instance_id,))
            conn.commit()

    def _mark_instance_failed(self, instance_id: str, error_message: str):
        """Mark workflow instance as failed"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE workflow_instances
                SET status = 'FAILED', failure_reason = ?
                WHERE instance_id = ?
            """, (error_message, instance_id))
            conn.commit()

    def get_workflow_status(self, instance_id: Optional[str] = None) -> Dict[str, Any]:
        """Get status of workflows"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if instance_id:
                # Get specific instance status
                cursor.execute("""
                    SELECT wi.*, cw.workflow_name
                    FROM workflow_instances wi
                    JOIN collection_workflows cw ON wi.workflow_id = cw.workflow_id
                    WHERE wi.instance_id = ?
                """, (instance_id,))
                
                instance = cursor.fetchone()
                if not instance:
                    return {'error': 'Instance not found'}
                
                # Get execution log
                cursor.execute("""
                    SELECT step_id, execution_date, status, result_data
                    FROM workflow_execution_log
                    WHERE instance_id = ?
                    ORDER BY execution_date
                """, (instance_id,))
                
                logs = cursor.fetchall()
                
                return {
                    'instance': dict(zip([col[0] for col in cursor.description], instance)),
                    'execution_log': [dict(zip([col[0] for col in cursor.description], log)) for log in logs]
                }
            
            else:
                # Get summary of all workflows
                cursor.execute("""
                    SELECT status, COUNT(*) as count
                    FROM workflow_instances
                    GROUP BY status
                """)
                
                status_summary = dict(cursor.fetchall())
                
                cursor.execute("""
                    SELECT COUNT(*) as active_workflows
                    FROM collection_workflows
                    WHERE is_active = TRUE
                """)
                
                active_workflows = cursor.fetchone()[0]
                
                cursor.execute("""
                    SELECT instance_id, workflow_id, customer_id, 
                           status, scheduled_date
                    FROM workflow_instances
                    WHERE status IN ('PENDING', 'ACTIVE')
                    ORDER BY scheduled_date
                    LIMIT 10
                """)
                
                upcoming = cursor.fetchall()
                
                return {
                    'status_summary': status_summary,
                    'active_workflow_definitions': active_workflows,
                    'upcoming_executions': [dict(zip([col[0] for col in cursor.description], row)) for row in upcoming]
                }

    def setup_default_workflows(self):
        """Set up default collection workflows"""
        self.logger.info("Setting up default collection workflows...")
        
        # Early Reminder Workflow (1-30 days past due)
        early_trigger = WorkflowTrigger(days_past_due=1, amount_threshold=100.0)
        early_actions = [
            WorkflowAction(ActionType.EMAIL_REMINDER, template_id="friendly_reminder", delay_days=0),
            WorkflowAction(ActionType.PHONE_CALL, assigned_to="Collection Team", delay_days=7),
            WorkflowAction(ActionType.EMAIL_REMINDER, template_id="second_notice", delay_days=14)
        ]
        self.create_workflow_definition("Early Reminder Workflow", early_trigger, early_actions)
        
        # Standard Collection Workflow (31-60 days past due)
        standard_trigger = WorkflowTrigger(days_past_due=31, amount_threshold=500.0)
        standard_actions = [
            WorkflowAction(ActionType.PHONE_CALL, assigned_to="Senior Collector", delay_days=0),
            WorkflowAction(ActionType.DUNNING_LETTER, delay_days=7),
            WorkflowAction(ActionType.PHONE_CALL, assigned_to="Collection Supervisor", delay_days=14)
        ]
        self.create_workflow_definition("Standard Collection Workflow", standard_trigger, standard_actions)
        
        # Intensive Collection Workflow (61-90 days past due)
        intensive_trigger = WorkflowTrigger(days_past_due=61, amount_threshold=1000.0)
        intensive_actions = [
            WorkflowAction(ActionType.PHONE_CALL, assigned_to="Collection Supervisor", delay_days=0),
            WorkflowAction(ActionType.CREDIT_HOLD, delay_days=3),
            WorkflowAction(ActionType.ESCALATION, assigned_to="Collection Manager", delay_days=7),
            WorkflowAction(ActionType.DUNNING_LETTER, template_id="final_notice", delay_days=14)
        ]
        self.create_workflow_definition("Intensive Collection Workflow", intensive_trigger, intensive_actions)
        
        # Legal Referral Workflow (90+ days past due)
        legal_trigger = WorkflowTrigger(days_past_due=90, amount_threshold=2000.0)
        legal_actions = [
            WorkflowAction(ActionType.ESCALATION, assigned_to="Collection Manager", delay_days=0),
            WorkflowAction(ActionType.LEGAL_REFERRAL, delay_days=7)
        ]
        self.create_workflow_definition("Legal Referral Workflow", legal_trigger, legal_actions)
        
        self.logger.info("Default workflows created successfully")

# Usage example and testing
if __name__ == "__main__":
    engine = CollectionWorkflowEngine()
    
    # Setup default workflows
    engine.setup_default_workflows()
    
    # Trigger workflows for qualifying invoices
    triggered = engine.trigger_workflows()
    print(f"Triggered {len(triggered)} workflow instances")
    
    # Execute pending workflows
    results = engine.execute_pending_workflows()
    print(f"Execution results: {results}")
    
    # Get workflow status
    status = engine.get_workflow_status()
    print(f"Workflow status: {status}")