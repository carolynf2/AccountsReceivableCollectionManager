"""
Collection prioritization algorithms for AR Collection Manager
"""

from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Tuple
import math
from database import DatabaseManager, CustomerManager, InvoiceManager, PaymentPromiseManager

class CollectionPrioritizer:
    """Prioritizes collection activities based on multiple factors"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.customer_manager = CustomerManager(db_manager)
        self.invoice_manager = InvoiceManager(db_manager)
        self.promise_manager = PaymentPromiseManager(db_manager)
        self.weights = self._get_priority_weights()
    
    def _get_priority_weights(self) -> Dict[str, float]:
        """Get current priority weights from database"""
        query = """
        SELECT * FROM priority_settings 
        ORDER BY updated_date DESC 
        LIMIT 1
        """
        results = self.db.execute_query(query)
        if results:
            settings = results[0]
            return {
                'days_overdue': settings['days_overdue_weight'],
                'amount': settings['amount_weight'],
                'risk_rating': settings['risk_rating_weight'],
                'broken_promises': settings['broken_promises_weight'],
                'last_contact': settings['last_contact_weight']
            }
        else:
            # Default weights
            return {
                'days_overdue': 2.0,
                'amount': 1.5,
                'risk_rating': 1.8,
                'broken_promises': 2.5,
                'last_contact': 1.2
            }
    
    def calculate_priority_score(self, customer_data: Dict[str, Any]) -> float:
        """Calculate priority score for a customer based on multiple factors"""
        score = 0.0
        
        # Factor 1: Days overdue (higher = more urgent)
        max_days_overdue = max([
            max(0, (date.today() - datetime.strptime(inv['due_date'], '%Y-%m-%d').date()).days)
            for inv in self._get_open_invoices(customer_data['customer_id'])
        ] or [0])
        
        days_score = min(100, max_days_overdue * 2)  # Cap at 100, 2 points per day
        score += days_score * self.weights['days_overdue']
        
        # Factor 2: Outstanding amount (logarithmic scale)
        outstanding_balance = customer_data.get('outstanding_balance', 0)
        if outstanding_balance > 0:
            amount_score = min(100, math.log10(outstanding_balance) * 10)  # Log scale
        else:
            amount_score = 0
        score += amount_score * self.weights['amount']
        
        # Factor 3: Risk rating
        risk_rating = customer_data.get('risk_rating', 'LOW')
        risk_scores = {'LOW': 10, 'MEDIUM': 50, 'HIGH': 100}
        risk_score = risk_scores.get(risk_rating, 10)
        score += risk_score * self.weights['risk_rating']
        
        # Factor 4: Broken promises
        broken_promises = customer_data.get('broken_promises', 0)
        promise_score = min(100, broken_promises * 20)  # 20 points per broken promise
        score += promise_score * self.weights['broken_promises']
        
        # Factor 5: Days since last contact
        last_contact_date = customer_data.get('last_contact_date')
        if last_contact_date:
            if isinstance(last_contact_date, str):
                try:
                    # Try different datetime formats
                    if '.' in last_contact_date:
                        # Remove microseconds if present
                        last_contact_date = last_contact_date.split('.')[0]
                    last_contact = datetime.strptime(last_contact_date, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    try:
                        last_contact = datetime.strptime(last_contact_date, '%Y-%m-%d').date()
                    except ValueError:
                        last_contact = date.today() - timedelta(days=365)  # Default to old
            else:
                last_contact = last_contact_date
            days_since_contact = (date.today() - last_contact).days
        else:
            days_since_contact = 365  # Assume very old if never contacted
        
        contact_score = min(100, days_since_contact * 2)  # 2 points per day
        score += contact_score * self.weights['last_contact']
        
        return round(score, 2)
    
    def _get_open_invoices(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get open invoices for a customer"""
        query = """
        SELECT * FROM invoices 
        WHERE customer_id = ? AND status IN ('OPEN', 'PARTIAL')
        """
        return self.db.execute_query(query, (customer_id,))
    
    def get_prioritized_collection_list(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get prioritized list of customers for collection"""
        customers = self.customer_manager.get_customer_summary()
        
        # Calculate priority scores and add to customer data
        for customer in customers:
            if customer['outstanding_balance'] > 0:  # Only customers with outstanding balance
                customer['priority_score'] = self.calculate_priority_score(customer)
            else:
                customer['priority_score'] = 0
        
        # Filter customers with outstanding balances and sort by priority
        prioritized = [c for c in customers if c['outstanding_balance'] > 0]
        prioritized.sort(key=lambda x: x['priority_score'], reverse=True)
        
        return prioritized[:limit]
    
    def get_high_priority_customers(self, threshold_score: float = 300) -> List[Dict[str, Any]]:
        """Get customers with priority scores above threshold"""
        prioritized = self.get_prioritized_collection_list()
        return [c for c in prioritized if c['priority_score'] >= threshold_score]
    
    def get_customers_by_risk_category(self) -> Dict[str, List[Dict[str, Any]]]:
        """Categorize customers by collection risk"""
        prioritized = self.get_prioritized_collection_list()
        
        categories = {
            'critical': [],    # Score > 500
            'high': [],        # Score 300-500
            'medium': [],      # Score 150-300
            'low': []          # Score < 150
        }
        
        for customer in prioritized:
            score = customer['priority_score']
            if score > 500:
                categories['critical'].append(customer)
            elif score > 300:
                categories['high'].append(customer)
            elif score > 150:
                categories['medium'].append(customer)
            else:
                categories['low'].append(customer)
        
        return categories
    
    def get_collection_recommendations(self, customer_id: int) -> List[str]:
        """Get specific collection recommendations for a customer"""
        customer = self.customer_manager.get_customer(customer_id)
        if not customer:
            return ["Customer not found"]
        
        customer_summary = None
        for c in self.customer_manager.get_customer_summary():
            if c['customer_id'] == customer_id:
                customer_summary = c
                break
        
        if not customer_summary:
            return ["No outstanding balance"]
        
        recommendations = []
        score = self.calculate_priority_score(customer_summary)
        
        # High priority recommendations
        if score > 500:
            recommendations.append("CRITICAL: Immediate action required - consider legal proceedings")
        elif score > 300:
            recommendations.append("HIGH PRIORITY: Daily contact attempts recommended")
        elif score > 150:
            recommendations.append("MEDIUM PRIORITY: Contact within 3-5 business days")
        else:
            recommendations.append("LOW PRIORITY: Standard collection process")
        
        # Specific recommendations based on factors
        overdue_balance = customer_summary.get('overdue_balance', 0)
        if overdue_balance > 0:
            overdue_invoices = self._get_overdue_invoices_for_customer(customer_id)
            max_days_overdue = max([inv['days_overdue'] for inv in overdue_invoices], default=0)
            
            if max_days_overdue > 90:
                recommendations.append("AGING: Account is 90+ days overdue - escalate to senior collector")
            elif max_days_overdue > 60:
                recommendations.append("AGING: Account is 60+ days overdue - consider payment plan")
            elif max_days_overdue > 30:
                recommendations.append("AGING: Account is 30+ days overdue - increase contact frequency")
        
        # Broken promises
        broken_promises = customer_summary.get('broken_promises', 0)
        if broken_promises > 2:
            recommendations.append("PROMISES: Multiple broken promises - require immediate payment or payment plan")
        elif broken_promises > 0:
            recommendations.append("PROMISES: Previous broken promises - be cautious with new promises")
        
        # Risk rating
        risk_rating = customer.get('risk_rating', 'LOW')
        if risk_rating == 'HIGH':
            recommendations.append("RISK: High risk customer - consider credit hold")
        elif risk_rating == 'MEDIUM':
            recommendations.append("RISK: Medium risk customer - monitor closely")
        
        # Contact history
        last_contact = customer.get('last_contact_date')
        if last_contact:
            if isinstance(last_contact, str):
                try:
                    # Try different datetime formats
                    if '.' in last_contact:
                        # Remove microseconds if present
                        last_contact = last_contact.split('.')[0]
                    last_contact_date = datetime.strptime(last_contact, '%Y-%m-%d %H:%M:%S').date()
                except ValueError:
                    try:
                        last_contact_date = datetime.strptime(last_contact, '%Y-%m-%d').date()
                    except ValueError:
                        last_contact_date = date.today() - timedelta(days=365)  # Default to old
            else:
                last_contact_date = last_contact
            days_since_contact = (date.today() - last_contact_date).days
            
            if days_since_contact > 14:
                recommendations.append("CONTACT: No contact in 14+ days - immediate follow-up needed")
            elif days_since_contact > 7:
                recommendations.append("CONTACT: No contact in 7+ days - schedule follow-up call")
        else:
            recommendations.append("CONTACT: No previous contact recorded - initial contact needed")
        
        # Amount-based recommendations
        outstanding = customer_summary.get('outstanding_balance', 0)
        if outstanding > 50000:
            recommendations.append("AMOUNT: Large outstanding balance - consider executive escalation")
        elif outstanding > 10000:
            recommendations.append("AMOUNT: Significant balance - prioritize for immediate action")
        
        return recommendations
    
    def _get_overdue_invoices_for_customer(self, customer_id: int) -> List[Dict[str, Any]]:
        """Get overdue invoices for a specific customer"""
        query = """
        SELECT * FROM overdue_invoices 
        WHERE customer_id = ?
        ORDER BY days_overdue DESC
        """
        return self.db.execute_query(query, (customer_id,))
    
    def get_collection_workload_distribution(self, collectors: List[str]) -> Dict[str, List[Dict[str, Any]]]:
        """Distribute collection workload among collectors"""
        prioritized_customers = self.get_prioritized_collection_list()
        
        if not collectors:
            return {'unassigned': prioritized_customers}
        
        # Initialize collector workloads
        workloads = {collector: [] for collector in collectors}
        
        # Distribute customers round-robin style, starting with highest priority
        for i, customer in enumerate(prioritized_customers):
            collector = collectors[i % len(collectors)]
            workloads[collector].append(customer)
        
        return workloads
    
    def update_priority_weights(self, new_weights: Dict[str, float]) -> int:
        """Update priority calculation weights"""
        query = """
        INSERT INTO priority_settings (
            days_overdue_weight, amount_weight, risk_rating_weight,
            broken_promises_weight, last_contact_weight
        ) VALUES (?, ?, ?, ?, ?)
        """
        params = (
            new_weights.get('days_overdue', 2.0),
            new_weights.get('amount', 1.5),
            new_weights.get('risk_rating', 1.8),
            new_weights.get('broken_promises', 2.5),
            new_weights.get('last_contact', 1.2)
        )
        
        setting_id = self.db.execute_insert(query, params)
        self.weights = new_weights  # Update local weights
        return setting_id

class CollectionEfficiencyCalculator:
    """Calculates various collection efficiency metrics"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
    
    def calculate_collection_rate(self, start_date: date, end_date: date) -> float:
        """Calculate collection rate for a period"""
        # Total receivables at start of period
        query_start = """
        SELECT SUM(balance) as total_receivables
        FROM invoices 
        WHERE invoice_date <= ? AND status IN ('OPEN', 'PARTIAL')
        """
        start_result = self.db.execute_query(query_start, (start_date,))
        start_receivables = start_result[0]['total_receivables'] or 0
        
        # Collections during period
        query_collections = """
        SELECT SUM(amount) as collections
        FROM payments 
        WHERE payment_date BETWEEN ? AND ?
        """
        collections_result = self.db.execute_query(query_collections, (start_date, end_date))
        collections = collections_result[0]['collections'] or 0
        
        if start_receivables > 0:
            return round((collections / start_receivables) * 100, 2)
        return 0.0
    
    def calculate_dso(self) -> float:
        """Calculate Days Sales Outstanding (DSO)"""
        # Average daily sales for last 90 days
        ninety_days_ago = date.today() - timedelta(days=90)
        
        query_sales = """
        SELECT SUM(amount) as total_sales
        FROM invoices 
        WHERE invoice_date >= ?
        """
        sales_result = self.db.execute_query(query_sales, (ninety_days_ago,))
        total_sales = sales_result[0]['total_sales'] or 0
        
        daily_sales = total_sales / 90 if total_sales > 0 else 0
        
        # Current accounts receivable
        query_ar = """
        SELECT SUM(balance) as total_ar
        FROM invoices 
        WHERE status IN ('OPEN', 'PARTIAL')
        """
        ar_result = self.db.execute_query(query_ar)
        total_ar = ar_result[0]['total_ar'] or 0
        
        if daily_sales > 0:
            return round(total_ar / daily_sales, 1)
        return 0.0
    
    def calculate_promise_keeping_rate(self, start_date: date, end_date: date) -> float:
        """Calculate promise keeping rate for a period"""
        query = """
        SELECT 
            COUNT(*) as total_promises,
            COUNT(CASE WHEN status = 'KEPT' THEN 1 END) as kept_promises
        FROM payment_promises 
        WHERE promise_date BETWEEN ? AND ?
        """
        result = self.db.execute_query(query, (start_date, end_date))
        
        if result and result[0]['total_promises'] > 0:
            return round((result[0]['kept_promises'] / result[0]['total_promises']) * 100, 2)
        return 0.0
    
    def calculate_contact_success_rate(self, start_date: date, end_date: date) -> float:
        """Calculate contact success rate for a period"""
        query = """
        SELECT 
            COUNT(*) as total_activities,
            COUNT(CASE WHEN outcome IN ('SPOKE_TO_CUSTOMER', 'PROMISE_TO_PAY') THEN 1 END) as successful_contacts
        FROM collection_activities 
        WHERE DATE(activity_date) BETWEEN ? AND ?
        """
        result = self.db.execute_query(query, (start_date, end_date))
        
        if result and result[0]['total_activities'] > 0:
            return round((result[0]['successful_contacts'] / result[0]['total_activities']) * 100, 2)
        return 0.0
    
    def calculate_average_collection_time(self) -> float:
        """Calculate average time to collect invoices"""
        query = """
        SELECT AVG(
            julianday(p.payment_date) - julianday(i.invoice_date)
        ) as avg_days
        FROM payments p
        JOIN invoices i ON p.invoice_id = i.invoice_id
        WHERE i.status = 'PAID'
        AND p.payment_date >= date('now', '-365 days')
        """
        result = self.db.execute_query(query)
        
        if result and result[0]['avg_days'] is not None:
            return round(result[0]['avg_days'], 1)
        return 0.0
    
    def generate_efficiency_report(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """Generate comprehensive efficiency report"""
        return {
            'period': {
                'start_date': start_date.strftime('%Y-%m-%d'),
                'end_date': end_date.strftime('%Y-%m-%d')
            },
            'collection_rate': self.calculate_collection_rate(start_date, end_date),
            'days_sales_outstanding': self.calculate_dso(),
            'promise_keeping_rate': self.calculate_promise_keeping_rate(start_date, end_date),
            'contact_success_rate': self.calculate_contact_success_rate(start_date, end_date),
            'average_collection_time': self.calculate_average_collection_time(),
            'aging_report': self._get_aging_summary(),
            'top_priorities': self._get_top_priority_customers()
        }
    
    def _get_aging_summary(self) -> Dict[str, Any]:
        """Get current aging summary"""
        invoice_manager = InvoiceManager(self.db)
        return invoice_manager.get_aging_report()
    
    def _get_top_priority_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top priority customers for the report"""
        prioritizer = CollectionPrioritizer(self.db)
        return prioritizer.get_prioritized_collection_list(limit)
    
    def save_metrics_snapshot(self, start_date: date, end_date: date) -> int:
        """Save efficiency metrics snapshot to database"""
        metrics = self.generate_efficiency_report(start_date, end_date)
        
        # Count activities and contacts
        activity_query = """
        SELECT 
            COUNT(*) as total_activities,
            COUNT(CASE WHEN outcome IN ('SPOKE_TO_CUSTOMER', 'PROMISE_TO_PAY') THEN 1 END) as successful_contacts
        FROM collection_activities 
        WHERE DATE(activity_date) BETWEEN ? AND ?
        """
        activity_result = self.db.execute_query(activity_query, (start_date, end_date))
        
        # Count promises
        promise_query = """
        SELECT 
            COUNT(*) as promises_made,
            COUNT(CASE WHEN status = 'KEPT' THEN 1 END) as promises_kept
        FROM payment_promises 
        WHERE promise_date BETWEEN ? AND ?
        """
        promise_result = self.db.execute_query(promise_query, (start_date, end_date))
        
        # Get total receivables
        aging = metrics['aging_report']
        total_receivables = aging.get('total_balance', 0)
        
        # Calculate collected amount
        collection_query = """
        SELECT SUM(amount) as collected
        FROM payments 
        WHERE payment_date BETWEEN ? AND ?
        """
        collection_result = self.db.execute_query(collection_query, (start_date, end_date))
        collected_amount = collection_result[0]['collected'] or 0
        
        # Insert metrics
        insert_query = """
        INSERT INTO collection_metrics (
            period_start, period_end, total_receivables, collected_amount,
            collection_rate, average_days_to_collect, total_activities,
            successful_contacts, promises_made, promises_kept
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        params = (
            start_date,
            end_date,
            total_receivables,
            collected_amount,
            metrics['collection_rate'],
            metrics['average_collection_time'],
            activity_result[0]['total_activities'] if activity_result else 0,
            activity_result[0]['successful_contacts'] if activity_result else 0,
            promise_result[0]['promises_made'] if promise_result else 0,
            promise_result[0]['promises_kept'] if promise_result else 0
        )
        
        return self.db.execute_insert(insert_query, params)