#!/usr/bin/env python3
"""
Accounts Receivable Collection Manager
Main application interface
"""

import os
import sys
from datetime import date, datetime, timedelta
from typing import List, Dict, Any
import argparse

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import (
    DatabaseManager, CustomerManager, InvoiceManager, 
    PaymentManager, CollectionActivityManager, PaymentPromiseManager
)
from collection_prioritizer import CollectionPrioritizer, CollectionEfficiencyCalculator

class ARCollectionManager:
    """Main application class for AR Collection Manager"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.customer_manager = CustomerManager(self.db_manager)
        self.invoice_manager = InvoiceManager(self.db_manager)
        self.payment_manager = PaymentManager(self.db_manager)
        self.activity_manager = CollectionActivityManager(self.db_manager)
        self.promise_manager = PaymentPromiseManager(self.db_manager)
        self.prioritizer = CollectionPrioritizer(self.db_manager)
        self.efficiency_calculator = CollectionEfficiencyCalculator(self.db_manager)
    
    def run_interactive_mode(self):
        """Run the interactive command-line interface"""
        print("="*60)
        print("  ACCOUNTS RECEIVABLE COLLECTION MANAGER")
        print("="*60)
        print()
        
        while True:
            self.show_main_menu()
            choice = input("\nEnter your choice (1-9, or 'q' to quit): ").strip().lower()
            
            if choice == 'q' or choice == 'quit':
                print("\nThank you for using AR Collection Manager!")
                break
            elif choice == '1':
                self.customer_menu()
            elif choice == '2':
                self.invoice_menu()
            elif choice == '3':
                self.payment_menu()
            elif choice == '4':
                self.collection_activity_menu()
            elif choice == '5':
                self.payment_promise_menu()
            elif choice == '6':
                self.collection_priority_menu()
            elif choice == '7':
                self.efficiency_reports_menu()
            elif choice == '8':
                self.dashboard_menu()
            elif choice == '9':
                self.sample_data_menu()
            else:
                print("Invalid choice. Please try again.")
                input("Press Enter to continue...")
    
    def show_main_menu(self):
        """Display the main menu"""
        print("\n" + "="*40)
        print("MAIN MENU")
        print("="*40)
        print("1. Customer Management")
        print("2. Invoice Management")
        print("3. Payment Processing")
        print("4. Collection Activities")
        print("5. Payment Promises")
        print("6. Collection Priorities")
        print("7. Efficiency Reports")
        print("8. Dashboard")
        print("9. Sample Data")
        print("Q. Quit")
    
    def customer_menu(self):
        """Customer management menu"""
        while True:
            print("\n" + "-"*30)
            print("CUSTOMER MANAGEMENT")
            print("-"*30)
            print("1. Add New Customer")
            print("2. View Customer Details")
            print("3. List All Customers")
            print("4. Update Customer")
            print("5. Customer Summary Report")
            print("B. Back to Main Menu")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'b':
                break
            elif choice == '1':
                self.add_customer()
            elif choice == '2':
                self.view_customer_details()
            elif choice == '3':
                self.list_customers()
            elif choice == '4':
                self.update_customer()
            elif choice == '5':
                self.customer_summary_report()
            else:
                print("Invalid choice.")
    
    def add_customer(self):
        """Add a new customer"""
        print("\n--- Add New Customer ---")
        
        customer_data = {}
        customer_data['customer_name'] = input("Customer Name: ").strip()
        customer_data['company_name'] = input("Company Name (optional): ").strip() or None
        customer_data['email'] = input("Email: ").strip() or None
        customer_data['phone'] = input("Phone: ").strip() or None
        customer_data['address'] = input("Address: ").strip() or None
        
        try:
            credit_limit = input("Credit Limit (default 0): ").strip()
            customer_data['credit_limit'] = float(credit_limit) if credit_limit else 0
        except ValueError:
            customer_data['credit_limit'] = 0
        
        try:
            payment_terms = input("Payment Terms in days (default 30): ").strip()
            customer_data['payment_terms'] = int(payment_terms) if payment_terms else 30
        except ValueError:
            customer_data['payment_terms'] = 30
        
        risk_rating = input("Risk Rating (LOW/MEDIUM/HIGH, default LOW): ").strip().upper()
        customer_data['risk_rating'] = risk_rating if risk_rating in ['LOW', 'MEDIUM', 'HIGH'] else 'LOW'
        
        customer_data['notes'] = input("Notes (optional): ").strip() or None
        
        try:
            customer_id = self.customer_manager.add_customer(customer_data)
            print(f"\nCustomer added successfully! Customer ID: {customer_id}")
        except Exception as e:
            print(f"Error adding customer: {e}")
        
        input("Press Enter to continue...")
    
    def view_customer_details(self):
        """View customer details"""
        print("\n--- View Customer Details ---")
        
        try:
            customer_id = int(input("Enter Customer ID: ").strip())
        except ValueError:
            print("Invalid Customer ID")
            return
        
        customer = self.customer_manager.get_customer(customer_id)
        if not customer:
            print("Customer not found")
            return
        
        print(f"\n--- Customer Details ---")
        print(f"Customer ID: {customer['customer_id']}")
        print(f"Name: {customer['customer_name']}")
        print(f"Company: {customer['company_name'] or 'N/A'}")
        print(f"Email: {customer['email'] or 'N/A'}")
        print(f"Phone: {customer['phone'] or 'N/A'}")
        print(f"Address: {customer['address'] or 'N/A'}")
        print(f"Credit Limit: ${customer['credit_limit']:,.2f}")
        print(f"Payment Terms: {customer['payment_terms']} days")
        print(f"Risk Rating: {customer['risk_rating']}")
        print(f"Last Contact: {customer['last_contact_date'] or 'Never'}")
        print(f"Notes: {customer['notes'] or 'None'}")
        
        # Show invoices
        invoices = self.invoice_manager.get_customer_invoices(customer_id)
        if invoices:
            print(f"\n--- Recent Invoices ---")
            for inv in invoices[:5]:  # Show last 5 invoices
                print(f"Invoice #{inv['invoice_number']}: ${inv['balance']:,.2f} "
                      f"(Due: {inv['due_date']}, Status: {inv['status']})")
        
        input("Press Enter to continue...")
    
    def list_customers(self):
        """List all customers"""
        print("\n--- All Customers ---")
        
        customers = self.customer_manager.get_all_customers()
        if not customers:
            print("No customers found")
            return
        
        print(f"{'ID':<5} {'Name':<25} {'Company':<25} {'Risk':<8} {'Credit Limit':<12}")
        print("-" * 80)
        
        for customer in customers:
            print(f"{customer['customer_id']:<5} "
                  f"{customer['customer_name'][:24]:<25} "
                  f"{(customer['company_name'] or '')[:24]:<25} "
                  f"{customer['risk_rating']:<8} "
                  f"${customer['credit_limit']:<11,.0f}")
        
        input("Press Enter to continue...")
    
    def customer_summary_report(self):
        """Show customer summary report"""
        print("\n--- Customer Summary Report ---")
        
        customers = self.customer_manager.get_customer_summary()
        if not customers:
            print("No customers found")
            return
        
        print(f"{'ID':<5} {'Name':<20} {'Outstanding':<12} {'Overdue':<12} {'Risk':<8} {'Broken Promises':<15}")
        print("-" * 85)
        
        for customer in customers:
            outstanding = customer['outstanding_balance'] or 0
            overdue = customer['overdue_balance'] or 0
            broken_promises = customer['broken_promises'] or 0
            
            print(f"{customer['customer_id']:<5} "
                  f"{customer['customer_name'][:19]:<20} "
                  f"${outstanding:<11,.0f} "
                  f"${overdue:<11,.0f} "
                  f"{customer['risk_rating']:<8} "
                  f"{broken_promises:<15}")
        
        input("Press Enter to continue...")
    
    def invoice_menu(self):
        """Invoice management menu"""
        while True:
            print("\n" + "-"*30)
            print("INVOICE MANAGEMENT")
            print("-"*30)
            print("1. Add New Invoice")
            print("2. View Invoice Details")
            print("3. List Overdue Invoices")
            print("4. Aging Report")
            print("5. Customer Invoices")
            print("B. Back to Main Menu")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'b':
                break
            elif choice == '1':
                self.add_invoice()
            elif choice == '2':
                self.view_invoice_details()
            elif choice == '3':
                self.list_overdue_invoices()
            elif choice == '4':
                self.aging_report()
            elif choice == '5':
                self.customer_invoices()
            else:
                print("Invalid choice.")
    
    def add_invoice(self):
        """Add a new invoice"""
        print("\n--- Add New Invoice ---")
        
        try:
            customer_id = int(input("Customer ID: ").strip())
            # Verify customer exists
            customer = self.customer_manager.get_customer(customer_id)
            if not customer:
                print("Customer not found")
                return
        except ValueError:
            print("Invalid Customer ID")
            return
        
        invoice_data = {}
        invoice_data['customer_id'] = customer_id
        invoice_data['invoice_number'] = input("Invoice Number: ").strip()
        
        try:
            invoice_date_str = input("Invoice Date (YYYY-MM-DD): ").strip()
            invoice_data['invoice_date'] = datetime.strptime(invoice_date_str, '%Y-%m-%d').date()
        except ValueError:
            print("Invalid date format")
            return
        
        try:
            due_date_str = input("Due Date (YYYY-MM-DD): ").strip()
            invoice_data['due_date'] = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            print("Invalid date format")
            return
        
        try:
            invoice_data['amount'] = float(input("Amount: $").strip())
        except ValueError:
            print("Invalid amount")
            return
        
        invoice_data['description'] = input("Description (optional): ").strip() or None
        
        try:
            invoice_id = self.invoice_manager.add_invoice(invoice_data)
            print(f"\nInvoice added successfully! Invoice ID: {invoice_id}")
        except Exception as e:
            print(f"Error adding invoice: {e}")
        
        input("Press Enter to continue...")
    
    def list_overdue_invoices(self):
        """List overdue invoices"""
        print("\n--- Overdue Invoices ---")
        
        overdue = self.invoice_manager.get_overdue_invoices()
        if not overdue:
            print("No overdue invoices found")
            return
        
        print(f"{'Invoice#':<15} {'Customer':<20} {'Days Overdue':<12} {'Balance':<12} {'Risk':<8}")
        print("-" * 75)
        
        for inv in overdue:
            print(f"{inv['invoice_number']:<15} "
                  f"{inv['customer_name'][:19]:<20} "
                  f"{int(inv['days_overdue']):<12} "
                  f"${inv['balance']:<11,.0f} "
                  f"{inv['risk_rating']:<8}")
        
        input("Press Enter to continue...")
    
    def aging_report(self):
        """Show aging report"""
        print("\n--- Aging Report ---")
        
        aging = self.invoice_manager.get_aging_report()
        if not aging:
            print("No data available")
            return
        
        total = aging.get('total_balance', 0)
        current = aging.get('current_balance', 0)
        days_1_30 = aging.get('days_1_30', 0)
        days_31_60 = aging.get('days_31_60', 0)
        days_61_90 = aging.get('days_61_90', 0)
        days_over_90 = aging.get('days_over_90', 0)
        
        print(f"Total Outstanding: ${total:,.2f}")
        print(f"Current (not overdue): ${current:,.2f}")
        print(f"1-30 days overdue: ${days_1_30:,.2f}")
        print(f"31-60 days overdue: ${days_31_60:,.2f}")
        print(f"61-90 days overdue: ${days_61_90:,.2f}")
        print(f"Over 90 days overdue: ${days_over_90:,.2f}")
        
        if total > 0:
            print(f"\nPercentage Distribution:")
            print(f"Current: {(current/total)*100:.1f}%")
            print(f"1-30 days: {(days_1_30/total)*100:.1f}%")
            print(f"31-60 days: {(days_31_60/total)*100:.1f}%")
            print(f"61-90 days: {(days_61_90/total)*100:.1f}%")
            print(f"Over 90 days: {(days_over_90/total)*100:.1f}%")
        
        input("Press Enter to continue...")
    
    def payment_menu(self):
        """Payment processing menu"""
        while True:
            print("\n" + "-"*30)
            print("PAYMENT PROCESSING")
            print("-"*30)
            print("1. Record Payment")
            print("2. View Invoice Payments")
            print("3. View Customer Payments")
            print("B. Back to Main Menu")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'b':
                break
            elif choice == '1':
                self.record_payment()
            elif choice == '2':
                self.view_invoice_payments()
            elif choice == '3':
                self.view_customer_payments()
            else:
                print("Invalid choice.")
    
    def record_payment(self):
        """Record a payment"""
        print("\n--- Record Payment ---")
        
        try:
            invoice_id = int(input("Invoice ID: ").strip())
            # Verify invoice exists
            invoice = self.invoice_manager.get_invoice(invoice_id)
            if not invoice:
                print("Invoice not found")
                return
        except ValueError:
            print("Invalid Invoice ID")
            return
        
        print(f"Invoice #{invoice['invoice_number']} - Balance: ${invoice['balance']:,.2f}")
        
        payment_data = {}
        payment_data['invoice_id'] = invoice_id
        
        try:
            payment_date_str = input("Payment Date (YYYY-MM-DD, or Enter for today): ").strip()
            if payment_date_str:
                payment_data['payment_date'] = datetime.strptime(payment_date_str, '%Y-%m-%d').date()
            else:
                payment_data['payment_date'] = date.today()
        except ValueError:
            print("Invalid date format")
            return
        
        try:
            payment_data['amount'] = float(input("Payment Amount: $").strip())
            if payment_data['amount'] > invoice['balance']:
                confirm = input(f"Payment amount exceeds balance. Continue? (y/n): ").strip().lower()
                if confirm != 'y':
                    return
        except ValueError:
            print("Invalid amount")
            return
        
        payment_data['payment_method'] = input("Payment Method (CHECK/WIRE/ACH/etc): ").strip().upper()
        payment_data['reference_number'] = input("Reference Number (optional): ").strip() or None
        payment_data['notes'] = input("Notes (optional): ").strip() or None
        
        try:
            payment_id = self.payment_manager.add_payment(payment_data)
            print(f"\nPayment recorded successfully! Payment ID: {payment_id}")
            
            # Show updated invoice balance
            updated_invoice = self.invoice_manager.get_invoice(invoice_id)
            print(f"Updated invoice balance: ${updated_invoice['balance']:,.2f}")
            
        except Exception as e:
            print(f"Error recording payment: {e}")
        
        input("Press Enter to continue...")
    
    def collection_activity_menu(self):
        """Collection activities menu"""
        while True:
            print("\n" + "-"*30)
            print("COLLECTION ACTIVITIES")
            print("-"*30)
            print("1. Record Activity")
            print("2. View Customer Activities")
            print("3. Follow-up Activities")
            print("B. Back to Main Menu")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'b':
                break
            elif choice == '1':
                self.record_activity()
            elif choice == '2':
                self.view_customer_activities()
            elif choice == '3':
                self.view_follow_up_activities()
            else:
                print("Invalid choice.")
    
    def record_activity(self):
        """Record a collection activity"""
        print("\n--- Record Collection Activity ---")
        
        try:
            customer_id = int(input("Customer ID: ").strip())
            # Verify customer exists
            customer = self.customer_manager.get_customer(customer_id)
            if not customer:
                print("Customer not found")
                return
        except ValueError:
            print("Invalid Customer ID")
            return
        
        print(f"Customer: {customer['customer_name']}")
        
        activity_data = {}
        activity_data['customer_id'] = customer_id
        
        # Optional invoice ID
        invoice_id_str = input("Invoice ID (optional, Enter to skip): ").strip()
        if invoice_id_str:
            try:
                activity_data['invoice_id'] = int(invoice_id_str)
            except ValueError:
                print("Invalid Invoice ID, skipping...")
        
        print("\nActivity Types: CALL, EMAIL, LETTER, VISIT, LEGAL")
        activity_data['activity_type'] = input("Activity Type: ").strip().upper()
        
        activity_data['collector_name'] = input("Collector Name: ").strip()
        
        print("\nOutcome Types: NO_ANSWER, SPOKE_TO_CUSTOMER, LEFT_MESSAGE, PROMISE_TO_PAY, DISPUTE, PAYMENT_ARRANGED")
        activity_data['outcome'] = input("Outcome: ").strip().upper()
        
        activity_data['notes'] = input("Notes: ").strip()
        
        # Follow-up date
        follow_up_str = input("Follow-up Date (YYYY-MM-DD, optional): ").strip()
        if follow_up_str:
            try:
                activity_data['follow_up_date'] = datetime.strptime(follow_up_str, '%Y-%m-%d').date()
            except ValueError:
                print("Invalid date format, skipping follow-up date")
        
        try:
            activity_id = self.activity_manager.add_activity(activity_data)
            print(f"\nActivity recorded successfully! Activity ID: {activity_id}")
        except Exception as e:
            print(f"Error recording activity: {e}")
        
        input("Press Enter to continue...")
    
    def collection_priority_menu(self):
        """Collection priority menu"""
        while True:
            print("\n" + "-"*30)
            print("COLLECTION PRIORITIES")
            print("-"*30)
            print("1. View Priority List")
            print("2. High Priority Customers")
            print("3. Risk Categories")
            print("4. Collection Recommendations")
            print("5. Workload Distribution")
            print("B. Back to Main Menu")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'b':
                break
            elif choice == '1':
                self.view_priority_list()
            elif choice == '2':
                self.view_high_priority_customers()
            elif choice == '3':
                self.view_risk_categories()
            elif choice == '4':
                self.view_collection_recommendations()
            elif choice == '5':
                self.view_workload_distribution()
            else:
                print("Invalid choice.")
    
    def view_priority_list(self):
        """View prioritized collection list"""
        print("\n--- Collection Priority List ---")
        
        try:
            limit = int(input("Number of customers to show (default 20): ").strip() or "20")
        except ValueError:
            limit = 20
        
        prioritized = self.prioritizer.get_prioritized_collection_list(limit)
        
        if not prioritized:
            print("No customers with outstanding balances found")
            return
        
        print(f"{'Rank':<5} {'Customer':<20} {'Score':<8} {'Outstanding':<12} {'Overdue':<12} {'Risk':<8}")
        print("-" * 75)
        
        for i, customer in enumerate(prioritized, 1):
            outstanding = customer['outstanding_balance'] or 0
            overdue = customer['overdue_balance'] or 0
            score = customer['priority_score']
            
            print(f"{i:<5} "
                  f"{customer['customer_name'][:19]:<20} "
                  f"{score:<8.1f} "
                  f"${outstanding:<11,.0f} "
                  f"${overdue:<11,.0f} "
                  f"{customer['risk_rating']:<8}")
        
        input("Press Enter to continue...")
    
    def view_collection_recommendations(self):
        """View collection recommendations for a customer"""
        print("\n--- Collection Recommendations ---")
        
        try:
            customer_id = int(input("Customer ID: ").strip())
        except ValueError:
            print("Invalid Customer ID")
            return
        
        recommendations = self.prioritizer.get_collection_recommendations(customer_id)
        
        customer = self.customer_manager.get_customer(customer_id)
        if customer:
            print(f"\nRecommendations for: {customer['customer_name']}")
            print("-" * 50)
            
            for rec in recommendations:
                print(f"• {rec}")
        else:
            print("Customer not found")
        
        input("Press Enter to continue...")
    
    def efficiency_reports_menu(self):
        """Efficiency reports menu"""
        while True:
            print("\n" + "-"*30)
            print("EFFICIENCY REPORTS")
            print("-"*30)
            print("1. Current Month Report")
            print("2. Custom Period Report")
            print("3. Collection Metrics")
            print("4. Promise Keeping Rate")
            print("5. Contact Success Rate")
            print("B. Back to Main Menu")
            
            choice = input("\nEnter choice: ").strip().lower()
            
            if choice == 'b':
                break
            elif choice == '1':
                self.current_month_report()
            elif choice == '2':
                self.custom_period_report()
            elif choice == '3':
                self.collection_metrics()
            elif choice == '4':
                self.promise_keeping_report()
            elif choice == '5':
                self.contact_success_report()
            else:
                print("Invalid choice.")
    
    def current_month_report(self):
        """Show current month efficiency report"""
        print("\n--- Current Month Efficiency Report ---")
        
        today = date.today()
        start_date = date(today.year, today.month, 1)
        end_date = today
        
        report = self.efficiency_calculator.generate_efficiency_report(start_date, end_date)
        self.display_efficiency_report(report)
    
    def display_efficiency_report(self, report):
        """Display efficiency report"""
        print(f"\nPeriod: {report['period']['start_date']} to {report['period']['end_date']}")
        print("=" * 50)
        
        print(f"Collection Rate: {report['collection_rate']:.1f}%")
        print(f"Days Sales Outstanding: {report['days_sales_outstanding']:.1f} days")
        print(f"Promise Keeping Rate: {report['promise_keeping_rate']:.1f}%")
        print(f"Contact Success Rate: {report['contact_success_rate']:.1f}%")
        print(f"Average Collection Time: {report['average_collection_time']:.1f} days")
        
        # Aging summary
        aging = report['aging_report']
        if aging:
            print(f"\nAging Summary:")
            print(f"Total Outstanding: ${aging.get('total_balance', 0):,.2f}")
            print(f"Over 90 days: ${aging.get('days_over_90', 0):,.2f}")
        
        input("Press Enter to continue...")
    
    def dashboard_menu(self):
        """Dashboard overview"""
        print("\n" + "="*50)
        print("COLLECTION DASHBOARD")
        print("="*50)
        
        # Key metrics
        aging = self.invoice_manager.get_aging_report()
        overdue = self.invoice_manager.get_overdue_invoices()
        promises = self.promise_manager.get_overdue_promises()
        
        print(f"\nKEY METRICS")
        print("-" * 30)
        print(f"Total Outstanding: ${aging.get('total_balance', 0):,.2f}")
        print(f"Overdue Amount: ${aging.get('days_1_30', 0) + aging.get('days_31_60', 0) + aging.get('days_61_90', 0) + aging.get('days_over_90', 0):,.2f}")
        print(f"Number of Overdue Invoices: {len(overdue)}")
        print(f"Overdue Promises: {len(promises)}")
        print(f"DSO: {self.efficiency_calculator.calculate_dso():.1f} days")
        
        # Top priorities
        high_priority = self.prioritizer.get_high_priority_customers(300)
        print(f"\nHIGH PRIORITY CUSTOMERS ({len(high_priority)})")
        print("-" * 40)
        
        for customer in high_priority[:5]:  # Show top 5
            print(f"* {customer['customer_name']} - Score: {customer['priority_score']:.0f} - ${customer['outstanding_balance']:,.0f}")
        
        if len(high_priority) > 5:
            print(f"... and {len(high_priority) - 5} more")
        
        # Overdue promises
        if promises:
            print(f"\nOVERDUE PROMISES ({len(promises)})")
            print("-" * 30)
            for promise in promises[:3]:  # Show top 3
                print(f"* {promise['customer_name']} - ${promise['promised_amount']:,.2f} - Due: {promise['promise_date']}")
        
        input("\nPress Enter to continue...")
    
    def sample_data_menu(self):
        """Sample data management"""
        print("\n--- Sample Data ---")
        print("1. Load Sample Data")
        print("2. Clear All Data")
        print("B. Back to Main Menu")
        
        choice = input("\nEnter choice: ").strip().lower()
        
        if choice == '1':
            self.load_sample_data()
        elif choice == '2':
            confirm = input("Are you sure you want to clear ALL data? (type 'YES' to confirm): ").strip()
            if confirm == 'YES':
                self.clear_all_data()
        elif choice != 'b':
            print("Invalid choice.")
    
    def load_sample_data(self):
        """Load sample data for testing"""
        print("\nLoading sample data...")
        
        try:
            # Sample customers
            customers_data = [
                {
                    'customer_name': 'Acme Corporation',
                    'company_name': 'Acme Corp',
                    'email': 'billing@acmecorp.com',
                    'phone': '555-0101',
                    'credit_limit': 50000,
                    'payment_terms': 30,
                    'risk_rating': 'MEDIUM'
                },
                {
                    'customer_name': 'Tech Solutions Inc',
                    'company_name': 'Tech Solutions',
                    'email': 'accounts@techsolutions.com',
                    'phone': '555-0102',
                    'credit_limit': 25000,
                    'payment_terms': 45,
                    'risk_rating': 'LOW'
                },
                {
                    'customer_name': 'Quick Pay LLC',
                    'company_name': 'Quick Pay',
                    'email': 'finance@quickpay.com',
                    'phone': '555-0103',
                    'credit_limit': 15000,
                    'payment_terms': 15,
                    'risk_rating': 'HIGH'
                }
            ]
            
            customer_ids = []
            for customer_data in customers_data:
                customer_id = self.customer_manager.add_customer(customer_data)
                customer_ids.append(customer_id)
                print(f"Added customer: {customer_data['customer_name']}")
            
            # Sample invoices
            import random
            from datetime import timedelta
            
            base_date = date.today() - timedelta(days=120)
            
            for i, customer_id in enumerate(customer_ids):
                # Create 3-5 invoices per customer
                num_invoices = random.randint(3, 5)
                
                for j in range(num_invoices):
                    invoice_date = base_date + timedelta(days=random.randint(0, 100))
                    due_date = invoice_date + timedelta(days=30)
                    amount = random.randint(1000, 15000)
                    
                    invoice_data = {
                        'customer_id': customer_id,
                        'invoice_number': f'INV-{customer_id:03d}-{j+1:03d}',
                        'invoice_date': invoice_date,
                        'due_date': due_date,
                        'amount': amount,
                        'description': f'Services rendered - Invoice {j+1}'
                    }
                    
                    invoice_id = self.invoice_manager.add_invoice(invoice_data)
                    
                    # Randomly add payments to some invoices
                    if random.random() < 0.6:  # 60% chance of payment
                        payment_amount = random.randint(int(amount * 0.3), amount)
                        payment_date = due_date + timedelta(days=random.randint(-5, 30))
                        
                        payment_data = {
                            'invoice_id': invoice_id,
                            'payment_date': payment_date,
                            'amount': payment_amount,
                            'payment_method': random.choice(['CHECK', 'WIRE', 'ACH']),
                            'reference_number': f'PAY-{random.randint(1000, 9999)}'
                        }
                        
                        self.payment_manager.add_payment(payment_data)
            
            # Sample collection activities
            for customer_id in customer_ids:
                for _ in range(random.randint(1, 3)):
                    activity_date = date.today() - timedelta(days=random.randint(1, 30))
                    
                    activity_data = {
                        'customer_id': customer_id,
                        'activity_type': random.choice(['CALL', 'EMAIL', 'LETTER']),
                        'collector_name': random.choice(['John Smith', 'Sarah Johnson', 'Mike Wilson']),
                        'outcome': random.choice(['NO_ANSWER', 'SPOKE_TO_CUSTOMER', 'LEFT_MESSAGE', 'PROMISE_TO_PAY']),
                        'notes': 'Sample collection activity',
                        'follow_up_date': activity_date + timedelta(days=random.randint(3, 7))
                    }
                    
                    self.activity_manager.add_activity(activity_data)
            
            # Sample payment promises
            for customer_id in customer_ids:
                if random.random() < 0.7:  # 70% chance of promises
                    promise_data = {
                        'customer_id': customer_id,
                        'promise_date': date.today() + timedelta(days=random.randint(1, 14)),
                        'promised_amount': random.randint(1000, 5000),
                        'notes': 'Payment promise from collection call'
                    }
                    
                    self.promise_manager.add_promise(promise_data)
            
            print("\nSample data loaded successfully!")
            
        except Exception as e:
            print(f"Error loading sample data: {e}")
        
        input("Press Enter to continue...")
    
    def clear_all_data(self):
        """Clear all data from database"""
        print("Clearing all data...")
        
        try:
            # Clear in reverse dependency order
            self.db_manager.execute_update("DELETE FROM collection_metrics")
            self.db_manager.execute_update("DELETE FROM payment_promises") 
            self.db_manager.execute_update("DELETE FROM collection_activities")
            self.db_manager.execute_update("DELETE FROM payments")
            self.db_manager.execute_update("DELETE FROM invoices")
            self.db_manager.execute_update("DELETE FROM customers")
            
            print("All data cleared successfully!")
            
        except Exception as e:
            print(f"Error clearing data: {e}")
        
        input("Press Enter to continue...")
    
    def __del__(self):
        """Cleanup database connection"""
        if hasattr(self, 'db_manager'):
            self.db_manager.close()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Accounts Receivable Collection Manager')
    parser.add_argument('--sample-data', action='store_true', 
                       help='Load sample data and exit')
    parser.add_argument('--priority-list', action='store_true',
                       help='Show priority list and exit')
    parser.add_argument('--dashboard', action='store_true',
                       help='Show dashboard and exit')
    
    args = parser.parse_args()
    
    app = ARCollectionManager()
    
    if args.sample_data:
        app.load_sample_data()
        return
    
    if args.priority_list:
        app.view_priority_list()
        return
    
    if args.dashboard:
        app.dashboard_menu()
        return
    
    # Run interactive mode
    app.run_interactive_mode()

if __name__ == "__main__":
    main()