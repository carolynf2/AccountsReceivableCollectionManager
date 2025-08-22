#!/usr/bin/env python3
"""
Test script for AR Collection Manager
"""

import sys
import os
from datetime import date, timedelta

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import DatabaseManager
from collection_prioritizer import CollectionPrioritizer, CollectionEfficiencyCalculator
from main import ARCollectionManager

def test_priority_system():
    """Test the prioritization system"""
    print("="*60)
    print("AR COLLECTION MANAGER - SYSTEM TEST")
    print("="*60)
    
    # Initialize system
    app = ARCollectionManager()
    
    print("\n1. TESTING PRIORITY CALCULATION")
    print("-" * 40)
    
    # Get prioritized list
    prioritized = app.prioritizer.get_prioritized_collection_list(10)
    
    if prioritized:
        print(f"{'Rank':<5} {'Customer':<20} {'Score':<8} {'Outstanding':<12} {'Risk':<8}")
        print("-" * 65)
        
        for i, customer in enumerate(prioritized, 1):
            outstanding = customer['outstanding_balance'] or 0
            score = customer['priority_score']
            
            print(f"{i:<5} "
                  f"{customer['customer_name'][:19]:<20} "
                  f"{score:<8.1f} "
                  f"${outstanding:<11,.0f} "
                  f"{customer['risk_rating']:<8}")
    else:
        print("No customers with outstanding balances found")
    
    print("\n2. TESTING COLLECTION RECOMMENDATIONS")
    print("-" * 40)
    
    if prioritized:
        # Test recommendations for top customer
        top_customer = prioritized[0]
        customer_id = top_customer['customer_id']
        
        print(f"Recommendations for: {top_customer['customer_name']}")
        print("-" * 30)
        
        recommendations = app.prioritizer.get_collection_recommendations(customer_id)
        for rec in recommendations:
            print(f"• {rec}")
    
    print("\n3. TESTING EFFICIENCY CALCULATIONS")
    print("-" * 40)
    
    # Calculate efficiency for last 30 days
    end_date = date.today()
    start_date = end_date - timedelta(days=30)
    
    report = app.efficiency_calculator.generate_efficiency_report(start_date, end_date)
    
    print(f"Period: {report['period']['start_date']} to {report['period']['end_date']}")
    print(f"Collection Rate: {report['collection_rate']:.1f}%")
    print(f"Days Sales Outstanding: {report['days_sales_outstanding']:.1f} days")
    print(f"Promise Keeping Rate: {report['promise_keeping_rate']:.1f}%")
    print(f"Contact Success Rate: {report['contact_success_rate']:.1f}%")
    print(f"Average Collection Time: {report['average_collection_time']:.1f} days")
    
    print("\n4. TESTING AGING REPORT")
    print("-" * 40)
    
    aging = app.invoice_manager.get_aging_report()
    if aging:
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
            print(f"\nOverdue Percentage: {((days_1_30 + days_31_60 + days_61_90 + days_over_90)/total)*100:.1f}%")
    
    print("\n5. TESTING RISK CATEGORIES")
    print("-" * 40)
    
    categories = app.prioritizer.get_customers_by_risk_category()
    
    for category, customers in categories.items():
        if customers:
            print(f"{category.upper()}: {len(customers)} customers")
            for customer in customers[:3]:  # Show top 3 in each category
                print(f"  • {customer['customer_name']} - Score: {customer['priority_score']:.0f}")
            if len(customers) > 3:
                print(f"  ... and {len(customers) - 3} more")
    
    print("\n" + "="*60)
    print("SYSTEM TEST COMPLETED SUCCESSFULLY")
    print("="*60)

if __name__ == "__main__":
    test_priority_system()