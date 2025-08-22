"""
Comprehensive Test Suite for AR Collection Management System
Tests all components and integration scenarios
"""

import unittest
import sqlite3
import os
import tempfile
import shutil
from datetime import datetime, timedelta, date
from decimal import Decimal
import json

# Import all AR system modules
from ar_data_generator import ARDataGenerator
from ar_prioritization import CustomerPrioritizer
from ar_promise_tracker import PaymentPromiseTracker
from ar_analytics import CollectionAnalytics
from ar_workflow_engine import CollectionWorkflowEngine, WorkflowTrigger, WorkflowAction, ActionType
from ar_activity_tracker import CollectionActivityTracker, CollectionActivity, ActivityType as ActType, ActivityResult, CommunicationMethod
from ar_aging_analysis import AgingAnalyzer
from ar_collection_manager import ARCollectionManager
from ar_config import ConfigManager, ARCollectionConfig

class TestARDataGenerator(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.data_generator = ARDataGenerator(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_database_setup(self):
        """Test database schema creation"""
        # Check if tables exist
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            expected_tables = ['customers', 'invoices', 'payments', 'payment_promises', 
                             'collection_activities', 'disputes', 'collection_metrics']
            
            for table in expected_tables:
                self.assertIn(table, tables, f"Table {table} not found")

    def test_sample_data_generation(self):
        """Test sample data generation"""
        self.data_generator.generate_sample_data()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Check customers were created
            cursor.execute("SELECT COUNT(*) FROM customers")
            customer_count = cursor.fetchone()[0]
            self.assertGreater(customer_count, 0, "No customers generated")
            
            # Check invoices were created
            cursor.execute("SELECT COUNT(*) FROM invoices")
            invoice_count = cursor.fetchone()[0]
            self.assertGreater(invoice_count, 0, "No invoices generated")
            
            # Check payments were created
            cursor.execute("SELECT COUNT(*) FROM payments")
            payment_count = cursor.fetchone()[0]
            self.assertGreater(payment_count, 0, "No payments generated")

class TestCustomerPrioritizer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.data_generator = ARDataGenerator(self.db_path)
        self.prioritizer = CustomerPrioritizer(self.db_path)
        
        # Generate test data
        self.data_generator.generate_sample_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_priority_score_calculation(self):
        """Test customer priority score calculation"""
        # Get a customer ID
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id FROM customers LIMIT 1")
            customer_id = cursor.fetchone()[0]
        
        # Calculate priority score
        score_result = self.prioritizer.calculate_customer_priority_score(customer_id)
        
        self.assertIn('priority_score', score_result)
        self.assertIsInstance(score_result['priority_score'], (int, float))
        self.assertGreaterEqual(score_result['priority_score'], 0)
        self.assertLessEqual(score_result['priority_score'], 100)

    def test_collection_queue_generation(self):
        """Test collection queue generation"""
        queue = self.prioritizer.generate_collection_queue()
        
        self.assertIsInstance(queue, list)
        self.assertGreater(len(queue), 0, "Collection queue is empty")
        
        # Check queue is sorted by priority (descending)
        if len(queue) > 1:
            for i in range(len(queue) - 1):
                self.assertGreaterEqual(
                    queue[i].get('priority_score', 0),
                    queue[i + 1].get('priority_score', 0),
                    "Collection queue not properly sorted"
                )

class TestPaymentPromiseTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.data_generator = ARDataGenerator(self.db_path)
        self.promise_tracker = PaymentPromiseTracker(self.db_path)
        
        # Generate test data
        self.data_generator.generate_sample_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_create_payment_promise(self):
        """Test payment promise creation"""
        # Get a customer ID
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id FROM customers LIMIT 1")
            customer_id = cursor.fetchone()[0]
        
        # Create a payment promise
        promise_id = self.promise_tracker.create_payment_promise(
            customer_id=customer_id,
            promised_amount=Decimal('5000.00'),
            promised_payment_date=(datetime.now() + timedelta(days=7)).date(),
            contact_person="Test Contact",
            contact_method="PHONE",
            notes="Test promise",
            created_by="Test User"
        )
        
        self.assertIsNotNone(promise_id)
        
        # Verify promise was created
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM payment_promises WHERE promise_id = ?", (promise_id,))
            promise = cursor.fetchone()
            self.assertIsNotNone(promise)

    def test_promise_status_update(self):
        """Test payment promise status updates"""
        # Create a promise first
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id FROM customers LIMIT 1")
            customer_id = cursor.fetchone()[0]
        
        promise_id = self.promise_tracker.create_payment_promise(
            customer_id=customer_id,
            promised_amount=Decimal('1000.00'),
            promised_payment_date=datetime.now().date(),
            contact_person="Test Contact"
        )
        
        # Update promise status
        success = self.promise_tracker.update_promise_status(
            promise_id=promise_id,
            new_status="KEPT",
            actual_payment_amount=Decimal('1000.00'),
            actual_payment_date=datetime.now().date()
        )
        
        self.assertTrue(success)

class TestCollectionAnalytics(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.data_generator = ARDataGenerator(self.db_path)
        self.analytics = CollectionAnalytics(self.db_path)
        
        # Generate test data
        self.data_generator.generate_sample_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_collection_efficiency_calculation(self):
        """Test collection efficiency index calculation"""
        cei_result = self.analytics.calculate_collection_efficiency_index()
        
        self.assertIn('current_cei', cei_result)
        self.assertIsInstance(cei_result['current_cei'], (int, float))
        self.assertGreaterEqual(cei_result['current_cei'], 0)

    def test_days_sales_outstanding_calculation(self):
        """Test DSO calculation"""
        dso_result = self.analytics.calculate_days_sales_outstanding()
        
        self.assertIn('current_dso', dso_result)
        self.assertIsInstance(dso_result['current_dso'], (int, float))
        self.assertGreaterEqual(dso_result['current_dso'], 0)

    def test_comprehensive_dashboard(self):
        """Test comprehensive dashboard generation"""
        dashboard = self.analytics.generate_comprehensive_dashboard()
        
        self.assertIn('collection_efficiency', dashboard)
        self.assertIn('aging_analysis', dashboard)
        self.assertIn('performance_metrics', dashboard)

class TestWorkflowEngine(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.data_generator = ARDataGenerator(self.db_path)
        self.workflow_engine = CollectionWorkflowEngine(self.db_path)
        
        # Generate test data
        self.data_generator.generate_sample_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_workflow_creation(self):
        """Test workflow definition creation"""
        trigger = WorkflowTrigger(days_past_due=30, amount_threshold=1000.0)
        actions = [
            WorkflowAction(ActionType.EMAIL_REMINDER, delay_days=0),
            WorkflowAction(ActionType.PHONE_CALL, delay_days=3)
        ]
        
        workflow_id = self.workflow_engine.create_workflow_definition(
            "Test Workflow", trigger, actions
        )
        
        self.assertIsNotNone(workflow_id)
        self.assertIsInstance(workflow_id, int)

    def test_workflow_triggering(self):
        """Test workflow triggering"""
        # Create a simple workflow first
        trigger = WorkflowTrigger(days_past_due=1, amount_threshold=100.0)
        actions = [WorkflowAction(ActionType.EMAIL_REMINDER)]
        
        self.workflow_engine.create_workflow_definition("Test Trigger", trigger, actions)
        
        # Trigger workflows
        triggered = self.workflow_engine.trigger_workflows()
        
        self.assertIsInstance(triggered, list)

    def test_workflow_execution(self):
        """Test workflow execution"""
        # Setup and trigger a workflow
        trigger = WorkflowTrigger(days_past_due=1, amount_threshold=0.0)
        actions = [WorkflowAction(ActionType.EMAIL_REMINDER)]
        
        self.workflow_engine.create_workflow_definition("Test Execution", trigger, actions)
        triggered = self.workflow_engine.trigger_workflows()
        
        if triggered:
            # Execute pending workflows
            results = self.workflow_engine.execute_pending_workflows()
            self.assertIn('executed', results)
            self.assertIn('failed', results)

class TestActivityTracker(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.data_generator = ARDataGenerator(self.db_path)
        self.activity_tracker = CollectionActivityTracker(self.db_path)
        
        # Generate test data
        self.data_generator.generate_sample_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_activity_logging(self):
        """Test activity logging"""
        # Get a customer ID
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id FROM customers LIMIT 1")
            customer_id = cursor.fetchone()[0]
        
        # Create an activity
        activity = CollectionActivity(
            customer_id=customer_id,
            activity_type=ActType.PHONE_CALL,
            activity_date=datetime.now().date(),
            contact_person="Test Contact",
            communication_method=CommunicationMethod.PHONE,
            activity_result=ActivityResult.CONTACT_MADE,
            duration_minutes=10,
            activity_notes="Test call",
            performed_by="Test User"
        )
        
        activity_id = self.activity_tracker.log_activity(activity)
        
        self.assertIsNotNone(activity_id)
        self.assertIsInstance(activity_id, int)

    def test_activity_history_retrieval(self):
        """Test activity history retrieval"""
        # Get a customer ID
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT customer_id FROM customers LIMIT 1")
            customer_id = cursor.fetchone()[0]
        
        # Get activity history
        history = self.activity_tracker.get_customer_activity_history(customer_id, days_back=30)
        
        self.assertIsInstance(history, list)

    def test_follow_up_tracking(self):
        """Test follow-up activity tracking"""
        follow_ups = self.activity_tracker.get_follow_up_activities()
        
        self.assertIsInstance(follow_ups, list)

class TestAgingAnalyzer(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.data_generator = ARDataGenerator(self.db_path)
        self.aging_analyzer = AgingAnalyzer(self.db_path)
        
        # Generate test data
        self.data_generator.generate_sample_data()

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_aging_calculation(self):
        """Test aging calculation"""
        self.aging_analyzer.calculate_invoice_aging()
        
        # Check that aging was calculated
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM invoices WHERE aging_bucket IS NOT NULL")
            count = cursor.fetchone()[0]
            self.assertGreater(count, 0, "No aging buckets calculated")

    def test_aging_report_generation(self):
        """Test aging report generation"""
        report = self.aging_analyzer.generate_aging_report()
        
        self.assertIn('summary', report)
        self.assertIn('customer_analysis', report)
        self.assertIn('risk_analysis', report)

    def test_collection_priorities(self):
        """Test collection priority generation"""
        priorities = self.aging_analyzer.get_collection_priorities_by_aging(limit=10)
        
        self.assertIsInstance(priorities, list)
        self.assertLessEqual(len(priorities), 10)

    def test_dashboard_metrics(self):
        """Test dashboard metrics generation"""
        metrics = self.aging_analyzer.generate_dashboard_metrics()
        
        self.assertIn('total_ar', metrics)
        self.assertIn('ar_composition', metrics)
        self.assertIn('collection_activity', metrics)

class TestConfigManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, "test_config.json")
        self.config_manager = ConfigManager(self.config_file)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_config_creation(self):
        """Test configuration file creation"""
        self.assertTrue(os.path.exists(self.config_file))

    def test_config_validation(self):
        """Test configuration validation"""
        validation = self.config_manager.validate_config()
        
        self.assertIn('valid', validation)
        self.assertIn('errors', validation)
        self.assertIn('warnings', validation)

    def test_config_updates(self):
        """Test configuration updates"""
        updates = {
            'collection_targets': {
                'weekly_calls': 200
            }
        }
        
        success = self.config_manager.update_config(updates)
        self.assertTrue(success)
        
        # Verify update
        config = self.config_manager.get_config()
        self.assertEqual(config.collection_targets.weekly_calls, 200)

    def test_config_backup_restore(self):
        """Test configuration backup and restore"""
        # Create backup
        backup_path = os.path.join(self.temp_dir, "config_backup.json")
        success = self.config_manager.backup_config(backup_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(backup_path))
        
        # Modify config
        self.config_manager.update_config({'environment': 'test'})
        
        # Restore backup
        success = self.config_manager.restore_config(backup_path)
        self.assertTrue(success)

class TestARCollectionManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_ar.db")
        self.manager = ARCollectionManager(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_system_initialization(self):
        """Test system initialization"""
        results = self.manager.initialize_system(generate_sample_data=True)
        
        self.assertIn('database_setup', results)
        self.assertIn('sample_data_generated', results)
        self.assertIn('workflows_created', results)
        self.assertIn('system_ready', results)
        self.assertTrue(results['system_ready'])

    def test_daily_collection_process(self):
        """Test daily collection process"""
        # Initialize system first
        self.manager.initialize_system(generate_sample_data=True)
        
        # Run daily process
        results = self.manager.run_daily_collection_process()
        
        self.assertIn('aging_updated', results)
        self.assertIn('priorities_calculated', results)
        self.assertIn('workflows_triggered', results)

    def test_dashboard_generation(self):
        """Test dashboard generation"""
        # Initialize system first
        self.manager.initialize_system(generate_sample_data=True)
        
        # Generate dashboard
        dashboard = self.manager.get_collection_dashboard()
        
        self.assertIn('key_metrics', dashboard)
        self.assertIn('ar_composition', dashboard)
        self.assertIn('collection_priorities', dashboard)

    def test_collection_actions(self):
        """Test collection action execution"""
        # Initialize system first
        self.manager.initialize_system(generate_sample_data=True)
        
        # Execute a phone call action
        result = self.manager.execute_collection_action(
            action_type="phone_call",
            customer_id=1,
            details={
                'contact_person': 'Test Contact',
                'duration_minutes': 10,
                'notes': 'Test call',
                'performer': 'Test User'
            }
        )
        
        self.assertTrue(result.get('success', False))

    def test_comprehensive_report(self):
        """Test comprehensive report generation"""
        # Initialize system first
        self.manager.initialize_system(generate_sample_data=True)
        
        # Generate report
        report = self.manager.generate_comprehensive_report("weekly")
        
        self.assertIn('report_metadata', report)
        self.assertIn('executive_summary', report)
        self.assertIn('detailed_analysis', report)

class TestIntegrationScenarios(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_integration.db")
        self.manager = ARCollectionManager(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def test_complete_collection_workflow(self):
        """Test complete end-to-end collection workflow"""
        # 1. Initialize system
        init_results = self.manager.initialize_system(generate_sample_data=True)
        self.assertTrue(init_results['system_ready'])
        
        # 2. Run daily process
        daily_results = self.manager.run_daily_collection_process()
        self.assertTrue(daily_results.get('aging_updated', False))
        
        # 3. Get priorities
        priorities = self.manager.aging_analyzer.get_collection_priorities_by_aging(limit=5)
        self.assertGreater(len(priorities), 0)
        
        # 4. Execute collection action on top priority
        if priorities:
            top_priority = priorities[0]
            action_result = self.manager.execute_collection_action(
                action_type="phone_call",
                customer_id=top_priority['customer_id'],
                invoice_id=top_priority['invoice_id'],
                details={
                    'contact_person': top_priority['customer_name'],
                    'duration_minutes': 15,
                    'result': ActivityResult.PROMISE_MADE,
                    'notes': 'Customer agreed to payment plan'
                }
            )
            self.assertTrue(action_result.get('success', False))
        
        # 5. Generate dashboard
        dashboard = self.manager.get_collection_dashboard()
        self.assertIn('key_metrics', dashboard)
        
        # 6. Generate report
        report = self.manager.generate_comprehensive_report("daily")
        self.assertIn('executive_summary', report)

    def test_promise_to_payment_workflow(self):
        """Test promise creation to payment tracking workflow"""
        # Initialize system
        self.manager.initialize_system(generate_sample_data=True)
        
        # Get a customer with outstanding invoices
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.customer_id, i.invoice_id, i.outstanding_amount
                FROM customers c
                JOIN invoices i ON c.customer_id = i.customer_id
                WHERE i.status = 'OPEN' AND i.outstanding_amount > 0
                LIMIT 1
            """)
            result = cursor.fetchone()
        
        if result:
            customer_id, invoice_id, outstanding_amount = result
            
            # Create payment promise
            promise_result = self.manager.execute_collection_action(
                action_type="create_promise",
                customer_id=customer_id,
                invoice_id=invoice_id,
                details={
                    'promised_amount': float(outstanding_amount),
                    'promised_date': (datetime.now() + timedelta(days=7)).strftime('%Y-%m-%d'),
                    'contact_person': 'Test Contact',
                    'notes': 'Payment arrangement made',
                    'created_by': 'Test User'
                }
            )
            
            self.assertTrue(promise_result.get('success', False))
            
            # Track promise
            promise_performance = self.manager.promise_tracker.get_promise_performance_report()
            self.assertIn('active_promises', promise_performance)

def run_performance_tests():
    """Run basic performance tests"""
    print("Running performance tests...")
    
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "perf_test.db")
    
    try:
        # Test data generation performance
        start_time = datetime.now()
        data_generator = ARDataGenerator(db_path)
        data_generator.generate_sample_data()
        generation_time = (datetime.now() - start_time).total_seconds()
        print(f"Data generation: {generation_time:.2f} seconds")
        
        # Test aging analysis performance
        start_time = datetime.now()
        aging_analyzer = AgingAnalyzer(db_path)
        aging_analyzer.calculate_invoice_aging()
        aging_time = (datetime.now() - start_time).total_seconds()
        print(f"Aging analysis: {aging_time:.2f} seconds")
        
        # Test dashboard generation performance
        start_time = datetime.now()
        manager = ARCollectionManager(db_path)
        dashboard = manager.get_collection_dashboard()
        dashboard_time = (datetime.now() - start_time).total_seconds()
        print(f"Dashboard generation: {dashboard_time:.2f} seconds")
        
        print("Performance tests completed successfully")
        
    finally:
        shutil.rmtree(temp_dir)

if __name__ == '__main__':
    # Run unit tests
    print("Running AR Collection System Test Suite...")
    print("=" * 50)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestARDataGenerator,
        TestCustomerPrioritizer,
        TestPaymentPromiseTracker,
        TestCollectionAnalytics,
        TestWorkflowEngine,
        TestActivityTracker,
        TestAgingAnalyzer,
        TestConfigManager,
        TestARCollectionManager,
        TestIntegrationScenarios
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    # Print summary
    print("\n" + "=" * 50)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, error in result.failures:
            print(f"- {test}: {error}")
    
    if result.errors:
        print("\nErrors:")
        for test, error in result.errors:
            print(f"- {test}: {error}")
    
    # Run performance tests
    print("\n" + "=" * 50)
    run_performance_tests()
    
    print("\nTest suite completed!")