"""
Accounts Receivable Collection Manager - Main Orchestrator
Central coordination system that integrates all AR collection components
"""

import sqlite3
import logging
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple, Any
import json
import sys
import os

# Import all AR collection modules
from ar_data_generator import ARDataGenerator
from ar_prioritization import CustomerPrioritizer
from ar_promise_tracker import PaymentPromiseTracker
from ar_analytics import CollectionAnalytics
from ar_workflow_engine import CollectionWorkflowEngine
from ar_activity_tracker import CollectionActivityTracker, CollectionActivity, ActivityType, ActivityResult, CommunicationMethod
from ar_aging_analysis import AgingAnalyzer

class ARCollectionManager:
    def __init__(self, db_path: str = "ar_collection.db", config: Optional[Dict] = None):
        self.db_path = db_path
        self.config = config or self._load_default_config()
        self.logger = logging.getLogger(__name__)
        self._setup_logging()
        
        # Initialize all collection modules
        self.data_generator = ARDataGenerator(db_path)
        self.prioritizer = CustomerPrioritizer(db_path)
        self.promise_tracker = PaymentPromiseTracker(db_path)
        self.analytics = CollectionAnalytics(db_path)
        self.workflow_engine = CollectionWorkflowEngine(db_path)
        self.activity_tracker = CollectionActivityTracker(db_path)
        self.aging_analyzer = AgingAnalyzer(db_path)
        
        self.logger.info("AR Collection Manager initialized successfully")

    def _setup_logging(self):
        log_level = self.config.get('log_level', 'INFO')
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('ar_collection.log'),
                logging.StreamHandler(sys.stdout)
            ]
        )

    def _load_default_config(self) -> Dict[str, Any]:
        """Load default configuration settings"""
        return {
            'log_level': 'INFO',
            'auto_workflow_execution': True,
            'daily_priority_refresh': True,
            'promise_follow_up_enabled': True,
            'aging_refresh_frequency': 'daily',
            'collection_targets': {
                'weekly_calls': 100,
                'weekly_emails': 200,
                'monthly_collection_rate': 85.0
            },
            'risk_thresholds': {
                'high_risk_days': 60,
                'critical_risk_days': 90,
                'large_invoice_threshold': 10000.0
            },
            'workflow_settings': {
                'auto_trigger': True,
                'escalation_enabled': True,
                'legal_referral_threshold': 90
            }
        }

    def initialize_system(self, generate_sample_data: bool = False) -> Dict[str, Any]:
        """Initialize the complete AR collection system"""
        self.logger.info("Initializing AR Collection Management System...")
        
        initialization_results = {
            'database_setup': False,
            'sample_data_generated': False,
            'workflows_created': False,
            'system_ready': False,
            'errors': []
        }
        
        try:
            # Ensure database schema is up to date
            self._setup_database_schema()
            initialization_results['database_setup'] = True
            
            # Generate sample data if requested
            if generate_sample_data:
                self.logger.info("Generating sample data...")
                self.data_generator.generate_sample_data()
                initialization_results['sample_data_generated'] = True
            
            # Setup default workflows
            self.workflow_engine.setup_default_workflows()
            initialization_results['workflows_created'] = True
            
            # Perform initial calculations
            self.aging_analyzer.calculate_invoice_aging()
            
            initialization_results['system_ready'] = True
            self.logger.info("AR Collection System initialized successfully")
            
        except Exception as e:
            error_msg = f"System initialization failed: {str(e)}"
            self.logger.error(error_msg)
            initialization_results['errors'].append(error_msg)
        
        return initialization_results

    def _setup_database_schema(self):
        """Ensure all required database tables exist"""
        schema_file = "ar_database_schema.sql"
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)
                self.logger.info("Database schema setup completed")

    def run_daily_collection_process(self) -> Dict[str, Any]:
        """Execute the complete daily collection process"""
        self.logger.info("Starting daily collection process...")
        
        process_results = {
            'start_time': datetime.now().isoformat(),
            'aging_updated': False,
            'priorities_calculated': False,
            'workflows_triggered': 0,
            'workflows_executed': 0,
            'promises_processed': 0,
            'follow_ups_generated': 0,
            'errors': []
        }
        
        try:
            # Step 1: Update aging analysis
            self.aging_analyzer.calculate_invoice_aging()
            process_results['aging_updated'] = True
            self.logger.info("Aging analysis updated")
            
            # Step 2: Calculate customer priorities
            priority_results = self.prioritizer.generate_collection_queue()
            process_results['priorities_calculated'] = True
            self.logger.info(f"Customer priorities calculated for {len(priority_results)} customers")
            
            # Step 3: Process payment promises
            if self.config.get('promise_follow_up_enabled', True):
                promise_results = self.promise_tracker.process_overdue_promises()
                process_results['promises_processed'] = len(promise_results.get('overdue_promises', []))
                self.logger.info(f"Processed {process_results['promises_processed']} overdue promises")
            
            # Step 4: Trigger workflows
            if self.config.get('workflow_settings', {}).get('auto_trigger', True):
                triggered_workflows = self.workflow_engine.trigger_workflows()
                process_results['workflows_triggered'] = len(triggered_workflows)
                self.logger.info(f"Triggered {len(triggered_workflows)} new workflows")
            
            # Step 5: Execute pending workflows
            if self.config.get('auto_workflow_execution', True):
                execution_results = self.workflow_engine.execute_pending_workflows()
                process_results['workflows_executed'] = execution_results.get('executed', 0)
                self.logger.info(f"Executed {execution_results.get('executed', 0)} workflows")
            
            # Step 6: Generate follow-up activities
            follow_ups = self.activity_tracker.get_follow_up_activities()
            process_results['follow_ups_generated'] = len(follow_ups)
            
            process_results['end_time'] = datetime.now().isoformat()
            process_results['success'] = True
            
            self.logger.info("Daily collection process completed successfully")
            
        except Exception as e:
            error_msg = f"Daily process failed: {str(e)}"
            self.logger.error(error_msg)
            process_results['errors'].append(error_msg)
            process_results['success'] = False
        
        return process_results

    def get_collection_dashboard(self) -> Dict[str, Any]:
        """Generate comprehensive collection dashboard"""
        self.logger.info("Generating collection dashboard...")
        
        try:
            # Key metrics from aging analyzer
            aging_metrics = self.aging_analyzer.generate_dashboard_metrics()
            
            # Collection efficiency metrics
            efficiency_metrics = self.analytics.calculate_collection_efficiency_index()
            dso_metrics = self.analytics.calculate_days_sales_outstanding()
            
            # Priority queue summary
            priority_queue = self.prioritizer.generate_collection_queue()
            
            # Promise tracking summary
            promise_summary = self.promise_tracker.get_promise_performance_report()
            
            # Recent activity summary
            activity_report = self.activity_tracker.create_activity_report(
                start_date=(datetime.now() - timedelta(days=7)).date()
            )
            
            # Workflow status
            workflow_status = self.workflow_engine.get_workflow_status()
            
            dashboard = {
                'report_timestamp': datetime.now().isoformat(),
                'key_metrics': {
                    'total_ar': aging_metrics['total_ar'],
                    'total_invoices': aging_metrics['total_invoices'],
                    'average_days_outstanding': aging_metrics['average_days_outstanding'],
                    'collection_efficiency_index': efficiency_metrics.get('current_cei', 0),
                    'days_sales_outstanding': dso_metrics.get('current_dso', 0)
                },
                'ar_composition': aging_metrics['ar_composition'],
                'ar_percentages': aging_metrics['ar_percentages'],
                'collection_priorities': {
                    'high_priority_customers': len([c for c in priority_queue if c.get('priority_score', 0) >= 80]),
                    'medium_priority_customers': len([c for c in priority_queue if 60 <= c.get('priority_score', 0) < 80]),
                    'low_priority_customers': len([c for c in priority_queue if c.get('priority_score', 0) < 60])
                },
                'promise_tracking': {
                    'active_promises': promise_summary.get('active_promises', 0),
                    'overdue_promises': promise_summary.get('overdue_promises', 0),
                    'promise_fulfillment_rate': promise_summary.get('fulfillment_rate', 0)
                },
                'recent_activity': {
                    'weekly_activities': activity_report['summary']['total_activities'],
                    'successful_contacts': activity_report['summary']['successful_contacts'],
                    'success_rate': activity_report['summary']['success_rate'],
                    'follow_ups_pending': aging_metrics['collection_activity']['activities_this_week']
                },
                'workflow_status': {
                    'active_workflows': workflow_status.get('active_workflow_definitions', 0),
                    'pending_executions': len(workflow_status.get('upcoming_executions', [])),
                    'status_summary': workflow_status.get('status_summary', {})
                },
                'risk_indicators': aging_metrics['risk_indicators']
            }
            
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Dashboard generation failed: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def execute_collection_action(self, action_type: str, customer_id: int, 
                                invoice_id: Optional[int] = None, 
                                details: Optional[Dict] = None) -> Dict[str, Any]:
        """Execute a specific collection action"""
        self.logger.info(f"Executing collection action: {action_type} for customer {customer_id}")
        
        try:
            if action_type == "phone_call":
                return self._execute_phone_call(customer_id, invoice_id, details)
            elif action_type == "send_email":
                return self._execute_email_action(customer_id, invoice_id, details)
            elif action_type == "create_promise":
                return self._create_payment_promise(customer_id, invoice_id, details)
            elif action_type == "escalate":
                return self._escalate_customer(customer_id, details)
            elif action_type == "credit_hold":
                return self._apply_credit_hold(customer_id, details)
            else:
                return {'success': False, 'error': f'Unknown action type: {action_type}'}
                
        except Exception as e:
            error_msg = f"Collection action failed: {str(e)}"
            self.logger.error(error_msg)
            return {'success': False, 'error': error_msg}

    def _execute_phone_call(self, customer_id: int, invoice_id: Optional[int], 
                          details: Optional[Dict]) -> Dict[str, Any]:
        """Execute phone call collection action"""
        contact_person = details.get('contact_person', 'Unknown') if details else 'Unknown'
        duration = details.get('duration_minutes', 10) if details else 10
        result = details.get('result', ActivityResult.CONTACT_MADE) if details else ActivityResult.CONTACT_MADE
        notes = details.get('notes', 'Collection call made') if details else 'Collection call made'
        performer = details.get('performer', 'Collection Team') if details else 'Collection Team'
        
        activity = CollectionActivity(
            customer_id=customer_id,
            invoice_id=invoice_id,
            activity_type=ActivityType.PHONE_CALL,
            activity_date=datetime.now().date(),
            contact_person=contact_person,
            communication_method=CommunicationMethod.PHONE,
            activity_result=result,
            duration_minutes=duration,
            activity_notes=notes,
            performed_by=performer
        )
        
        activity_id = self.activity_tracker.log_activity(activity)
        
        return {
            'success': True,
            'activity_id': activity_id,
            'action': 'phone_call_logged',
            'customer_id': customer_id,
            'invoice_id': invoice_id
        }

    def _execute_email_action(self, customer_id: int, invoice_id: Optional[int], 
                            details: Optional[Dict]) -> Dict[str, Any]:
        """Execute email collection action"""
        template = details.get('template', 'standard_reminder') if details else 'standard_reminder'
        performer = details.get('performer', 'Collection Team') if details else 'Collection Team'
        
        activity = CollectionActivity(
            customer_id=customer_id,
            invoice_id=invoice_id,
            activity_type=ActivityType.EMAIL,
            activity_date=datetime.now().date(),
            contact_person='Email Contact',
            communication_method=CommunicationMethod.EMAIL,
            activity_result=ActivityResult.SENT_SUCCESSFULLY,
            activity_notes=f'Collection email sent using template: {template}',
            performed_by=performer
        )
        
        activity_id = self.activity_tracker.log_activity(activity)
        
        return {
            'success': True,
            'activity_id': activity_id,
            'action': 'email_sent',
            'template': template,
            'customer_id': customer_id,
            'invoice_id': invoice_id
        }

    def _create_payment_promise(self, customer_id: int, invoice_id: Optional[int], 
                              details: Optional[Dict]) -> Dict[str, Any]:
        """Create a payment promise"""
        if not details or 'promised_amount' not in details or 'promised_date' not in details:
            return {'success': False, 'error': 'Promise details required'}
        
        promise_id = self.promise_tracker.create_payment_promise(
            customer_id=customer_id,
            promised_amount=details['promised_amount'],
            promised_payment_date=datetime.strptime(details['promised_date'], '%Y-%m-%d').date(),
            invoice_id=invoice_id,
            contact_person=details.get('contact_person', 'Unknown'),
            contact_method=details.get('contact_method', 'PHONE'),
            notes=details.get('notes', ''),
            created_by=details.get('created_by', 'Collection Team')
        )
        
        # Log the promise creation activity
        activity = CollectionActivity(
            customer_id=customer_id,
            invoice_id=invoice_id,
            activity_type=ActivityType.PHONE_CALL,
            activity_date=datetime.now().date(),
            contact_person=details.get('contact_person', 'Unknown'),
            communication_method=CommunicationMethod.PHONE,
            activity_result=ActivityResult.PROMISE_MADE,
            activity_notes=f'Payment promise created: ${details["promised_amount"]} by {details["promised_date"]}',
            performed_by=details.get('created_by', 'Collection Team'),
            follow_up_required=True,
            next_action_date=datetime.strptime(details['promised_date'], '%Y-%m-%d').date()
        )
        
        activity_id = self.activity_tracker.log_activity(activity)
        
        return {
            'success': True,
            'promise_id': promise_id,
            'activity_id': activity_id,
            'action': 'promise_created',
            'customer_id': customer_id,
            'promised_amount': details['promised_amount'],
            'promised_date': details['promised_date']
        }

    def _escalate_customer(self, customer_id: int, details: Optional[Dict]) -> Dict[str, Any]:
        """Escalate customer to higher collection level"""
        assigned_to = details.get('assigned_to', 'Collection Supervisor') if details else 'Collection Supervisor'
        reason = details.get('reason', 'Collection escalation') if details else 'Collection escalation'
        
        # Update customer priority
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE customers 
                SET collection_priority = 'HIGH',
                    updated_date = CURRENT_TIMESTAMP
                WHERE customer_id = ?
            """, (customer_id,))
            conn.commit()
        
        # Log escalation activity
        activity = CollectionActivity(
            customer_id=customer_id,
            activity_type=ActivityType.ESCALATION,
            activity_date=datetime.now().date(),
            contact_person='Internal Escalation',
            communication_method=CommunicationMethod.PHONE,
            activity_result=ActivityResult.CONTACT_MADE,
            activity_notes=f'Customer escalated: {reason}',
            assigned_to=assigned_to,
            collection_stage='ESCALATED',
            performed_by='System'
        )
        
        activity_id = self.activity_tracker.log_activity(activity)
        
        return {
            'success': True,
            'activity_id': activity_id,
            'action': 'customer_escalated',
            'customer_id': customer_id,
            'assigned_to': assigned_to
        }

    def _apply_credit_hold(self, customer_id: int, details: Optional[Dict]) -> Dict[str, Any]:
        """Apply credit hold to customer"""
        reason = details.get('reason', 'Collection action') if details else 'Collection action'
        authorized_by = details.get('authorized_by', 'System') if details else 'System'
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Apply credit hold
            cursor.execute("""
                UPDATE customers 
                SET is_credit_hold = TRUE,
                    updated_date = CURRENT_TIMESTAMP
                WHERE customer_id = ?
            """, (customer_id,))
            
            # Record in credit history
            cursor.execute("""
                INSERT INTO credit_history
                (customer_id, event_date, event_type, reason, authorized_by)
                VALUES (?, ?, 'CREDIT_HOLD', ?, ?)
            """, (customer_id, datetime.now().date(), reason, authorized_by))
            
            conn.commit()
        
        return {
            'success': True,
            'action': 'credit_hold_applied',
            'customer_id': customer_id,
            'reason': reason,
            'authorized_by': authorized_by
        }

    def generate_comprehensive_report(self, report_type: str = "monthly") -> Dict[str, Any]:
        """Generate comprehensive collection performance report"""
        self.logger.info(f"Generating {report_type} collection report...")
        
        # Determine date range based on report type
        end_date = datetime.now().date()
        if report_type == "daily":
            start_date = end_date
        elif report_type == "weekly":
            start_date = end_date - timedelta(days=7)
        elif report_type == "monthly":
            start_date = end_date - timedelta(days=30)
        elif report_type == "quarterly":
            start_date = end_date - timedelta(days=90)
        else:
            start_date = end_date - timedelta(days=30)  # Default to monthly
        
        try:
            # Collection efficiency analysis
            efficiency_data = self.analytics.generate_comprehensive_dashboard()
            
            # Aging analysis
            aging_report = self.aging_analyzer.generate_aging_report()
            
            # Activity effectiveness
            activity_effectiveness = self.activity_tracker.get_collection_effectiveness(start_date, end_date)
            
            # Promise performance
            promise_performance = self.promise_tracker.get_promise_performance_report()
            
            # Workflow performance
            workflow_status = self.workflow_engine.get_workflow_status()
            
            # Top performing actions
            priority_queue = self.prioritizer.generate_collection_queue()
            
            comprehensive_report = {
                'report_metadata': {
                    'report_type': report_type,
                    'period_start': start_date.isoformat(),
                    'period_end': end_date.isoformat(),
                    'generated_at': datetime.now().isoformat()
                },
                'executive_summary': {
                    'total_ar': aging_report['summary']['total_outstanding'],
                    'collection_efficiency': efficiency_data.get('current_cei', 0),
                    'days_sales_outstanding': efficiency_data.get('current_dso', 0),
                    'promise_fulfillment_rate': promise_performance.get('fulfillment_rate', 0),
                    'high_priority_accounts': len([c for c in priority_queue if c.get('priority_score', 0) >= 80])
                },
                'detailed_analysis': {
                    'aging_analysis': aging_report,
                    'collection_efficiency': efficiency_data,
                    'activity_effectiveness': activity_effectiveness,
                    'promise_performance': promise_performance,
                    'workflow_performance': workflow_status
                },
                'recommendations': self._generate_recommendations(
                    efficiency_data, aging_report, activity_effectiveness, promise_performance
                )
            }
            
            return comprehensive_report
            
        except Exception as e:
            self.logger.error(f"Report generation failed: {str(e)}")
            return {'error': str(e), 'timestamp': datetime.now().isoformat()}

    def _generate_recommendations(self, efficiency_data: Dict, aging_report: Dict, 
                                activity_data: Dict, promise_data: Dict) -> List[Dict[str, str]]:
        """Generate actionable recommendations based on analysis"""
        recommendations = []
        
        # Aging-based recommendations
        if aging_report['summary']['aging_buckets'].get('120+', {}).get('percentage', 0) > 10:
            recommendations.append({
                'category': 'Aging',
                'priority': 'High',
                'recommendation': 'Over 10% of AR is 120+ days old. Consider legal action or write-offs for oldest accounts.',
                'action': 'Review accounts over 120 days for legal referral'
            })
        
        # Efficiency recommendations
        if efficiency_data.get('current_cei', 0) < 80:
            recommendations.append({
                'category': 'Efficiency',
                'priority': 'Medium',
                'recommendation': 'Collection Efficiency Index below 80%. Increase collection activities and follow-ups.',
                'action': 'Implement more aggressive collection workflows'
            })
        
        # Promise performance recommendations
        if promise_data.get('fulfillment_rate', 0) < 70:
            recommendations.append({
                'category': 'Promises',
                'priority': 'High',
                'recommendation': 'Promise fulfillment rate below 70%. Improve promise tracking and follow-up processes.',
                'action': 'Enhance promise monitoring and customer vetting'
            })
        
        # Activity effectiveness recommendations
        activity_success_rate = activity_data.get('promise_statistics', {}).get('fulfillment_rate', 0)
        if activity_success_rate < 60:
            recommendations.append({
                'category': 'Activities',
                'priority': 'Medium',
                'recommendation': 'Collection activity success rate low. Review communication methods and timing.',
                'action': 'Analyze and optimize collection activity approaches'
            })
        
        return recommendations

# Usage example and main execution
if __name__ == "__main__":
    # Initialize the AR Collection Manager
    manager = ARCollectionManager()
    
    # Initialize system with sample data
    print("Initializing AR Collection Management System...")
    init_results = manager.initialize_system(generate_sample_data=True)
    print(f"Initialization results: {init_results}")
    
    if init_results['system_ready']:
        # Run daily collection process
        print("\nRunning daily collection process...")
        daily_results = manager.run_daily_collection_process()
        print(f"Daily process results: {daily_results}")
        
        # Generate dashboard
        print("\nGenerating collection dashboard...")
        dashboard = manager.get_collection_dashboard()
        print(f"Dashboard key metrics: {dashboard.get('key_metrics', {})}")
        
        # Execute sample collection action
        print("\nExecuting sample collection action...")
        action_result = manager.execute_collection_action(
            action_type="phone_call",
            customer_id=1,
            details={
                'contact_person': 'John Smith',
                'duration_minutes': 15,
                'result': ActivityResult.PROMISE_MADE,
                'notes': 'Customer agreed to pay $5000 by Friday',
                'performer': 'Sarah Johnson'
            }
        )
        print(f"Collection action result: {action_result}")
        
        # Generate comprehensive report
        print("\nGenerating monthly collection report...")
        report = manager.generate_comprehensive_report("monthly")
        print(f"Report executive summary: {report.get('executive_summary', {})}")
        
        print("\nAR Collection Management System demonstration completed successfully!")
    else:
        print("System initialization failed. Please check the logs for details.")